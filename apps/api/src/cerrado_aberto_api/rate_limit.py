"""Middleware leve de rate limiting em memória por IP para a API pública (Fase 5)."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Aplica janela deslizante de 60 segundos por IP cliente, configurável via ambiente."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        requests_per_minute: int | None = None,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        env_val = os.getenv("CERRADO_RATE_LIMIT_RPM")
        default_rpm = int(env_val) if env_val and env_val.isdigit() else 240
        self.limit = requests_per_minute if requests_per_minute is not None else default_rpm
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}

    def reset(self) -> None:
        """Limpa contadores em memória (útil para testes automatizados)."""
        with self._lock:
            self._buckets.clear()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Não limita documentação estática OpenAPI
        if request.url.path in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Permite sobrescrever limite dinamicamente em testes via variável de ambiente
        env_rpm = os.getenv("CERRADO_RATE_LIMIT_RPM")
        limite_atual = int(env_rpm) if env_rpm and env_rpm.isdigit() else self.limit
        if limite_atual <= 0:
            return await call_next(request)

        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "local")
        )
        agora = time.monotonic()
        corte = agora - self.window_seconds

        with self._lock:
            bucket = self._buckets.setdefault(client_ip, deque())
            while bucket and bucket[0] <= corte:
                bucket.popleft()

            if len(bucket) >= limite_atual:
                retry_after = max(1, int(self.window_seconds - (agora - bucket[0])) + 1)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            "Limite temporário de requisições excedido para este endereço. "
                            "Aguarde alguns segundos antes de tentar novamente."
                        ),
                        "retry_after_seconds": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limite_atual),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            bucket.append(agora)
            restantes = max(0, limite_atual - len(bucket))

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limite_atual)
        response.headers["X-RateLimit-Remaining"] = str(restantes)
        return response
