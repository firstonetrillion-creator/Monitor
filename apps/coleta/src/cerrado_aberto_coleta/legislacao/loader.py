"""Persistência idempotente da Legislação Municipal no PostgreSQL 16 (ADR-004 / Fase 5)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import psycopg

from cerrado_aberto_coleta.legislacao.parser import (
    VERSAO_COLETOR_LEGISLACAO,
    NormaRegistro,
    parse_pagina_leis_nucleogov,
)
from cerrado_aberto_coleta.nexlegis.postgres_loader import (
    validar_ausencia_cpf_em_valores,
)


def persistir_normas_postgres(
    conn: psycopg.Connection[Any],
    *,
    municipio_id: str,
    normas: list[NormaRegistro],
    documentos_brutos: list[dict[str, Any]],
    execucao_id: str | None = None,
    iniciado_em: datetime | None = None,
    finalizado_em: datetime | None = None,
) -> dict[str, int]:
    """Carrega registros de `norma` e `documento_bruto` de forma 100% idempotente, sem sobrescrever OCR já pronto."""
    exec_id = execucao_id or str(uuid4())
    inicio = iniciado_em or datetime.now(UTC)
    fim = finalizado_em or datetime.now(UTC)

    novos = 0
    alterados = 0
    inalterados = 0
    primeiro_doc_id: str | None = documentos_brutos[0]["documento_id"] if documentos_brutos else None

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO coleta_execucao (
                execucao_id, municipio_id, fonte_id, versao_coletor,
                iniciado_em, finalizado_em, status, registros_lidos
            )
            VALUES (%s, %s, 'legislacao_nucleogov', %s, %s, %s, 'SUCESSO', %s)
            ON CONFLICT (execucao_id) DO NOTHING
            """,
            (exec_id, municipio_id, VERSAO_COLETOR_LEGISLACAO, inicio, fim, len(normas)),
        )

        for d in documentos_brutos:
            cur.execute(
                """
                INSERT INTO documento_bruto (
                    documento_id, municipio_id, fonte_id, execucao_id, fonte_url,
                    coletado_em, hash_conteudo, versao_coletor, storage_backend,
                    caminho_armazenamento, mime_type, tamanho_bytes, status_http
                )
                VALUES (%s, %s, 'legislacao_nucleogov', %s, %s, %s, %s, %s, 'local', %s, %s, %s, %s)
                ON CONFLICT (municipio_id, fonte_id, hash_conteudo, fonte_url) DO NOTHING
                """,
                (
                    d["documento_id"],
                    municipio_id,
                    exec_id,
                    d["fonte_url"],
                    d["coletado_em"],
                    d["hash_conteudo"],
                    VERSAO_COLETOR_LEGISLACAO,
                    d["caminho"],
                    d.get("mime_type", "application/json"),
                    d["tamanho_bytes"],
                    d.get("status_http", 200),
                ),
            )

        for n in normas:
            validar_ausencia_cpf_em_valores(n.model_dump(mode="json"), contexto="norma")
            cur.execute(
                """
                SELECT hash_conteudo FROM norma
                WHERE municipio_id = %s AND tabela_origem = %s AND id_origem = %s
                """,
                (n.municipio_id, n.tabela_origem, n.id_origem),
            )
            atual = cur.fetchone()
            if atual is None:
                novos += 1
            elif str(atual[0]).strip() == n.hash_conteudo:
                inalterados += 1
            else:
                alterados += 1

            cur.execute(
                """
                INSERT INTO norma (
                    norma_id, municipio_id, tabela_origem, id_origem, numero, ano,
                    tipo_norma, categoria_id_origem, categoria_descricao,
                    data_publicacao, data_publicacao_portal, ementa, total_anexos,
                    texto_extraido, status_ocr, extraido_por_ocr, ocr_engine_versao,
                    ocr_confianca_media, requer_revisao_humana, motivo_revisao_humana,
                    documento_bruto_id, fonte_id, fonte_url, coletado_em,
                    hash_conteudo, versao_coletor
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (municipio_id, tabela_origem, id_origem) DO UPDATE SET
                    numero = EXCLUDED.numero,
                    ano = EXCLUDED.ano,
                    tipo_norma = EXCLUDED.tipo_norma,
                    categoria_id_origem = EXCLUDED.categoria_id_origem,
                    categoria_descricao = EXCLUDED.categoria_descricao,
                    data_publicacao = EXCLUDED.data_publicacao,
                    data_publicacao_portal = EXCLUDED.data_publicacao_portal,
                    ementa = EXCLUDED.ementa,
                    total_anexos = EXCLUDED.total_anexos,
                    texto_extraido = COALESCE(EXCLUDED.texto_extraido, norma.texto_extraido),
                    status_ocr = CASE
                        WHEN EXCLUDED.texto_extraido IS NOT NULL THEN EXCLUDED.status_ocr
                        ELSE norma.status_ocr
                    END,
                    extraido_por_ocr = CASE
                        WHEN EXCLUDED.texto_extraido IS NOT NULL THEN EXCLUDED.extraido_por_ocr
                        ELSE norma.extraido_por_ocr
                    END,
                    fonte_url = EXCLUDED.fonte_url,
                    coletado_em = EXCLUDED.coletado_em,
                    hash_conteudo = EXCLUDED.hash_conteudo,
                    versao_coletor = EXCLUDED.versao_coletor
                """,
                (
                    n.norma_id,
                    n.municipio_id,
                    n.tabela_origem,
                    n.id_origem,
                    n.numero,
                    n.ano,
                    n.tipo_norma,
                    n.categoria_id_origem,
                    n.categoria_descricao,
                    n.data_publicacao,
                    n.data_publicacao_portal,
                    n.ementa,
                    n.total_anexos,
                    n.texto_extraido,
                    n.status_ocr,
                    n.extraido_por_ocr,
                    n.ocr_engine_versao,
                    n.ocr_confianca_media,
                    n.requer_revisao_humana,
                    n.motivo_revisao_humana,
                    primeiro_doc_id,
                    n.fonte_id,
                    n.fonte_url,
                    n.coletado_em,
                    n.hash_conteudo,
                    n.versao_coletor,
                ),
            )

        cur.execute(
            """
            UPDATE coleta_execucao
            SET registros_novos = %s, registros_alterados = %s, registros_inalterados = %s
            WHERE execucao_id = %s
            """,
            (novos, alterados, inalterados, exec_id),
        )
        conn.commit()

    return {"lidos": len(normas), "novos": novos, "alterados": alterados, "inalterados": inalterados}


