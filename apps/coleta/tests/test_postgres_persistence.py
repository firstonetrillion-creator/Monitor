"""Testes automatizados da persistência PostgreSQL 16 (idempotência, integridade referencial, NULLs e LGPD)."""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from cerrado_aberto_coleta.nexlegis.postgres_loader import (
    PostgresNexlegisRepository,
    ViolacaoLGPDError,
    carregar_bienio_2025_2026_no_postgres,
    validar_ausencia_cpf_em_valores,
)
from cerrado_aberto_coleta.nexlegis.schemas import VereadorRegistro

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def pg_conn(pg_uri: str):
    """Conecta ao cluster PostgreSQL 16 local (data/pgdata) e garante carga do biênio 2025–2026."""
    with psycopg.connect(pg_uri, row_factory=dict_row) as conn:
        yield conn


def test_persistencia_bienio_2025_2026_e_reexecucao_100_porcento_idempotente(pg_conn) -> None:
    """Carrega os dados de 2025 (Lote 2) e 2026 (Lote 1) no PostgreSQL 16 e comprova reexecução com novos=0 e alterados=0."""
    rel_1 = carregar_bienio_2025_2026_no_postgres(pg_conn, REPO_ROOT)
    totais = rel_1["lote2_2025"].contagem_total_banco
    assert totais["de_para_tipo_proposicao"] == 21
    assert totais["coleta_execucao"] >= 2  # 2 lotes históricos + execuções incrementais semanais
    assert totais["documento_bruto"] >= 269
    assert totais["vereador"] == 32
    assert totais["vereador_alias"] >= 66
    assert totais["mandato"] == 16
    assert totais["sessao"] >= 133  # 73 (2025) + >=60 (2026)
    assert totais["presenca"] >= 1995  # 1095 (2025) + >=900 (2026)
    assert totais["proposicao"] >= 1295  # 717 (2025) + >=578 (2026 + incrementais)
    assert totais["autoria"] >= 1891  # 1013 (2025) + >=878 (2026)
    assert totais["tramitacao"] >= 1286  # 717 (2025) + >=569 (2026)
    assert totais["pauta_item"] >= 1680  # 942 (2025) + >=738 (2026)
    assert totais["votacao"] >= 1600  # 874 (2025) + >=726 (2026)
    assert totais["voto"] >= 7990  # 5545 (2025) + >=2445 (2026)

    # Reexecução imediata: nenhuma tabela em nenhum dos dois lotes pode criar novos registros nem alterar existentes
    rel_2 = carregar_bienio_2025_2026_no_postgres(pg_conn, REPO_ROOT)
    for lote_chave, rel_lote in rel_2.items():
        for nome_tabela, metricas in rel_lote.por_tabela.items():
            assert metricas["novos"] == 0, f"[{lote_chave}] Tabela {nome_tabela} inseriu registros na reexecução: {metricas}"
            assert metricas["alterados"] == 0, f"[{lote_chave}] Tabela {nome_tabela} alterou registros na reexecução: {metricas}"
            assert metricas["inalterados"] == metricas["lidos"]


