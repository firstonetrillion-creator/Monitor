"""Testes unitários e de integração do motor de resumos em linguagem simples e boletins (Fase 4)."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from cerrado_aberto_api.main import app
from cerrado_aberto_api.resumos import (
    PALAVRAS_PROIBIDAS_TEXTO_CIDADAO,
    gerar_alerta_whatsapp,
    gerar_resumo_materia,
    gerar_resumo_sessao,
    limpar_ementa_cidada,
)

_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_limpar_ementa_cidada_remove_jargao_e_preserva_siglas() -> None:
    bruta = (
        "REQUER QUE SEJA ENCAMINHADO EXPEDIENTE AO EXCELENTÍSSIMO SENHOR PREFEITO MUNICIPAL "
        "SOLICITANDO MELHORIAS NA UBSF DO SETOR GO-070 E ATENDIMENTO NO SUS."
    )
    limpa = limpar_ementa_cidada(bruta)
    assert limpa.startswith(("Solicita", "Pede"))
    assert "EXCELENTÍSSIMO" not in limpa
    assert "UBSF" in limpa
    assert "SUS" in limpa
    assert "GO-070" in limpa
    # Garante correção de verbo duplicado vindo da fonte oficial ("SOLICITA SOLICITAM ...")
    assert limpar_ementa_cidada("SOLICITA SOLICITAM DA SECRETARIA DE SAÚDE LEVANTAMENTO.").startswith(
        "Solicita da secretaria"
    )


def test_gerar_resumo_materia_traz_selo_automatico_e_3_linhas_neutras() -> None:
    resumo = gerar_resumo_materia(
        nome_materia="Requerimento 326/2026",
        tipo_descricao="Requerimento",
        ementa="REQUER PAVIMENTAÇÃO ASFÁLTICA NO BAIRRO JARDIM AMÉLIA.",
        autores_nomes=["Prof. Kelvy Fernandes"],
        situacao_atual="Aprovado por unanimidade",
        data_referencia=date(2026, 11, 17),
        placar_resumo="Aprovada (15 favoráveis, 0 contrários)",
        fonte_url="https://inhumas.nexlegis.com.br/materias/2786",
        coletado_em=datetime(2026, 11, 19, 0, 56, tzinfo=UTC),
    )

    assert "Resumo automático" in resumo.rotulo_transparencia
    assert resumo.metodo_geracao == "AUTOMATICO_DETERMINISTICO"
    assert resumo.revisado_por_humano is False
    assert "Requerimento" in resumo.o_que_e or "pedido formal" in resumo.o_que_e.lower()
    assert "Jardim" in resumo.o_que_propoe or "pavimentação" in resumo.o_que_propoe.lower()
    assert "Prof. Kelvy Fernandes" in resumo.situacao_e_resultado
    assert resumo.fonte_url == "https://inhumas.nexlegis.com.br/materias/2786"

    texto_completo = (
        f"{resumo.o_que_e} {resumo.o_que_propoe} {resumo.situacao_e_resultado} "
        f"{resumo.texto_resumo_3_linhas}"
    ).lower()
    for proibida in PALAVRAS_PROIBIDAS_TEXTO_CIDADAO:
        assert proibida not in texto_completo


def test_gerar_alerta_whatsapp_respeita_limite_400_caracteres_e_opt_out() -> None:
    resumo_s = gerar_resumo_sessao(
        nome_sessao="Sessão Ordinária 044/2026",
        data_abertura=date(2026, 11, 17),
        total_presentes=15,
        total_faltas_justificadas=0,
        total_ausentes=0,
        total_licencas=0,
        total_proposicoes_parlamentares=11,
        total_votacoes=12,
        contagem_por_tipo={"Requerimento": 10, "Projeto de Lei do Legislativo": 1},
        fonte_url="https://inhumas.nexlegis.com.br/sessoes/1035",
        coletado_em=datetime(2026, 11, 19, 0, 56, tzinfo=UTC),
    )
    alerta = gerar_alerta_whatsapp(
        nome_sessao="Sessão Ordinária 044/2026",
        data_abertura=date(2026, 11, 17),
        total_presentes=15,
        total_proposicoes_parlamentares=11,
        contagem_por_tipo={"Requerimento": 10, "Projeto de Lei do Legislativo": 1},
        url_sessao="https://cerradoaberto.org.br/sessoes/inhumas-go-sessao-1035",
        coletado_em=datetime(2026, 11, 19, 0, 56, tzinfo=UTC),
    )

    assert "Resumo automático" in resumo_s.rotulo_transparencia
    assert len(alerta) <= 400
    assert "Sessão Ordinária 044/2026" in alerta
    assert "17/11/2026" in alerta
    assert "18/11/2026" in alerta  # 2026-11-19T00:56Z equivale a 18/11/2026 em Goiás (UTC-3)
    assert "SAIR" in alerta or "parar" in alerta.lower()
    for proibida in PALAVRAS_PROIBIDAS_TEXTO_CIDADAO:
        assert proibida not in alerta.lower()


def test_endpoint_boletim_semanal_e_resumos_na_api_v1() -> None:
    """Valida contra o banco local PostgreSQL 16 (que já contém a Sessão 044/2026)."""
    client = TestClient(app)

    r_bol = client.get("/api/v1/boletins/resumo-semanal")
    assert r_bol.status_code == 200
    bol = r_bol.json()

    assert bol["nome_sessao"] == "Sessão Ordinária 044/2026"
    assert bol["data_abertura"] == "2026-11-17"
    assert bol["total_presentes"] >= 1
    assert len(bol["alerta_whatsapp"]) <= 400
    assert "@cerradoaberto" in bol["legenda_instagram"]
    assert "Resumo automático" in bol["resumo_sessao"]["rotulo_transparencia"]
    assert len(bol["slides_instagram"]) == 3
    assert Decimal(bol["panorama_financeiro_2026"]["despesa_paga_acumulada"]) == Decimal("8873608.80")
    assert not _RE_CPF.search(r_bol.text)

    # Verifica resumo_cidadao acoplado em GET /api/v1/sessoes/{id} e GET /api/v1/materias/{id}
    r_ses = client.get(f"/api/v1/sessoes/{bol['sessao_id']}")
    assert r_ses.status_code == 200
    assert "Resumo automático" in r_ses.json()["resumo_cidadao"]["rotulo_transparencia"]

    if bol["destaques_pauta"]:
        prop_id = bol["destaques_pauta"][0]["proposicao_id"]
        r_mat = client.get(f"/api/v1/materias/{prop_id}")
        assert r_mat.status_code == 200
        assert "Resumo automático" in r_mat.json()["resumo_cidadao"]["rotulo_transparencia"]
