"""Parser determinístico e schemas Pydantic da Legislação Municipal (NúcleoGov — ADR-004)."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from cerrado_aberto_coleta import __version__

VERSAO_COLETOR_LEGISLACAO = f"cerrado-aberto-coleta/{__version__}-legislacao-nucleogov"
_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")


class LayoutLegislacaoAlteradoError(ValueError):
    """Levantado quando o contrato JSON do NúcleoGov de legislação muda inesperadamente."""


class NormaRegistro(BaseModel):
    model_config = ConfigDict(frozen=True)

    norma_id: str
    municipio_id: str
    tabela_origem: str
    id_origem: int
    numero: str
    ano: int | None
    tipo_norma: str
    categoria_id_origem: str | None
    categoria_descricao: str
    data_publicacao: date | None
    data_publicacao_portal: date | None
    ementa: str
    total_anexos: int
    texto_extraido: str | None = None
    status_ocr: str = "METADADOS_APENAS"
    extraido_por_ocr: bool = False
    ocr_engine_versao: str | None = None
    ocr_confianca_media: float | None = None
    requer_revisao_humana: bool = False
    motivo_revisao_humana: str | None = None
    fonte_id: str = "legislacao_nucleogov"
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str = VERSAO_COLETOR_LEGISLACAO


def _parse_data_iso(valor: Any) -> date | None:
    if not valor or not isinstance(valor, str):
        return None
    bruto = valor.strip()[:10]
    try:
        return date.fromisoformat(bruto)
    except ValueError:
        return None


def construir_url_canonica_norma(
    *,
    base_url: str = "https://acessoainformacao.inhumas.go.leg.br",
    tabela_origem: str,
    id_origem: int,
) -> str:
    """Retorna a URL pública permanente da norma (jamais a URL temporária do S3)."""
    mapa_segmento = {
        "leis": "lei",
        "decretos": "decreto",
        "resolucoes": "resolucao",
        "portarias": "portaria",
    }
    seg = mapa_segmento.get(tabela_origem.lower(), "lei")
    return f"{base_url.rstrip('/')}/legislacao/{seg}/id={id_origem}"


def _mascarar_cpf_texto(texto: str) -> str:
    return _RE_CPF.sub("***.***.***-**", texto)


def parse_pagina_leis_nucleogov(
    payload: dict[str, Any],
    *,
    municipio_id: str = "inhumas-go",
    base_url: str = "https://acessoainformacao.inhumas.go.leg.br",
    coletado_em: datetime,
) -> tuple[int, list[NormaRegistro]]:
    """Parseia uma página JSON retornada por POST /api do NúcleoGov (estrutura multiplexada ou direta)."""
    if not isinstance(payload, dict):
        raise LayoutLegislacaoAlteradoError("Payload de legislação não é um objeto JSON.")

    bloco: dict[str, Any] | None = None
    if "dados" in payload and isinstance(payload["dados"], list):
        bloco = payload
    else:
        for val in payload.values():
            if isinstance(val, dict) and isinstance(val.get("dados"), list):
                bloco = val
                break

    if bloco is None:
        raise LayoutLegislacaoAlteradoError(
            "Estrutura JSON da legislação alterada: nenhum bloco com array 'dados' encontrado."
        )

    try:
        total_declarado = int(bloco.get("total") or len(bloco["dados"]))
    except (TypeError, ValueError) as exc:
        raise LayoutLegislacaoAlteradoError(f"Campo 'total' inválido: {bloco.get('total')!r}") from exc

    normas: list[NormaRegistro] = []
    for item in bloco["dados"]:
        if not isinstance(item, dict):
            continue
        if str(item.get("desativado") or "0") == "1" or str(item.get("oculto") or "0") == "1":
            continue
        if "id" not in item or "numero" not in item or "ementa" not in item:
            raise LayoutLegislacaoAlteradoError(
                f"Registro de lei sem campos obrigatórios ('id', 'numero', 'ementa'): {list(item.keys())}"
            )

        id_origem = int(item["id"])
        tabela = str(item.get("tabela") or "leis").strip().lower()
        numero = str(item["numero"]).strip()
        data_pub = _parse_data_iso(item.get("data_publicacao"))
        data_portal = _parse_data_iso(item.get("data_publicacao_portal"))

        ano_val: int | None = None
        if item.get("ano_referencia") is not None and str(item["ano_referencia"]).isdigit():
            ano_val = int(item["ano_referencia"])
        elif data_pub is not None:
            ano_val = data_pub.year

        categoria_desc = str(item.get("categoria_descricao") or "Lei Municipal").strip()
        ementa_limpa = _mascarar_cpf_texto(re.sub(r"\s+", " ", str(item["ementa"] or "")).strip())
        texto_nativo = item.get("texto")
        texto_limpo = (
            _mascarar_cpf_texto(str(texto_nativo).strip())
            if isinstance(texto_nativo, str) and texto_nativo.strip()
            else None
        )
        total_anexos = int(item.get("total_anexos") or 0)
        fonte_url = construir_url_canonica_norma(
            base_url=base_url, tabela_origem=tabela, id_origem=id_origem
        )

        # Hash canônico determinístico do registro normalizado para idempotência real
        assinatura = f"{tabela}|{id_origem}|{numero}|{data_pub}|{categoria_desc}|{ementa_limpa}|{total_anexos}"
        hash_registro = hashlib.sha256(assinatura.encode("utf-8")).hexdigest()

        normas.append(
            NormaRegistro(
                norma_id=f"{municipio_id}-norma-{tabela}-{id_origem}",
                municipio_id=municipio_id,
                tabela_origem=tabela,
                id_origem=id_origem,
                numero=numero,
                ano=ano_val,
                tipo_norma=categoria_desc,
                categoria_id_origem=str(item["categoria"]) if item.get("categoria") is not None else None,
                categoria_descricao=categoria_desc,
                data_publicacao=data_pub,
                data_publicacao_portal=data_portal,
                ementa=ementa_limpa,
                total_anexos=total_anexos,
                texto_extraido=texto_limpo,
                status_ocr="TEXTO_NATIVO_PDF" if texto_limpo else "METADADOS_APENAS",
                fonte_url=fonte_url,
                coletado_em=coletado_em,
                hash_conteudo=hash_registro,
            )
        )

    return total_declarado, normas
