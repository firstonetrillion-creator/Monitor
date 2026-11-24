"""Armazenamento local versionado de arquivos brutos (data/raw/) com abstração S3-compatível e governança de OCR (ADR-005)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4


def calcular_sha256(conteudo: bytes) -> str:
    """Calcula o hash SHA-256 hexadecimal de um conteúdo binário."""
    return hashlib.sha256(conteudo).hexdigest()


@dataclass(frozen=True)
class MetadadosDocumentoBruto:
    documento_id: str
    municipio_id: str
    fonte_id: str
    fonte_url: str
    coletado_em: str
    hash_conteudo: str
    versao_coletor: str
    storage_backend: str
    caminho_armazenamento: str
    mime_type: str
    tamanho_bytes: int
    status_http: int | None = 200
    url_temporaria: bool = False
    processado_ocr: bool = False
    extraido_por_ocr: bool = False
    ocr_engine_versao: str | None = None
    ocr_confianca_media: float | None = None
    requer_revisao_humana: bool = False
    motivo_revisao_humana: str | None = None


@dataclass(frozen=True)
class ResultadoOCR:
    """Mantém o texto extraído separado do binário original e sinaliza revisão humana (ADR-005)."""

    hash_documento_original: str
    extraido_por_ocr: bool
    texto_extraido: str
    ocr_engine_versao: str | None
    ocr_confianca_media: float | None
    requer_revisao_humana: bool
    motivo_revisao_humana: str | None = None


class StorageBackend(Protocol):
    """Protocolo de armazenamento bruto imutável pronto para migração S3-compatível."""

    def salvar_bruto(
        self,
        *,
        municipio_id: str,
        fonte_id: str,
        fonte_url: str,
        conteudo: bytes,
        mime_type: str,
        extensao: str,
        versao_coletor: str,
        status_http: int | None = 200,
        url_temporaria: bool = False,
        coletado_em: datetime | None = None,
    ) -> MetadadosDocumentoBruto: ...

    def ler_bruto(self, caminho_armazenamento: str) -> bytes: ...

    def salvar_resultado_ocr(
        self, metadados: MetadadosDocumentoBruto, resultado_ocr: ResultadoOCR
    ) -> MetadadosDocumentoBruto: ...


class LocalVersionedStorage:
    """Implementação local versionada em `data/raw/<municipio>/<fonte>/<YYYY>/<sha256>.<ext>`."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def construir_chave_objeto(
        self, municipio_id: str, fonte_id: str, ano: int, hash_conteudo: str, extensao: str
    ) -> str:
        ext_limpa = extensao.lstrip(".")
        return f"{municipio_id}/{fonte_id}/{ano}/{hash_conteudo}.{ext_limpa}"

    def salvar_bruto(
        self,
        *,
        municipio_id: str,
        fonte_id: str,
        fonte_url: str,
        conteudo: bytes,
        mime_type: str,
        extensao: str,
        versao_coletor: str,
        status_http: int | None = 200,
        url_temporaria: bool = False,
        coletado_em: datetime | None = None,
        ano_particao: int | None = None,
    ) -> MetadadosDocumentoBruto:
        instante = (coletado_em or datetime.now(UTC)).astimezone(UTC)
        hash_sha256 = calcular_sha256(conteudo)
        ano_dir = ano_particao if ano_particao is not None else instante.year
        chave_relativa = self.construir_chave_objeto(
            municipio_id=municipio_id,
            fonte_id=fonte_id,
            ano=ano_dir,
            hash_conteudo=hash_sha256,
            extensao=extensao,
        )
        caminho_arquivo = self.base_dir / chave_relativa
        caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

        # Bruto imutável: nunca sobrescreve se o mesmo SHA-256 já existir
        if not caminho_arquivo.exists():
            caminho_arquivo.write_bytes(conteudo)

        metadados = MetadadosDocumentoBruto(
            documento_id=str(uuid4()),
            municipio_id=municipio_id,
            fonte_id=fonte_id,
            fonte_url=fonte_url,
            coletado_em=instante.isoformat(),
            hash_conteudo=hash_sha256,
            versao_coletor=versao_coletor,
            storage_backend="local",
            caminho_armazenamento=chave_relativa,
            mime_type=mime_type,
            tamanho_bytes=len(conteudo),
            status_http=status_http,
            url_temporaria=url_temporaria,
        )

        caminho_meta = caminho_arquivo.with_suffix(caminho_arquivo.suffix + ".meta.json")
        if not caminho_meta.exists():
            caminho_meta.write_text(
                json.dumps(asdict(metadados), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return metadados

    def ler_bruto(self, caminho_armazenamento: str) -> bytes:
        caminho = self.base_dir / caminho_armazenamento
        return caminho.read_bytes()

    def salvar_resultado_ocr(
        self, metadados: MetadadosDocumentoBruto, resultado_ocr: ResultadoOCR
    ) -> MetadadosDocumentoBruto:
        """Armazena o texto extraído por OCR em arquivo .ocr.txt separado do PDF original intacto."""
        if resultado_ocr.hash_documento_original != metadados.hash_conteudo:
            raise ValueError(
                "Hash do resultado OCR não corresponde ao hash do documento bruto original."
            )

        caminho_original = self.base_dir / metadados.caminho_armazenamento
        if not caminho_original.exists():
            raise FileNotFoundError(
                f"Arquivo original '{metadados.caminho_armazenamento}' não encontrado."
            )

        caminho_texto_ocr = caminho_original.with_suffix(caminho_original.suffix + ".ocr.txt")
        caminho_texto_ocr.write_text(resultado_ocr.texto_extraido, encoding="utf-8")

        metadados_atualizados = MetadadosDocumentoBruto(
            **{
                **asdict(metadados),
                "processado_ocr": True,
                "extraido_por_ocr": resultado_ocr.extraido_por_ocr,
                "ocr_engine_versao": resultado_ocr.ocr_engine_versao,
                "ocr_confianca_media": resultado_ocr.ocr_confianca_media,
                "requer_revisao_humana": resultado_ocr.requer_revisao_humana,
                "motivo_revisao_humana": resultado_ocr.motivo_revisao_humana,
            }
        )
        caminho_meta = caminho_original.with_suffix(caminho_original.suffix + ".meta.json")
        caminho_meta.write_text(
            json.dumps(asdict(metadados_atualizados), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return metadados_atualizados
