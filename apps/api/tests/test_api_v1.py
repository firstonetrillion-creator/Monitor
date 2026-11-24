"""Testes automatizados dos endpoints da API FastAPI v1 (paginação, filtros, relacionamentos e LGPD)."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from pathlib import Path

import pgserver
import psycopg
import pytest
from cerrado_aberto_coleta.nexlegis.postgres_loader import (
    carregar_bienio_2025_2026_no_postgres,
)
from cerrado_aberto_coleta.transparencia.postgres_loader import (
    persistir_lote_transparencia_2026_no_postgres,
)
from fastapi.testclient import TestClient

from cerrado_aberto_api.db import configurar_uri_banco
from cerrado_aberto_api.main import app
from cerrado_aberto_api.security import FiltroLogLGPD, sanitizar_estrutura_lgpd

REPO_ROOT = Path(__file__).resolve().parents[3]
_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Inicializa o banco PostgreSQL 16 local com os dados de 2025–2026 e retorna um TestClient FastAPI."""
    pgdata_dir = REPO_ROOT / "data" / "pgdata"
    pgdata_dir.mkdir(parents=True, exist_ok=True)
    srv = pgserver.get_server(str(pgdata_dir))
    uri = str(srv.get_uri())
    with psycopg.connect(uri) as conn:
        carregar_bienio_2025_2026_no_postgres(conn, REPO_ROOT)
        persistir_lote_transparencia_2026_no_postgres(
            conn=conn,
            diretorio_raiz_lote=REPO_ROOT
            / "data"
            / "raw"
            / "inhumas-go"
            / "transparencia_centi"
            / "2026",
            caminho_migracao_0001=REPO_ROOT
            / "db"
            / "migrations"
            / "0001_init_core_and_nexlegis.sql",
            caminho_migracao_0002=REPO_ROOT
            / "db"
            / "migrations"
            / "0002_init_transparencia_and_custo_mandato.sql",
        )
    configurar_uri_banco(uri)
    return TestClient(app)


