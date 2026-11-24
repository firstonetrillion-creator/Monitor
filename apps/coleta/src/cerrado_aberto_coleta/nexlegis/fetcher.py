"""Etapa 1 (Fetch) do coletor Nexlegis: baixa o bruto sem transformar, respeita taxa e grava SHA-256."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from cerrado_aberto_coleta.config import MunicipioConfig
from cerrado_aberto_coleta.storage import MetadadosDocumentoBruto, StorageBackend


class NexlegisFetcher:
    """Cliente HTTP educado para a REST API JSON do Nexlegis (`https://inhumas.nexlegis.com.br/api`)."""

    def __init__(
        self,
        config: MunicipioConfig,
        storage: StorageBackend,
        *,
        http_client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.fonte_cfg = config.obter_fonte("nexlegis")
        self.storage = storage
        self._sleep = sleep_fn
        self._ultimo_request_ts: float | None = None
        self._client = http_client or httpx.Client(
            headers={
                "User-Agent": config.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=self.fonte_cfg.timeout_segundos,
            follow_redirects=True,
        )

    def _aguardar_rate_limit(self) -> None:
        if self._ultimo_request_ts is not None:
            decorrido = time.monotonic() - self._ultimo_request_ts
            restante = self.fonte_cfg.crawl_delay_segundos - decorrido
            if restante > 0:
                self._sleep(restante)
        self._ultimo_request_ts = time.monotonic()

    def _get_bytes_com_retry(self, url: str) -> tuple[bytes, int, str]:
        ultimo_erro: Exception | None = None
        for tentativa in range(1, self.fonte_cfg.max_tentativas + 1):
            self._aguardar_rate_limit()
            try:
                resp = self._client.get(url)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"Status HTTP {resp.status_code} temporário ao acessar {url}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                mime_type = resp.headers.get("content-type", "application/json").split(";")[0].strip()
                return resp.content, resp.status_code, mime_type
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                ultimo_erro = exc
                if tentativa < self.fonte_cfg.max_tentativas:
                    backoff = (2**tentativa) + random.uniform(0.1, 0.5)
                    self._sleep(backoff)

        raise RuntimeError(
            f"Falha ao baixar {url} após {self.fonte_cfg.max_tentativas} tentativas: {ultimo_erro}"
        ) from ultimo_erro

    def fetch_json_endpoint(
        self, caminho_relativo: str, *, coletado_em: datetime | None = None
    ) -> tuple[bytes, MetadadosDocumentoBruto]:
        """Baixa um endpoint JSON do Nexlegis e grava imediatamente no armazenamento bruto versionado."""
        base = self.fonte_cfg.url_base.rstrip("/")
        caminho = caminho_relativo.lstrip("/")
        url_completa = f"{base}/{caminho}"

        conteudo, status_http, mime_type = self._get_bytes_com_retry(url_completa)
        metadados = self.storage.salvar_bruto(
            municipio_id=self.config.municipio_id,
            fonte_id=self.fonte_cfg.fonte_id,
            fonte_url=url_completa,
            conteudo=conteudo,
            mime_type=mime_type or "application/json",
            extensao="json",
            versao_coletor=self.config.versao_coletor,
            status_http=status_http,
            url_temporaria=False,
            coletado_em=coletado_em or datetime.now(UTC),
        )
        return conteudo, metadados

    def fetch_pdf_imediato(
        self,
        *,
        download_url: str,
        fonte_url_canonica: str,
        url_temporaria: bool = True,
        coletado_em: datetime | None = None,
    ) -> tuple[bytes, MetadadosDocumentoBruto]:
        """Baixa imediatamente um PDF (ex.: ata ou lei com URL pré-assinada do S3) e grava no bruto."""
        conteudo, status_http, mime_type = self._get_bytes_com_retry(download_url)
        metadados = self.storage.salvar_bruto(
            municipio_id=self.config.municipio_id,
            fonte_id=self.fonte_cfg.fonte_id,
            fonte_url=fonte_url_canonica,
            conteudo=conteudo,
            mime_type=mime_type or "application/pdf",
            extensao="pdf",
            versao_coletor=self.config.versao_coletor,
            status_http=status_http,
            url_temporaria=url_temporaria,
            coletado_em=coletado_em or datetime.now(UTC),
        )
        return conteudo, metadados
