"""Segurança e proteção LGPD (mascaramento de CPF em respostas, logs e erros + bloqueio de escrita)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_RE_CPF_FORMATADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_RE_CPF_11_DIGITOS = re.compile(r"(?<!\d)\d{11}(?!\d)")
_CHAVES_HASH_OU_URL = {
    "hash_conteudo",
    "fonte_url",
    "avatar_url",
    "ata_pdf_url",
    "anexo_principal_url",
    "evidencia_url",
}
_METODOS_LEITURA_PERMITIDOS = {"GET", "HEAD", "OPTIONS"}


def mascarar_cpf_em_texto(texto: str, *, nome_campo: str = "") -> str:
    """Mascara qualquer CPF formatado (XXX.XXX.XXX-XX) ou de 11 dígitos em campo de CPF."""
    limpo = _RE_CPF_FORMATADO.sub("***.***.***-**", texto)
    if (
        nome_campo
        and nome_campo not in _CHAVES_HASH_OU_URL
        and "cpf" in nome_campo.lower()
    ):
        limpo = _RE_CPF_11_DIGITOS.sub("***.***.***-**", limpo)
    return limpo


def sanitizar_estrutura_lgpd(valor: Any, *, nome_campo: str = "") -> Any:
    """Varre recursivamente dicionários, listas e strings para garantir ausência de CPF completo."""
    if isinstance(valor, str):
        return mascarar_cpf_em_texto(valor, nome_campo=nome_campo)
    if isinstance(valor, dict):
        return {
            k: sanitizar_estrutura_lgpd(v, nome_campo=str(k))
            for k, v in valor.items()
        }
    if isinstance(valor, list):
        return [sanitizar_estrutura_lgpd(item, nome_campo=nome_campo) for item in valor]
    if isinstance(valor, tuple):
        return [sanitizar_estrutura_lgpd(item, nome_campo=nome_campo) for item in valor]
    return valor


class FiltroLogLGPD(logging.Filter):
    """Filtro de logging que mascara CPFs antes que qualquer mensagem seja gravada em log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mascarar_cpf_em_texto(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    mascarar_cpf_em_texto(a) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: mascarar_cpf_em_texto(v, nome_campo=str(k)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


class LGPDAndReadOnlyMiddleware(BaseHTTPMiddleware):
    """Garante modo somente leitura e aplica sanitização LGPD em todas as respostas HTTP."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method.upper() not in _METODOS_LEITURA_PERMITIDOS:
            return JSONResponse(
                status_code=405,
                content={
                    "detail": (
                        "Operação não permitida. A API pública do Cerrado Aberto opera "
                        "exclusivamente em modo somente leitura (GET/HEAD/OPTIONS)."
                    )
                },
                headers={"Allow": "GET, HEAD, OPTIONS"},
            )

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response

        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                body_chunks.append(chunk.encode("utf-8"))
            else:
                body_chunks.append(bytes(chunk))
        raw_body = b"".join(body_chunks)

        try:
            texto = raw_body.decode("utf-8")
            if _RE_CPF_FORMATADO.search(texto) or '"cpf"' in texto.lower():
                dados = json.loads(texto)
                dados_limpos = sanitizar_estrutura_lgpd(dados)
                raw_body = json.dumps(dados_limpos, ensure_ascii=False).encode("utf-8")
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

        headers = dict(response.headers)
        headers["content-length"] = str(len(raw_body))
        return Response(
            content=raw_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