def test_health_endpoint_e_contagens_2025_2026(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["status"] == "ok"
    assert dados["plataforma"] == "Cerrado Aberto"
    assert dados["modo_acesso"] == "SOMENTE_LEITURA"
    assert "PostgreSQL 16" in dados["versao_postgresql"]
    assert dados["contagens_persistidas"]["vereador"] == 32
    assert dados["contagens_persistidas"]["sessao"] >= 133  # 73 (2025) + >=60 (2026, cresce na coleta semanal)
    assert dados["contagens_persistidas"]["presenca"] >= 1995  # 1095 (2025) + >=900 (2026)
    assert dados["contagens_persistidas"]["proposicao"] >= 1295  # 717 (2025) + >=578 (2026 + incrementais)
    assert dados["contagens_persistidas"]["voto"] >= 7990  # 5545 (2025) + >=2445 (2026)
    assert len(dados["lacunas_historicas_documentadas"]) == 2
    assert not _RE_CPF.search(resp.text)


def test_vereadores_listagem_paginacao_e_filtros(client: TestClient) -> None:
    # 1. Listagem padrão paginada
    r1 = client.get("/api/v1/vereadores?page=1&per_page=10")
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["page"] == 1
    assert b1["per_page"] == 10
    assert b1["total"] == 32
    assert b1["total_pages"] == 4
    assert len(b1["items"]) == 10
    assert "proveniencia" in b1["items"][0]
    assert len(b1["items"][0]["proveniencia"]["hash_conteudo"]) == 64

    # 2. Filtro apenas_legislatura_atual=true (15 titulares + 1 suplente = 16)
    r_atual = client.get("/api/v1/vereadores?apenas_legislatura_atual=true&per_page=50")
    assert r_atual.status_code == 200
    assert r_atual.json()["total"] == 16

    # 3. Filtro por condição TITULAR (15) e SUPLENTE (1)
    r_tit = client.get("/api/v1/vereadores?condicao=TITULAR&per_page=50")
    assert r_tit.status_code == 200
    assert r_tit.json()["total"] == 15

    r_sup = client.get("/api/v1/vereadores?condicao=SUPLENTE&per_page=50")
    assert r_sup.status_code == 200
    assert r_sup.json()["total"] == 1
    assert r_sup.json()["items"][0]["slug"] == "weber-enxovais"

    # 4. Filtro por partido (PL -> 3 vereadores) e busca textual q=kelvy
    r_pl = client.get("/api/v1/vereadores?partido=PL")
    assert r_pl.status_code == 200
    assert r_pl.json()["total"] == 3

    r_q = client.get("/api/v1/vereadores?q=kelvy")
    assert r_q.status_code == 200
    assert r_q.json()["total"] == 1
    assert r_q.json()["items"][0]["id_origem_nexlegis"] == 149
    assert r_q.json()["items"][0]["total_proposicoes_parlamentares_2025"] == 69
    assert r_q.json()["items"][0]["total_proposicoes_parlamentares_2026"] >= 65


def test_vereador_detalhe_por_id_slug_e_preservacao_null(client: TestClient) -> None:
    # Busca por ID numérico (149), ID canônico (inhumas-go-ver-149) e slug (professor-kelvy-fernandes)
    for identificador in ("149", "inhumas-go-ver-149", "professor-kelvy-fernandes"):
        resp = client.get(f"/api/v1/vereadores/{identificador}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["vereador_id"] == "inhumas-go-ver-149"
        assert d["nome_civil"] == "Kelvy Pereira Fernandes"
        assert d["resumo_presenca_2025"]["total_sessoes_registradas"] == 73
        assert d["total_proposicoes_parlamentares_2025"] == 69
        assert d["resumo_presenca_2026"]["total_sessoes_registradas"] >= 60
        assert d["total_proposicoes_parlamentares_2026"] >= 65
        assert len(d["aliases"]) >= 4
        assert len(d["mandatos"]) == 1
        assert len(d["votos_recentes_2025"]) > 0
        assert len(d["votos_recentes_2026"]) > 0
        # Garante que nenhuma Ata (144 ou 145) aparece na produção parlamentar do vereador em 2025 ou 2026
        tipos_prod = {x["tipo_id_origem"] for x in d["producao_por_tipo_2025"] + d["producao_por_tipo_2026"]}
        assert 144 not in tipos_prod
        assert 145 not in tipos_prod

    # Verifica preservação de NULL em campos ausentes (vereador TCHULÃO, id 148)
    r_null = client.get("/api/v1/vereadores/148")
    assert r_null.status_code == 200
    dn = r_null.json()
    assert dn["nome_civil"] == "Julierme Vinícius de Castro Vieira"
    assert dn["biografia_texto"] is None
    assert dn["mandatos"][0]["partido_id"] is None

    # 404 para vereador inexistente
    assert client.get("/api/v1/vereadores/nao-existe-9999").status_code == 404


def test_sessoes_listagem_filtros_e_detalhe_com_votos(client: TestClient) -> None:
    # 1. Listagem de sessões de 2025 (73) e de 2026 (60)
    r_ses_25 = client.get("/api/v1/sessoes?ano=2025&page=1&per_page=15")
    assert r_ses_25.status_code == 200
    bs25 = r_ses_25.json()
    assert bs25["total"] == 73
    assert bs25["total_pages"] == 5

    r_ses = client.get("/api/v1/sessoes?ano=2026&page=1&per_page=15")
    assert r_ses.status_code == 200
    bs = r_ses.json()
    assert bs["total"] >= 60
    assert bs["total_pages"] >= 4
    assert len(bs["items"]) == 15
    assert bs["items"][0]["total_presentes"] + bs["items"][0]["total_ausentes_ou_justificados"] == 15

    # 2. Filtro por intervalo de datas e busca textual
    r_data = client.get("/api/v1/sessoes?data_inicio=2026-11-01&data_fim=2026-11-12")
    assert r_data.status_code == 200
    assert r_data.json()["total"] >= 1

    # 3. Detalhe de sessão de 2025 (710) e de 2026 (969)
    r_det_25 = client.get("/api/v1/sessoes/710")
    assert r_det_25.status_code == 200
    assert r_det_25.json()["ano"] == 2025
    assert len(r_det_25.json()["presencas"]) == 15

    r_det = client.get("/api/v1/sessoes/969")
    assert r_det.status_code == 200
    det = r_det.json()
    assert det["sessao_id"] == "inhumas-go-sessao-969"
    assert len(det["presencas"]) == 15
    assert len(det["pauta_itens"]) > 0
    assert len(det["votacoes"]) > 0
    # Verifica que o placar nominal real é calculado a partir de votos_nominais
    primeira_vot = det["votacoes"][0]
    assert primeira_vot["placar_favoravel"] == len(primeira_vot["votos_nominais"])
    assert not _RE_CPF.search(r_det.text)

    # 404 para sessão inexistente
    assert client.get("/api/v1/sessoes/999999").status_code == 404


def test_materias_listagem_filtros_adr005_e_detalhe(client: TestClient) -> None:
    # 1. Total de matérias de 2025 (717 = 643 parlamentares + 74 administrativas) e de 2026 (571 = 509 + 62)
    r_all_25 = client.get("/api/v1/materias?ano=2025&per_page=10")
    assert r_all_25.status_code == 200
    assert r_all_25.json()["total"] == 717

    r_parl_25 = client.get("/api/v1/materias?ano=2025&eh_proposicao_parlamentar=true&per_page=10")
    assert r_parl_25.status_code == 200
    assert r_parl_25.json()["total"] == 643

    r_adm_25 = client.get("/api/v1/materias?ano=2025&eh_proposicao_parlamentar=false&per_page=10")
    assert r_adm_25.status_code == 200
    assert r_adm_25.json()["total"] == 74

    r_all = client.get("/api/v1/materias?ano=2026&per_page=10")
    assert r_all.status_code == 200
    total_2026 = r_all.json()["total"]
    assert total_2026 >= 571

    # 2. Filtro ADR-005 em 2026: eh_proposicao_parlamentar=true (>=509) vs false (>=62), partição exata
    r_parl = client.get("/api/v1/materias?ano=2026&eh_proposicao_parlamentar=true&per_page=10")
    assert r_parl.status_code == 200
    total_parl_2026 = r_parl.json()["total"]
    assert total_parl_2026 >= 509

    r_adm = client.get("/api/v1/materias?ano=2026&eh_proposicao_parlamentar=false&per_page=10")
    assert r_adm.status_code == 200
    total_adm_2026 = r_adm.json()["total"]
    assert total_adm_2026 >= 62
    assert total_parl_2026 + total_adm_2026 == total_2026

    # 3. Filtro por tipo_id=5 (Requerimento -> >=307 em 2026) e por vereador_id=149 (69 em 2025, >=65 em 2026)
    r_req = client.get("/api/v1/materias?ano=2026&tipo_id=5&per_page=5")
    assert r_req.status_code == 200
    assert r_req.json()["total"] >= 307

    r_ver_25 = client.get("/api/v1/materias?ano=2025&vereador_id=149&eh_proposicao_parlamentar=true")
    assert r_ver_25.status_code == 200
    assert r_ver_25.json()["total"] == 69

    r_ver = client.get("/api/v1/materias?ano=2026&vereador_id=149&eh_proposicao_parlamentar=true")
    assert r_ver.status_code == 200
    assert r_ver.json()["total"] >= 65

    # 4. Detalhe da matéria 2770 (Requerimento 312/2026)
    r_m = client.get("/api/v1/materias/2770")
    assert r_m.status_code == 200
    dm = r_m.json()
    assert dm["proposicao_id"] == "inhumas-go-prop-2770"
    assert dm["eh_proposicao_parlamentar"] is True
    assert dm["contabilizar_producao_vereador"] is True
    assert len(dm["autores"]) >= 1
    assert len(dm["tramitacoes"]) >= 1
    assert len(dm["deliberacoes_em_sessao"]) >= 1
    assert dm["deliberacoes_em_sessao"][0]["placar_favoravel"] == 14

    # 5. Detalhe da matéria administrativa 2771 (ATA DA SESSÃO 042/2026, tipo_id 144)
    r_ata = client.get("/api/v1/materias/2771")
    assert r_ata.status_code == 200
    da = r_ata.json()
    assert da["tipo_id_origem"] == 144
    assert da["eh_proposicao_parlamentar"] is False
    assert da["contabilizar_producao_vereador"] is False


def test_validacao_parametros_bloqueio_escrita_openapi_e_lgpd(client: TestClient) -> None:
    # 1. Validação de parâmetros inválidos (422)
    r_inv = client.get("/api/v1/vereadores?page=0&per_page=999")
    assert r_inv.status_code == 422

    # 2. Caso o usuário envie um CPF num parâmetro inválido que gere erro 422, o handler sanitiza o erro!
    r_cpf_err = client.get("/api/v1/vereadores?condicao=123.456.789-00")
    assert r_cpf_err.status_code == 422
    assert "123.456.789-00" not in r_cpf_err.text
    assert "***.***.***-**" in r_cpf_err.text

    # 3. Bloqueio estrito de operações de escrita (POST, PUT, PATCH, DELETE -> 405)
    for metodo in ("POST", "PUT", "PATCH", "DELETE"):
        resp_w = client.request(metodo, "/api/v1/vereadores")
        assert resp_w.status_code == 405

    # 4. Documentação OpenAPI disponível e completa
    r_oa = client.get("/openapi.json")
    assert r_oa.status_code == 200
    rotas = set(r_oa.json()["paths"].keys())
    assert rotas == {
        "/api/v1/health",
        "/api/v1/vereadores",
        "/api/v1/vereadores/{id}",
        "/api/v1/sessoes",
        "/api/v1/sessoes/{id}",
        "/api/v1/materias",
        "/api/v1/materias/{id}",
        "/api/v1/transparencia/custo-mandato",
        "/api/v1/transparencia/folha",
        "/api/v1/transparencia/despesas",
        "/api/v1/transparencia/despesas/resumo",
        "/api/v1/transparencia/diarias",
        "/api/v1/transparencia/duodecimo",
        "/api/v1/transparencia/declaracoes",
        "/api/v1/boletins/resumo-semanal",
        "/api/v1/busca",
        "/api/v1/bairros",
        "/api/v1/bairros/{slug}",
        "/api/v1/legislacao",
        "/api/v1/legislacao/{id}",
        "/api/v1/comparativo",
    }

    # 5. Teste unitário direto da sanitização LGPD em estruturas e logs
    dados_sujos = {"cpf": "12345678901", "obs": "Doc 111.222.333-44"}
    dados_limpos = sanitizar_estrutura_lgpd(dados_sujos)
    assert dados_limpos == {"cpf": "***.***.***-**", "obs": "Doc ***.***.***-**"}

    filtro_log = FiltroLogLGPD()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="Erro no CPF 999.888.777-66 durante consulta", args=(), exc_info=None
    )
    filtro_log.filter(record)
    assert "999.888.777-66" not in record.msg
    assert "***.***.***-**" in record.msg


def test_integracao_transparencia_2026_e_custo_mandato_na_api(client: TestClient) -> None:
    # 1. Perfil de vereador (Prof. Kelvy Fernandes) integra Nexlegis + Custo da Estrutura do Mandato 2026
    r_kelvy = client.get("/api/v1/vereadores/149")
    assert r_kelvy.status_code == 200
    dk = r_kelvy.json()
    custo = dk["custo_estrutura_mandato_2026"]
    assert custo is not None
    assert custo["ano"] == 2026
    assert custo["competencias_fechadas"] == 10
    assert custo["competencias_abertas_null"] == 2
    assert len(custo["series_mensais"]) == 12
    assert custo["series_mensais"][10]["custo_estrutura_mandato_total"] is None  # Nov/2026 NULL
    assert custo["series_mensais"][11]["custo_estrutura_mandato_total"] is None  # Dez/2026 NULL
    assert (
        "NÃO POSSUI legislação vigente" in custo["nota_cota_parlamentar"]
        or "inexistente" in custo["nota_cota_parlamentar"].lower()
    )

    # 2. Presidente da Câmara (Hugo Pessoni, id 81): lacuna parcial de lotação preserva NULL
    r_hugo = client.get("/api/v1/vereadores/81")
    assert r_hugo.status_code == 200
    dh = r_hugo.json()["custo_estrutura_mandato_2026"]
    assert dh["competencias_lacuna_parcial"] == 10
    assert dh["folha_bruta_gabinete_acumulada"] is None
    assert dh["custo_estrutura_mandato_acumulado"] is None

    # 3. Endpoints dedicados de Transparência 2026
    r_custo = client.get("/api/v1/transparencia/custo-mandato?ano=2026&per_page=50")
    assert r_custo.status_code == 200
    assert r_custo.json()["total"] == 180

    r_folha = client.get("/api/v1/transparencia/folha?ano=2026&mes=10&per_page=100")
    assert r_folha.status_code == 200
    assert r_folha.json()["total"] == 88
    assert all(x["cpf_mascarado"] == "***.***.***-**" for x in r_folha.json()["items"])
    assert not _RE_CPF.search(r_folha.text)

    r_desp = client.get("/api/v1/transparencia/despesas?ano=2026&per_page=50")
    assert r_desp.status_code == 200
    assert r_desp.json()["total"] == 360
    assert not _RE_CPF.search(r_desp.text)

    r_diarias = client.get("/api/v1/transparencia/diarias?ano=2026")
    assert r_diarias.status_code == 200
    assert r_diarias.json()["total"] == 14

    r_duo = client.get("/api/v1/transparencia/duodecimo?ano=2026")
    assert r_duo.status_code == 200
    assert r_duo.json()["total"] == 22

    r_decl = client.get("/api/v1/transparencia/declaracoes")
    assert r_decl.status_code == 200
    assert len(r_decl.json()) == 2

    # 4. Resumo agregado de despesas e filtros novos (período, elemento e totais por favorecido)
    r_res = client.get("/api/v1/transparencia/despesas/resumo?ano=2026")
    assert r_res.status_code == 200
    res_data = r_res.json()
    assert res_data["totais"]["quantidade_empenhos"] == 360
    assert res_data["totais"]["valor_empenhado_liquido"] == "9878324.86"
    assert res_data["totais"]["valor_pago"] == "8873608.80"
    assert len(res_data["por_elemento"]) >= 10
    assert len(res_data["favorecidos"]) >= 50
    fav_pj = [
        f for f in res_data["favorecidos"] if f["tipo_pessoa_favorecido"] == "PESSOA_JURIDICA"
    ]
    assert len(fav_pj) >= 20
    assert all("valor_pago" in f and "documento_favorecido" in f for f in fav_pj)
    soma_pago_favorecidos = sum(Decimal(f["valor_pago"]) for f in res_data["favorecidos"])
    assert soma_pago_favorecidos == Decimal("8873608.80")
    assert not _RE_CPF.search(r_res.text)

    r_inv_data = client.get(
        "/api/v1/transparencia/despesas?data_inicio=2026-05-01&data_fim=2026-04-01"
    )
    assert r_inv_data.status_code == 422

