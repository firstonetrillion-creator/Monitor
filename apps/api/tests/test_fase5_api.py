"""Testes automatizados dos endpoints da Fase 5 (Busca Avançada, Bairros, Legislação, Comparativo SICONFI e Rate Limit)."""

from __future__ import annotations

import os
import re
from decimal import Decimal

from fastapi.testclient import TestClient

from cerrado_aberto_api.main import app
from cerrado_aberto_api.resumos import PALAVRAS_PROIBIDAS_TEXTO_CIDADAO

_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")


def test_busca_unificada_fts_sem_acento_e_filtros() -> None:
    client = TestClient(app)

    # Busca por termo com variação de acento ("asfalto")
    r = client.get("/api/v1/busca?q=asfalto&per_page=10")
    assert r.status_code == 200
    assert "x-ratelimit-limit" in r.headers
    dados = r.json()
    assert dados["total"] > 0
    assert dados["contagem_por_tipo"]["proposicoes"] > 0
    assert len(dados["items"]) > 0
    assert not _RE_CPF.search(r.text)

    # Busca por número exato de lei ("3577") encontra a Lei Ordinária nº 3577/2026
    r_lei = client.get("/api/v1/busca?q=3577&categoria=normas")
    assert r_lei.status_code == 200
    dl = r_lei.json()
    assert dl["contagem_por_tipo"]["normas"] >= 1
    assert any("3577" in it["titulo"] for it in dl["items"])

    # Busca por vereador ("kelvy")
    r_ver = client.get("/api/v1/busca?q=kelvy&categoria=vereadores")
    assert r_ver.status_code == 200
    assert r_ver.json()["contagem_por_tipo"]["vereadores"] >= 1


def test_bairros_painel_e_detalhe_com_transparencia_metodologica() -> None:
    client = TestClient(app)

    r = client.get("/api/v1/bairros")
    assert r.status_code == 200
    dados = r.json()
    assert dados["proposicoes_com_bairro"] >= 200
    assert dados["proposicoes_com_bairro"] + dados["proposicoes_sem_bairro"] == dados["proposicoes_parlamentares_total"]
    assert len(dados["bairros"]) >= 40
    assert len(dados["temas_disponiveis"]) >= 5
    assert not _RE_CPF.search(r.text)

    # Detalhe de um bairro real (Centro)
    r_det = client.get("/api/v1/bairros/centro")
    assert r_det.status_code == 200
    det = r_det.json()
    assert det["bairro"]["nome_oficial"] == "Centro"
    assert det["total"] >= 10
    assert len(det["proposicoes"]) >= 1
    assert all(p["trecho_evidencia"] for p in det["proposicoes"])

    # 404 para bairro inexistente
    assert client.get("/api/v1/bairros/bairro-inexistente-xyz").status_code == 404


def test_legislacao_listagem_filtro_e_detalhe_com_resumo_automatico() -> None:
    client = TestClient(app)

    r = client.get("/api/v1/legislacao?per_page=10")
    assert r.status_code == 200
    dados = r.json()
    assert dados["total"] >= 400
    assert len(dados["categorias_disponiveis"]) >= 3
    assert len(dados["anos_disponiveis"]) >= 5
    assert not _RE_CPF.search(r.text)
    # Nenhuma URL temporária S3 pode vazar na API pública
    assert "amazonaws.com" not in r.text.lower()

    # Detalhe por número de lei (3577)
    r_det = client.get("/api/v1/legislacao/3577")
    assert r_det.status_code == 200
    det = r_det.json()
    assert det["numero"] == "3577"
    assert det["fonte_url"] == "https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id=407"
    assert "Resumo automático" in det["resumo_cidadao"]["rotulo_transparencia"]
    assert len(det["proveniencia"]["hash_conteudo"]) == 64

    assert client.get("/api/v1/legislacao/nao-existe-999999").status_code == 404


def test_comparativo_siconfi_oficial_e_neutralidade_editorial() -> None:
    client = TestClient(app)

    r = client.get("/api/v1/comparativo?ano=2025")
    assert r.status_code == 200
    dados = r.json()
    assert dados["ano_selecionado"] == 2025
    assert set(dados["anos_disponiveis"]) >= {2024, 2025}
    assert len(dados["municipios"]) == 8
    inhumas = next(m for m in dados["municipios"] if m["eh_municipio_foco"])
    assert inhumas["codigo_ibge"] == "5210000"
    assert Decimal(inhumas["despesa_paga"]) == Decimal("9739153.62")
    assert inhumas["variacao_pct_ano_anterior"] is not None
    assert not _RE_CPF.search(r.text)

    # Garante neutralidade absoluta no texto metodológico
    nota_lower = dados["nota_metodologica"].lower()
    for proibida in PALAVRAS_PROIBIDAS_TEXTO_CIDADAO:
        assert proibida not in nota_lower


def test_rate_limit_retorna_429_quando_excedido() -> None:
    client = TestClient(app)
    anterior = os.environ.get("CERRADO_RATE_LIMIT_RPM")
    os.environ["CERRADO_RATE_LIMIT_RPM"] = "3"
    try:
        # Usa IP fictício isolado via X-Forwarded-For para não afetar outros testes
        headers = {"X-Forwarded-For": "198.51.100.77"}
        for _ in range(3):
            ok = client.get("/api/v1/comparativo?ano=2025", headers=headers)
            assert ok.status_code == 200
        bloqueado = client.get("/api/v1/comparativo?ano=2025", headers=headers)
        assert bloqueado.status_code == 429
        assert "retry-after" in bloqueado.headers
    finally:
        if anterior is None:
            os.environ.pop("CERRADO_RATE_LIMIT_RPM", None)
        else:
            os.environ["CERRADO_RATE_LIMIT_RPM"] = anterior