def test_integridade_referencial_e_proveniencia_no_postgres(pg_conn) -> None:
    """Verifica relacionamentos, chaves estrangeiras e presença de proveniência em todas as linhas de 2025 e 2026."""
    with pg_conn.cursor() as cur:
        # 1. Nenhuma sessão fora de {2025, 2026} deve estar persistida (Lote 3 2020-2024 não foi iniciado)
        cur.execute("SELECT COUNT(*) AS c FROM sessao WHERE ano NOT IN (2025, 2026)")
        assert cur.fetchone()["c"] == 0

        cur.execute("SELECT ano, COUNT(*) AS c FROM sessao GROUP BY ano ORDER BY ano")
        sessoes_por_ano = {r["ano"]: r["c"] for r in cur.fetchall()}
        assert set(sessoes_por_ano.keys()) == {2025, 2026}
        assert sessoes_por_ano[2025] == 73
        assert sessoes_por_ano[2026] >= 60

        # 2. Todas as 717 matérias de 2025 (643 parlamentares + 74 administrativas) e >=571 de 2026 estão presentes
        cur.execute(
            """
            SELECT
                ano,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE eh_proposicao_parlamentar = TRUE) AS parlamentares,
                COUNT(*) FILTER (WHERE eh_proposicao_parlamentar = FALSE) AS administrativas
            FROM proposicao
            WHERE ano IN (2025, 2026)
            GROUP BY ano
            ORDER BY ano
            """
        )
        rows_p = {r["ano"]: r for r in cur.fetchall()}
        assert rows_p[2025]["total"] == 717
        assert rows_p[2025]["parlamentares"] == 643
        assert rows_p[2025]["administrativas"] == 74
        assert rows_p[2026]["total"] >= 571
        assert rows_p[2026]["parlamentares"] >= 509
        assert rows_p[2026]["administrativas"] >= 62
        assert rows_p[2026]["parlamentares"] + rows_p[2026]["administrativas"] == rows_p[2026]["total"]

        # 3. View analítica vw_producao_legislativa_vereador exclui Atas (144 e 145), Vetos (14 e 210), Julgamentos (211) e Balanços (213)
        cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM vw_producao_legislativa_vereador
            WHERE tipo_id_origem IN (14, 144, 145, 210, 211, 213, 375)
            """
        )
        assert cur.fetchone()["c"] == 0

        # 4. Verifica proveniência não nula e hash SHA-256 de 64 caracteres
        for tabela in ("vereador", "sessao", "presenca", "proposicao", "autoria", "tramitacao", "pauta_item", "votacao", "voto"):
            cur.execute(
                f"""
                SELECT COUNT(*) AS invalidos
                FROM {tabela}
                WHERE fonte_url IS NULL
                   OR coletado_em IS NULL
                   OR LENGTH(TRIM(hash_conteudo)) <> 64
                   OR versao_coletor IS NULL
                """
            )
            assert cur.fetchone()["invalidos"] == 0, f"Proveniência inválida em {tabela}"


def test_preservacao_estrita_de_null_para_dados_ausentes(pg_conn) -> None:
    """Garante que campos ausentes na fonte permanecem NULL no PostgreSQL e nunca viram zero ou string vazia."""
    with pg_conn.cursor() as cur:
        # Vereador TCHULÃO (id 148) não tem nome_civil, biografia, partido nem votos_eleicao na API
        cur.execute(
            """
            SELECT v.nome_civil, v.biografia_html, v.biografia_texto, m.partido_id, m.votos_eleicao, m.cargo_mesa
            FROM vereador v
            JOIN mandato m ON m.vereador_id = v.vereador_id
            WHERE v.id_origem_nexlegis = 148
            """
        )
        row = cur.fetchone()
        assert row is not None
        assert row["biografia_html"] is None
        assert row["biografia_texto"] is None
        assert row["partido_id"] is None
        assert row["votos_eleicao"] is None
        assert row["cargo_mesa"] is None

        # Sessões sem mídia/ata em midias[] devem manter ata_pdf_url = NULL (>=11 em 2026) e nunca string vazia
        cur.execute("SELECT COUNT(*) AS c FROM sessao WHERE ano = 2026 AND ata_pdf_url IS NULL")
        assert cur.fetchone()["c"] >= 11
        cur.execute("SELECT COUNT(*) AS c FROM sessao WHERE ata_pdf_url = ''")
        assert cur.fetchone()["c"] == 0

        # Mandatos sem votos_eleicao devem permanecer NULL (nunca 0)
        cur.execute("SELECT COUNT(*) AS c FROM mandato WHERE votos_eleicao = 0")
        assert cur.fetchone()["c"] == 0

        # Proposições sem anexo_principal_url ou anexo_principal_nome permanecem NULL (nunca string vazia)
        cur.execute("SELECT COUNT(*) AS c FROM proposicao WHERE anexo_principal_url = '' OR anexo_principal_nome = ''")
        assert cur.fetchone()["c"] == 0


def test_bloqueio_lgpd_impede_persistir_cpf_completo(pg_conn) -> None:
    """Garante que tentar persistir qualquer registro contendo CPF completo levanta ViolacaoLGPDError."""
    with pytest.raises(ViolacaoLGPDError):
        validar_ausencia_cpf_em_valores(
            {"nome_civil": "João da Silva CPF 123.456.789-00"},
            contexto="vereador",
        )

    repo = PostgresNexlegisRepository(pg_conn)
    ver_com_cpf = VereadorRegistro(
        vereador_id="inhumas-go-ver-99999",
        municipio_id="inhumas-go",
        id_origem_nexlegis=99999,
        nome_civil="Teste CPF 111.222.333-44",
        nome_politico="TESTE LGPD",
        nome_exibicao="Teste LGPD",
        slug="teste-lgpd",
        chave_busca="teste lgpd",
        fonte_id="nexlegis",
        fonte_url="https://inhumas.nexlegis.com.br/api/vereadores",
        coletado_em="2026-11-12T00:00:00+00:00",
        hash_conteudo="a" * 64,
        versao_coletor="cerrado-aberto-coleta/0.1.0",
    )
    with pytest.raises(ViolacaoLGPDError):
        repo.carregar_vereadores([ver_com_cpf])
