"""Coletor, parser e loader PostgreSQL do comparativo SICONFI (Função 01 - Legislativa).

Fonte oficial: API pública de dados abertos da Secretaria do Tesouro Nacional (SICONFI):
- `GET https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes`
- `GET https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?an_exercicio={ano}&no_anexo=DCA-Anexo+I-E&id_ente={cod_ibge}`
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import psycopg
from pydantic import BaseModel, ConfigDict

from cerrado_aberto_coleta import __version__
from cerrado_aberto_coleta.nexlegis.postgres_loader import (
    validar_ausencia_cpf_em_valores,
)

SICONFI_BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
VERSAO_COLETOR_SICONFI = f"cerrado-aberto-coleta/{__version__}-siconfi-dca"
USER_AGENT_PADRAO = "CerradoAberto/0.1 (+https://cerradoaberto.org.br; contato@cerradoaberto.org.br)"


@dataclass(frozen=True)
class MunicipioParSiconfi:
    codigo_ibge: str
    nome: str
    uf: str
    eh_foco: bool = False


# Municípios goianos na faixa de porte semelhante a Inhumas (44k–67k hab., validados em /entes)
MUNICIPIOS_PARES_POR_MUNICIPIO: dict[str, tuple[MunicipioParSiconfi, ...]] = {
    "inhumas-go": (
        MunicipioParSiconfi("5210000", "Inhumas", "GO", eh_foco=True),
        MunicipioParSiconfi("5213806", "Morrinhos", "GO"),
        MunicipioParSiconfi("5218508", "Quirinópolis", "GO"),
        MunicipioParSiconfi("5210406", "Itaberaí", "GO"),
        MunicipioParSiconfi("5211800", "Jaraguá", "GO"),
        MunicipioParSiconfi("5218003", "Porangatu", "GO"),
        MunicipioParSiconfi("5221601", "Uruaçu", "GO"),
        MunicipioParSiconfi("5206206", "Cristalina", "GO"),
    ),
}


class ComparativoSiconfiRegistro(BaseModel):
    model_config = ConfigDict(frozen=True)

    comparativo_id: str
    municipio_id: str
    codigo_ibge: str
    ente_nome: str
    uf: str
    eh_municipio_foco: bool
    ano: int
    anexo_siconfi: str = "DCA-Anexo I-E"
    funcao_codigo: str = "01"
    funcao_descricao: str = "01 - Legislativa"
    populacao_siconfi: int | None
    despesa_empenhada: Decimal | None
    despesa_liquidada: Decimal | None
    despesa_paga: Decimal | None
    despesa_paga_per_capita_ano: Decimal | None
    despesa_paga_per_capita_mes: Decimal | None
    fonte_id: str = "siconfi_stn"
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str = VERSAO_COLETOR_SICONFI


class LayoutSiconfiAlteradoError(ValueError):
    """Sinaliza alteração inesperada no contrato JSON da API SICONFI."""


def _para_decimal(valor: Any) -> Decimal | None:
    if valor is None or valor == "":
        return None
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_dca_funcao_legislativa(
    payload: dict[str, Any],
    *,
    municipio_id: str,
    par: MunicipioParSiconfi,
    ano: int,
    populacao_ente: int | None,
    fonte_url: str,
    coletado_em: datetime,
    hash_conteudo: str,
) -> ComparativoSiconfiRegistro:
    """Extrai exclusivamente a conta consolidada '01 - Legislativa' do DCA-Anexo I-E."""
    if not isinstance(payload, dict) or "items" not in payload or not isinstance(payload["items"], list):
        raise LayoutSiconfiAlteradoError("Payload SICONFI DCA sem chave 'items' em formato de lista.")

    empenhada: Decimal | None = None
    liquidada: Decimal | None = None
    paga: Decimal | None = None
    pop_item: int | None = populacao_ente

    for item in payload["items"]:
        conta = str(item.get("conta") or "").strip()
        # Somente a função agregadora '01 - Legislativa' (exclui subfunções como '01.031 - Ação Legislativa')
        if conta != "01 - Legislativa":
            continue
        if item.get("populacao") is not None:
            try:
                pop_item = int(item["populacao"])
            except (TypeError, ValueError):
                pass
        coluna = str(item.get("coluna") or "").strip().lower()
        val = _para_decimal(item.get("valor"))
        if coluna == "despesas empenhadas":
            empenhada = val
        elif coluna == "despesas liquidadas":
            liquidada = val
        elif coluna == "despesas pagas":
            paga = val

    per_capita_ano: Decimal | None = None
    per_capita_mes: Decimal | None = None
    if paga is not None and pop_item is not None and pop_item > 0:
        per_capita_ano = (paga / Decimal(pop_item)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        per_capita_mes = (paga / Decimal(pop_item) / Decimal(12)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return ComparativoSiconfiRegistro(
        comparativo_id=f"{municipio_id}-siconfi-{par.codigo_ibge}-{ano}",
        municipio_id=municipio_id,
        codigo_ibge=par.codigo_ibge,
        ente_nome=par.nome,
        uf=par.uf,
        eh_municipio_foco=par.eh_foco,
        ano=ano,
        populacao_siconfi=pop_item,
        despesa_empenhada=empenhada,
        despesa_liquidada=liquidada,
        despesa_paga=paga,
        despesa_paga_per_capita_ano=per_capita_ano,
        despesa_paga_per_capita_mes=per_capita_mes,
        fonte_url=fonte_url,
        coletado_em=coletado_em,
        hash_conteudo=hash_conteudo,
    )


def _requisitar_json_com_retentativa(
    client: httpx.Client,
    url: str,
    params: dict[str, Any] | None = None,
    tentativas: int = 3,
) -> tuple[bytes, int, str]:
    ultimo_erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = client.get(url, params=params)
            if resp.status_code in (429, 500, 502, 503, 504) and tentativa < tentativas:
                time.sleep(1.5 * tentativa)
                continue
            resp.raise_for_status()
            return resp.content, resp.status_code, str(resp.url)
        except Exception as exc:  # noqa: BLE001
            ultimo_erro = exc
            if tentativa < tentativas:
                time.sleep(1.5 * tentativa)
    raise RuntimeError(f"Falha ao consultar SICONFI {url}: {ultimo_erro}") from ultimo_erro


def coletar_e_persistir_siconfi(
    conn: psycopg.Connection[Any],
    *,
    repo_root: Path,
    municipio_id: str = "inhumas-go",
    anos: tuple[int, ...] = (2024, 2025),
    crawl_delay_seg: float = 1.0,
) -> dict[str, Any]:
    """Coleta dados oficiais SICONFI DCA-Anexo I-E, grava bruto SHA-256 e persiste no PostgreSQL 16."""
    pares = MUNICIPIOS_PARES_POR_MUNICIPIO.get(municipio_id)
    if not pares:
        raise ValueError(f"Nenhum município par configurado para '{municipio_id}'.")

    raw_dir = repo_root / "data" / "raw" / municipio_id / "siconfi"
    raw_dir.mkdir(parents=True, exist_ok=True)
    execucao_id = str(uuid4())
    iniciado_em = datetime.now(UTC)
    registros: list[ComparativoSiconfiRegistro] = []
    documentos: list[dict[str, Any]] = []
    populacoes_entes: dict[str, int] = {}

    with httpx.Client(headers={"User-Agent": USER_AGENT_PADRAO}, timeout=30.0) as client:
        # 1. Lista de entes oficiais para validar população
        bytes_entes, status_entes, url_entes = _requisitar_json_com_retentativa(
            client, f"{SICONFI_BASE_URL}/entes"
        )
        hash_entes = hashlib.sha256(bytes_entes).hexdigest()
        caminho_entes = raw_dir / f"entes_{hash_entes[:16]}.json"
        caminho_entes.write_bytes(bytes_entes)
        coletado_entes = datetime.now(UTC)
        payload_entes = json.loads(bytes_entes.decode("utf-8"))
        for item in payload_entes.get("items", []):
            cod = str(item.get("cod_ibge") or "").strip()
            if cod and item.get("populacao") is not None:
                try:
                    populacoes_entes[cod] = int(item["populacao"])
                except (TypeError, ValueError):
                    pass
        documentos.append(
            {
                "documento_id": str(uuid5(NAMESPACE_URL, f"{municipio_id}:siconfi_stn:{hash_entes}:{url_entes}")),
                "fonte_url": url_entes,
                "coletado_em": coletado_entes,
                "hash_conteudo": hash_entes,
                "caminho": str(caminho_entes.relative_to(repo_root / "data" / "raw")).replace("\\", "/"),
                "tamanho_bytes": len(bytes_entes),
                "status_http": status_entes,
            }
        )

        # 2. DCA-Anexo I-E para cada município par e ano
        for ano in anos:
            for par in pares:
                time.sleep(max(0.5, crawl_delay_seg))
                raw_bytes, status_http, url_final = _requisitar_json_com_retentativa(
                    client,
                    f"{SICONFI_BASE_URL}/dca",
                    params={
                        "an_exercicio": ano,
                        "no_anexo": "DCA-Anexo I-E",
                        "id_ente": par.codigo_ibge,
                    },
                )
                h = hashlib.sha256(raw_bytes).hexdigest()
                arq = raw_dir / f"dca_{ano}_{par.codigo_ibge}_{h[:16]}.json"
                arq.write_bytes(raw_bytes)
                coletado_em = datetime.now(UTC)
                doc_id = str(uuid5(NAMESPACE_URL, f"{municipio_id}:siconfi_stn:{h}:{url_final}"))
                documentos.append(
                    {
                        "documento_id": doc_id,
                        "fonte_url": url_final,
                        "coletado_em": coletado_em,
                        "hash_conteudo": h,
                        "caminho": str(arq.relative_to(repo_root / "data" / "raw")).replace("\\", "/"),
                        "tamanho_bytes": len(raw_bytes),
                        "status_http": status_http,
                    }
                )
                payload = json.loads(raw_bytes.decode("utf-8"))
                reg = parse_dca_funcao_legislativa(
                    payload,
                    municipio_id=municipio_id,
                    par=par,
                    ano=ano,
                    populacao_ente=populacoes_entes.get(par.codigo_ibge),
                    fonte_url=url_final,
                    coletado_em=coletado_em,
                    hash_conteudo=h,
                )
                validar_ausencia_cpf_em_valores(reg.model_dump(mode="json"), contexto="comparativo_siconfi")
                registros.append(reg)

    finalizado_em = datetime.now(UTC)
    doc_por_hash = {d["hash_conteudo"]: d["documento_id"] for d in documentos}
    resumo_persist = persistir_comparativo_siconfi_postgres(
        conn,
        municipio_id=municipio_id,
        execucao_id=execucao_id,
        iniciado_em=iniciado_em,
        finalizado_em=finalizado_em,
        documentos=documentos,
        registros=registros,
        doc_por_hash=doc_por_hash,
    )

    manifesto = {
        "execucao_id": execucao_id,
        "municipio_id": municipio_id,
        "anos": list(anos),
        "versao_coletor": VERSAO_COLETOR_SICONFI,
        "iniciado_em": iniciado_em.isoformat(),
        "finalizado_em": finalizado_em.isoformat(),
        "total_requisicoes": len(documentos),
        "total_registros": len(registros),
        "persistencia": resumo_persist,
    }
    (raw_dir / f"manifesto_{execucao_id}.json").write_text(
        json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifesto


def persistir_comparativo_siconfi_postgres(
    conn: psycopg.Connection[Any],
    *,
    municipio_id: str,
    execucao_id: str,
    iniciado_em: datetime,
    finalizado_em: datetime,
    documentos: list[dict[str, Any]],
    registros: list[ComparativoSiconfiRegistro],
    doc_por_hash: dict[str, str],
) -> dict[str, int]:
    """Persiste execução, documentos brutos e tabela comparativo_legislativo_siconfi de forma idempotente."""
    novos = 0
    alterados = 0
    inalterados = 0

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO coleta_execucao (
                execucao_id, municipio_id, fonte_id, versao_coletor,
                iniciado_em, finalizado_em, status, registros_lidos
            )
            VALUES (%s, %s, 'siconfi_stn', %s, %s, %s, 'SUCESSO', %s)
            ON CONFLICT (execucao_id) DO NOTHING
            """,
            (execucao_id, municipio_id, VERSAO_COLETOR_SICONFI, iniciado_em, finalizado_em, len(registros)),
        )

        for d in documentos:
            cur.execute(
                """
                INSERT INTO documento_bruto (
                    documento_id, municipio_id, fonte_id, execucao_id, fonte_url,
                    coletado_em, hash_conteudo, versao_coletor, storage_backend,
                    caminho_armazenamento, mime_type, tamanho_bytes, status_http
                )
                VALUES (%s, %s, 'siconfi_stn', %s, %s, %s, %s, %s, 'local', %s, 'application/json', %s, %s)
                ON CONFLICT (municipio_id, fonte_id, hash_conteudo, fonte_url) DO NOTHING
                """,
                (
                    d["documento_id"],
                    municipio_id,
                    execucao_id,
                    d["fonte_url"],
                    d["coletado_em"],
                    d["hash_conteudo"],
                    VERSAO_COLETOR_SICONFI,
                    d["caminho"],
                    d["tamanho_bytes"],
                    d["status_http"],
                ),
            )

        for r in registros:
            cur.execute(
                """
                SELECT hash_conteudo FROM comparativo_legislativo_siconfi
                WHERE municipio_id = %s AND codigo_ibge = %s AND ano = %s
                """,
                (r.municipio_id, r.codigo_ibge, r.ano),
            )
            atual = cur.fetchone()
            doc_id = doc_por_hash.get(r.hash_conteudo)
            if atual is None:
                novos += 1
            elif str(atual[0]).strip() == r.hash_conteudo:
                inalterados += 1
            else:
                alterados += 1

            cur.execute(
                """
                INSERT INTO comparativo_legislativo_siconfi (
                    comparativo_id, municipio_id, codigo_ibge, ente_nome, uf,
                    eh_municipio_foco, ano, anexo_siconfi, funcao_codigo, funcao_descricao,
                    populacao_siconfi, despesa_empenhada, despesa_liquidada, despesa_paga,
                    despesa_paga_per_capita_ano, despesa_paga_per_capita_mes,
                    documento_bruto_id, fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (municipio_id, codigo_ibge, ano) DO UPDATE SET
                    ente_nome = EXCLUDED.ente_nome,
                    uf = EXCLUDED.uf,
                    eh_municipio_foco = EXCLUDED.eh_municipio_foco,
                    populacao_siconfi = EXCLUDED.populacao_siconfi,
                    despesa_empenhada = EXCLUDED.despesa_empenhada,
                    despesa_liquidada = EXCLUDED.despesa_liquidada,
                    despesa_paga = EXCLUDED.despesa_paga,
                    despesa_paga_per_capita_ano = EXCLUDED.despesa_paga_per_capita_ano,
                    despesa_paga_per_capita_mes = EXCLUDED.despesa_paga_per_capita_mes,
                    documento_bruto_id = COALESCE(EXCLUDED.documento_bruto_id, comparativo_legislativo_siconfi.documento_bruto_id),
                    fonte_url = EXCLUDED.fonte_url,
                    coletado_em = EXCLUDED.coletado_em,
                    hash_conteudo = EXCLUDED.hash_conteudo,
                    versao_coletor = EXCLUDED.versao_coletor
                """,
                (
                    r.comparativo_id,
                    r.municipio_id,
                    r.codigo_ibge,
                    r.ente_nome,
                    r.uf,
                    r.eh_municipio_foco,
                    r.ano,
                    r.anexo_siconfi,
                    r.funcao_codigo,
                    r.funcao_descricao,
                    r.populacao_siconfi,
                    r.despesa_empenhada,
                    r.despesa_liquidada,
                    r.despesa_paga,
                    r.despesa_paga_per_capita_ano,
                    r.despesa_paga_per_capita_mes,
                    doc_id,
                    r.fonte_id,
                    r.fonte_url,
                    r.coletado_em,
                    r.hash_conteudo,
                    r.versao_coletor,
                ),
            )

        cur.execute(
            """
            UPDATE coleta_execucao
            SET registros_novos = %s, registros_alterados = %s, registros_inalterados = %s
            WHERE execucao_id = %s
            """,
            (novos, alterados, inalterados, execucao_id),
        )
        conn.commit()

    return {"lidos": len(registros), "novos": novos, "alterados": alterados, "inalterados": inalterados}