def carregar_paginas_brutas_legislacao_no_postgres(
    conn: psycopg.Connection[Any],
    *,
    diretorio_paginas: Path,
    repo_root: Path,
    municipio_id: str = "inhumas-go",
) -> dict[str, Any]:
    """Lê arquivos JSON paginados salvos em `data/raw/inhumas-go/legislacao/leis/` e carrega no PostgreSQL."""
    import hashlib

    arquivos = sorted(diretorio_paginas.glob("pagina_*.json"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhuma página JSON encontrada em {diretorio_paginas}")

    coletado_em = datetime.now(UTC)
    normas_por_id: dict[tuple[str, int], NormaRegistro] = {}
    docs: list[dict[str, Any]] = []
    total_declarado_max = 0

    for arq in arquivos:
        raw_bytes = arq.read_bytes()
        h = hashlib.sha256(raw_bytes).hexdigest()
        payload = json.loads(raw_bytes.decode("utf-8"))
        total_decl, lista = parse_pagina_leis_nucleogov(
            payload, municipio_id=municipio_id, coletado_em=coletado_em
        )
        total_declarado_max = max(total_declarado_max, total_decl)
        for n in lista:
            normas_por_id[(n.tabela_origem, n.id_origem)] = n

        fonte_url_pag = f"https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis#{arq.stem}"
        docs.append(
            {
                "documento_id": str(uuid5(NAMESPACE_URL, f"{municipio_id}:legislacao_nucleogov:{h}:{fonte_url_pag}")),
                "fonte_url": fonte_url_pag,
                "coletado_em": coletado_em,
                "hash_conteudo": h,
                "caminho": str(arq.relative_to(repo_root / "data" / "raw")).replace("\\", "/"),
                "tamanho_bytes": len(raw_bytes),
                "status_http": 200,
            }
        )

    normas_ordenadas = sorted(normas_por_id.values(), key=lambda x: x.id_origem, reverse=True)
    resumo = persistir_normas_postgres(
        conn,
        municipio_id=municipio_id,
        normas=normas_ordenadas,
        documentos_brutos=docs,
    )
    return {
        "municipio_id": municipio_id,
        "arquivos_lidos": len(arquivos),
        "total_declarado_portal": total_declarado_max,
        "normas_unicas_carregadas": len(normas_ordenadas),
        "persistencia": resumo,
    }
