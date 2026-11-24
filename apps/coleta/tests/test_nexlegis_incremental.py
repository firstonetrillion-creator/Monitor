"""Testes unitários, de idempotência, LGPD e layout quebrado para o coletor incremental semanal do Nexlegis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pgserver
import psycopg
import pytest

from cerrado_aberto_coleta.nexlegis.incremental import (
    ColetorIncrementalNexlegis,
    carregar_incrementais_em_disco_no_postgres,
)
from cerrado_aberto_coleta.nexlegis.parser import LayoutQuebradoError
from cerrado_aberto_coleta.nexlegis.postgres_loader import PostgresNexlegisRepository

REPO_ROOT = Path(__file__).resolve().parents[3]


def _payload_sessoes_pagina1() -> dict[str, Any]:
    return {
        "current_page": 1,
        "last_page": 1,
        "total": 2,
        "data": [
            {
                "id": 1035,
                "numero": "044",
                "ano": 2026,
                "data": "2026-11-17",
                "horario_abertura": "16:00",
                "data_encerramento": "2026-11-17",
                "horario_encerramento": "17:30",
                "tipo_id": 1,
                "tipo": {"id": 1, "descricao": "Ordinária"},
                "nome_sessao": "Sessão Ordinária 044/2026",
                "slug": "sessao-ordinaria-044-2026",
                "quorum": 15,
                "midias": [],
            },
            {
                "id": 1001,
                "numero": "001",
                "ano": 2026,
                "data": "2026-02-03",
                "horario_abertura": "16:00",
                "tipo_id": 1,
                "tipo": {"id": 1, "descricao": "Ordinária"},
                "nome_sessao": "Sessão Ordinária 001/2026",
                "slug": "sessao-ordinaria-001-2026",
                "quorum": 15,
                "midias": [],
            },
        ],
    }


def _payload_sessao_1035_detalhe() -> dict[str, Any]:
    return {
        "id": 1035,
        "numero": "044",
        "ano": 2026,
        "data": "2026-11-17",
        "horario_abertura": "16:00",
        "data_encerramento": "2026-11-17",
        "horario_encerramento": "17:30",
        "tipo_id": 1,
        "tipo": {"id": 1, "descricao": "Ordinária"},
        "nome_sessao": "Sessão Ordinária 044/2026",
        "slug": "sessao-ordinaria-044-2026",
        "quorum": 15,
        "midias": [],
        "presenca": [
            {
                "id": 50001,
                "vereador_id": 149,
                "situacao_id": 1,
                "situacao": {"id": 1, "descricao": "Presente"},
            }
        ],
        "pautas": [
            {
                "id": 60001,
                "ordem": 1,
                "turno": 1,
                "materia_id": 2786,
                "tipo_pauta_id": 2,
                "tipo_pauta": {"id": 2, "descricao": "Ordem do Dia"},
                "unanime": True,
                "has_votos": True,
                "materia": {
                    "id": 2786,
                    "tipo_id": 5,
                    "tipo": {"id": 5, "descricao": "Requerimento"},
                    "numero": "326",
                    "ano": 2026,
                    "nome_materia": "Requerimento 326/2026",
                    "slug": "requerimento-326-2026",
                    "ementa": "Solicita pavimentação na Rua A (contato teste 123.456.789-00).",
                    "data_publicacao": "2026-11-17",
                    "ultima_movimentacao": "2026-11-17",
                    "situacao": "Aprovado por unanimidade",
                },
                "votacao": {
                    "id": 70001,
                    "tipo_turno_id": 1,
                    "unanime": True,
                    "has_votos": True,
                    "votos": [
                        {
                            "id": 80001,
                            "vereador_id": 149,
                            "voto_id": 1,
                            "voto": {"id": 1, "descricao": "Favorável"},
                        }
                    ],
                },
            }
        ],
    }


def _payload_materias_pagina1() -> dict[str, Any]:
    return {
        "current_page": 1,
        "last_page": 1,
        "total": 1,
        "data": [
            {
                "id": 2786,
                "tipo_id": 5,
                "tipo": {"id": 5, "descricao": "Requerimento"},
                "numero": "326",
                "ano": 2026,
                "nome_materia": "Requerimento 326/2026",
                "slug": "requerimento-326-2026",
                "ementa": "Solicita pavimentação na Rua A (contato teste 123.456.789-00).",
                "data_publicacao": "2026-11-17",
                "ultima_movimentacao": "2026-11-17",
                "situacao": "Aprovado por unanimidade",
                "vereadores": [{"vereador_id": 149}],
                "tramitacao": {
                    "id": 90001,
                    "data": "2026-11-17",
                    "local_origem": {"descricao": "Plenário"},
                    "local_destino": {"descricao": "Prefeitura"},
                    "situacao": {"descricao": "Aprovado"},
                },
            }
        ],
    }


def test_coletor_incremental_detecta_delta_sanitiza_lgpd_e_e_idempotente(tmp_path: Path) -> None:
    requisicoes_feitas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requisicoes_feitas.append(str(request.url))
        path = request.url.path
        if path.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if path.endswith("/api/sessoes"):
            return httpx.Response(200, json=_payload_sessoes_pagina1())
        if path.endswith("/api/sessoes/1035"):
            return httpx.Response(200, json=_payload_sessao_1035_detalhe())
        if path.endswith("/api/materias"):
            return httpx.Response(200, json=_payload_materias_pagina1())
        return httpx.Response(404, json={"error": "not found"})

    pg_dir = tmp_path / "pgdata"
    srv = pgserver.get_server(str(pg_dir), cleanup_mode="delete")
    try:
        with psycopg.connect(srv.get_uri()) as conn:
            pg_repo = PostgresNexlegisRepository(conn)
            pg_repo.aplicar_migracao_sql(
                REPO_ROOT / "db" / "migrations" / "0001_init_core_and_nexlegis.sql"
            )
            pg_repo.sincronizar_vocabulario_tipos_proposicao("inhumas-go")

            # Insere o vereador 149 e uma sessão antiga (1001) já existente no banco
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO vereador (
                        vereador_id, municipio_id, id_origem_nexlegis, nome_politico, nome_exibicao,
                        slug, chave_busca, fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                    ) VALUES (
                        'inhumas-go-ver-149', 'inhumas-go', 149, 'Prof. Kelvy Fernandes',
                        'Prof. Kelvy Fernandes', 'prof-kelvy-fernandes', 'kelvy fernandes',
                        'nexlegis', 'https://inhumas.nexlegis.com.br/api/vereadores',
                        NOW(), repeat('a', 64), 'test'
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO sessao (
                        sessao_id, municipio_id, id_origem_nexlegis, tipo_id_origem, tipo_descricao,
                        numero, ano, nome_sessao, slug, data_abertura,
                        fonte_id, fonte_url, coletado_em, hash_conteudo, versao_coletor
                    ) VALUES (
                        'inhumas-go-sessao-1001', 'inhumas-go', 1001, 1, 'Ordinária',
                        '001', 2026, 'Sessão Ordinária 001/2026', 'sessao-ordinaria-001-2026', '2026-02-03',
                        'nexlegis', 'https://inhumas.nexlegis.com.br/api/sessoes/1001',
                        NOW(), repeat('b', 64), 'test'
                    )
                    """
                )
            conn.commit()

            # 1ª Execução: busca apenas a sessão nova 1035 (não baixa 1001 antiga)
            client1 = httpx.Client(transport=httpx.MockTransport(handler))
            coletor1 = ColetorIncrementalNexlegis(
                repo_root=tmp_path,
                municipio_id="inhumas-go",
                ano=2026,
                http_client=client1,
                sleep_fn=lambda _s: None,
                crawl_delay_segundos=0.0,
            )
            rel1 = coletor1.executar(conn)

            assert rel1.sessoes_detalhes_coletados == 1
            assert not any("/api/sessoes/1001" in u for u in requisicoes_feitas)
            assert any("/api/sessoes/1035" in u for u in requisicoes_feitas)
            assert rel1.cpfs_mascarados_total >= 2
            assert rel1.por_tabela["sessao"]["novos"] == 1
            assert rel1.por_tabela["proposicao"]["novos"] == 1
            assert rel1.por_tabela["presenca"]["novos"] == 1
            assert rel1.por_tabela["voto"]["novos"] == 1

            # Verifica que o CPF falso foi mascarado tanto no PostgreSQL quanto no bruto em disco
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ementa FROM proposicao WHERE proposicao_id = 'inhumas-go-prop-2786'"
                )
                row = cur.fetchone()
                assert row is not None
                assert "123.456.789-00" not in row[0]
                assert "***.***.***-**" in row[0]

            # 2ª Execução (idempotência): novos == 0 e alterados == 0
            client2 = httpx.Client(transport=httpx.MockTransport(handler))
            coletor2 = ColetorIncrementalNexlegis(
                repo_root=tmp_path,
                municipio_id="inhumas-go",
                ano=2026,
                http_client=client2,
                sleep_fn=lambda _s: None,
                crawl_delay_segundos=0.0,
            )
            rel2 = coletor2.executar(conn)
            assert rel2.por_tabela["sessao"]["novos"] == 0
            assert rel2.por_tabela["sessao"]["alterados"] == 0
            assert rel2.por_tabela["proposicao"]["novos"] == 0
            assert rel2.por_tabela["proposicao"]["alterados"] == 0

            # Replay offline a partir dos arquivos em disco também deve ser 100% idempotente
            rel_replay = carregar_incrementais_em_disco_no_postgres(conn, tmp_path)
            assert len(rel_replay) >= 1
            assert all(r["por_tabela"]["sessao"]["novos"] == 0 for r in rel_replay)
    finally:
        srv.cleanup()


def test_coletor_incremental_falha_explicita_em_layout_quebrado(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, json={"erro_layout": "campo data ausente"})

    pg_dir = tmp_path / "pgdata_err"
    srv = pgserver.get_server(str(pg_dir), cleanup_mode="delete")
    try:
        with psycopg.connect(srv.get_uri()) as conn:
            pg_repo = PostgresNexlegisRepository(conn)
            pg_repo.aplicar_migracao_sql(
                REPO_ROOT / "db" / "migrations" / "0001_init_core_and_nexlegis.sql"
            )
            client = httpx.Client(transport=httpx.MockTransport(handler))
            coletor = ColetorIncrementalNexlegis(
                repo_root=tmp_path,
                municipio_id="inhumas-go",
                ano=2026,
                http_client=client,
                sleep_fn=lambda _s: None,
                crawl_delay_segundos=0.0,
            )
            with pytest.raises(LayoutQuebradoError):
                coletor.executar(conn)
    finally:
        srv.cleanup()
