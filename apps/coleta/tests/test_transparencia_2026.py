"""Testes automatizados do coletor, parser, sanitização LGPD e persistência PostgreSQL 16 (Fase 2 — CENTI 2026)."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from cerrado_aberto_coleta.nexlegis.postgres_loader import (
    ViolacaoLGPDError,
    carregar_bienio_2025_2026_no_postgres,
    validar_ausencia_cpf_em_valores,
)
from cerrado_aberto_coleta.transparencia.lote_2026 import ExecutorLoteTransparencia2026
from cerrado_aberto_coleta.transparencia.parser import sanitizar_csv_despesas_lgpd
from cerrado_aberto_coleta.transparencia.postgres_loader import (
    persistir_lote_transparencia_2026_no_postgres,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
LOTE_2026_DIR = REPO_ROOT / "data" / "raw" / "inhumas-go" / "transparencia_centi" / "2026"
_RE_CPF_COMPLETO_OU_PARCIAL = re.compile(r"\b\d{3}\.[0-9xX]{3}\.[0-9xX]{3}-\d{2}\b")


def test_sanitizacao_lgpd_csv_despesas_mascara_cpfs() -> None:
    amostra = (
        '"Valor Empenhado (Soma):";" 240,00"\n'
        'Empenho;Data;"Saldo a Pagar";Favorecido;CPF/CNPJ;Empenhado;Liquidado;Pago;"Descrição / Histórico";Anulação\n'
        '224943;10/11/2026;0,00;"SERVIDOR TESTE";050.123.456-63;240,00;240,00;240,00;"ADIANTAMENTO";0,00\n'
        '224944;05/11/2026;0,00;"EMPRESA LTDA";48.993.720/0001-21;62,25;62,25;62,25;"COMPRA";0,00\n'
    ).encode()

    limpo_bytes, qtd_mascarados = sanitizar_csv_despesas_lgpd(amostra)
    limpo_texto = limpo_bytes.decode("utf-8")
    assert qtd_mascarados == 1
    assert "050.123.456-63" not in limpo_texto
    assert "***.***.***-**" in limpo_texto
    assert "48.993.720/0001-21" in limpo_texto


def test_arquivos_brutos_2026_sem_cpf_exposto() -> None:
    if not LOTE_2026_DIR.exists():
        pytest.skip("Diretório data/raw de transparência 2026 não encontrado neste ambiente.")

    for arq in LOTE_2026_DIR.rglob("*"):
        if arq.is_file() and arq.suffix in (".csv", ".json"):
            conteudo = arq.read_text(encoding="utf-8")
            assert not _RE_CPF_COMPLETO_OU_PARCIAL.search(conteudo), (
                f"Detectado CPF não mascarado em {arq}"
            )


def test_pacote_2026_reconciliacao_contabil_e_custo_mandato() -> None:
    if not LOTE_2026_DIR.exists():
        pytest.skip("Diretório data/raw de transparência 2026 não encontrado neste ambiente.")

    executor = ExecutorLoteTransparencia2026(diretorio_raiz_lote=LOTE_2026_DIR)
    pacote = executor.carregar_pacote_do_disco()

    assert len(pacote.documentos_brutos) == 14
    assert len(pacote.folha_pagamento) == 939
    assert len(pacote.fornecedores) == 102
    assert len(pacote.despesas_empenhos) == 360
    assert len(pacote.diarias) == 14
    assert len(pacote.duodecimos) == 22
    assert len(pacote.declaracoes) == 2
    assert len(pacote.custos_mandato_mensais) == 180  # 15 vereadores x 12 meses

    # Reconciliação exata das despesas (Linha 0 do CSV oficial)
    emp_bruto = sum(e.valor_empenhado_bruto for e in pacote.despesas_empenhos)
    anulacao = sum(e.valor_anulacao for e in pacote.despesas_empenhos)
    emp_liquido = sum(e.valor_empenhado_liquido for e in pacote.despesas_empenhos)
    liquidado = sum(e.valor_liquidado for e in pacote.despesas_empenhos)
    pago = sum(e.valor_pago for e in pacote.despesas_empenhos)

    assert emp_bruto == Decimal("11122741.47")
    assert anulacao == Decimal("1244416.61")
    assert emp_liquido == Decimal("9878324.86")
    assert liquidado == Decimal("8873608.80")
    assert pago == Decimal("8873608.80")

    # Reconciliação de duodécimo
    repasses = sum(d.valor for d in pacote.duodecimos if d.tipo_natureza == "RECEITA_REPASSE")
    devolucoes = sum(d.valor for d in pacote.duodecimos if d.tipo_natureza == "DEVOLUCAO_DUODECIMO")
    assert repasses == Decimal("9111797.89")
    assert devolucoes == Decimal("99000.00")

    # Competências 11 e 12/2026 devem preservar NULL (nunca 0)
    nov_dez = [c for c in pacote.custos_mandato_mensais if c.mes in (11, 12)]
    assert len(nov_dez) == 30
    assert all(c.competencia_status == "ABERTA_SEM_PUBLICACAO" for c in nov_dez)
    assert all(c.subsidio_bruto_vereador is None for c in nov_dez)
    assert all(c.folha_bruta_gabinete is None for c in nov_dez)
    assert all(c.custo_estrutura_mandato_total is None for c in nov_dez)

    # Presidente da Câmara (Hugo Pessoni, inhumas-go-ver-81): lotação PRESIDENCIA -> folha gabinete NULL
    hugo_fechadas = [
        c
        for c in pacote.custos_mandato_mensais
        if c.vereador_id == "inhumas-go-ver-81" and c.mes <= 10
    ]
    assert len(hugo_fechadas) == 10
    assert all(c.competencia_status == "LACUNA_PARCIAL_LOTACAO" for c in hugo_fechadas)
    assert all(c.folha_bruta_gabinete is None for c in hugo_fechadas)
    assert all(c.custo_estrutura_mandato_total is None for c in hugo_fechadas)
    assert sum(c.diarias_atribuiveis_pagas or Decimal(0) for c in hugo_fechadas) == Decimal(
        "200.00"
    )

    # Jôsy Militão (inhumas-go-ver-147): diária verificável de R$ 1.000,00 em fev/2026
    josy_fev = next(
        c
        for c in pacote.custos_mandato_mensais
        if c.vereador_id == "inhumas-go-ver-147" and c.mes == 2
    )
    assert josy_fev.diarias_atribuiveis_pagas == Decimal("1000.00")
    assert josy_fev.custo_estrutura_mandato_total == (
        josy_fev.subsidio_bruto_vereador + josy_fev.folha_bruta_gabinete + Decimal("1000.00")
    )


def test_persistencia_postgres_transparencia_2026_idempotente(pg_uri: str) -> None:
    if not LOTE_2026_DIR.exists():
        pytest.skip("Diretório data/raw de transparência 2026 não encontrado neste ambiente.")

    with psycopg.connect(pg_uri) as conn:
        carregar_bienio_2025_2026_no_postgres(conn, REPO_ROOT)
        rel = persistir_lote_transparencia_2026_no_postgres(
            conn=conn,
            diretorio_raiz_lote=LOTE_2026_DIR,
            caminho_migracao_0001=REPO_ROOT / "db" / "migrations" / "0001_init_core_and_nexlegis.sql",
            caminho_migracao_0002=REPO_ROOT
            / "db"
            / "migrations"
            / "0002_init_transparencia_and_custo_mandato.sql",
        )

    assert rel.contagem_total_banco["folha_pagamento"] == 939
    assert rel.contagem_total_banco["despesa_empenho"] == 360
    assert rel.contagem_total_banco["diaria"] == 14
    assert rel.contagem_total_banco["receita_duodecimo"] == 22
    assert rel.contagem_total_banco["declaracao_oficial_transparencia"] == 2
    assert rel.contagem_total_banco["custo_estrutura_mandato_mensal"] == 180

    # Reexecução deve ser 100% idempotente (0 novos, 0 alterados)
    for tabela, stats in rel.por_tabela.items():
        assert stats["novos"] == 0, f"Tabela {tabela} teve novos na reexecução"
        assert stats["alterados"] == 0, f"Tabela {tabela} teve alterados na reexecução"

    # Garante que tentativa de persistir CPF completo é bloqueada pela trava LGPD
    with pytest.raises(ViolacaoLGPDError):
        validar_ausencia_cpf_em_valores(
            {"cpf_mascarado": "123.456.789-00"}, contexto="folha_pagamento"
        )
