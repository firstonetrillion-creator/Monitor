"""Testes unitários e de integração da Fase 5 em apps/coleta (Bairros, SICONFI e Legislação/OCR)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from cerrado_aberto_coleta.bairros import (
    classificar_tema_proposicao,
    extrair_bairros_da_ementa,
    popular_bairros_e_vinculos_postgres,
)
from cerrado_aberto_coleta.legislacao.loader import persistir_normas_postgres
from cerrado_aberto_coleta.legislacao.ocr import extrair_texto_pdf_hibrido
from cerrado_aberto_coleta.legislacao.parser import (
    LayoutLegislacaoAlteradoError,
    parse_pagina_leis_nucleogov,
)
from cerrado_aberto_coleta.siconfi.collector import (
    LayoutSiconfiAlteradoError,
    MunicipioParSiconfi,
    parse_dca_funcao_legislativa,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_LEGISLACAO = Path(__file__).resolve().parent / "fixtures" / "legislacao"


def test_extracao_bairros_aliases_temas_e_bloqueio_falsos_positivos() -> None:
    # 1. Alias Setor Central -> centro e tema Trânsito
    v1 = extrair_bairros_da_ementa(
        municipio_id="inhumas-go",
        proposicao_id="inhumas-go-prop-t1",
        ementa="SOLICITA INSTALAÇÃO DE REDUTOR DE VELOCIDADE (QUEBRA MOLAS) NO SETOR CENTRAL.",
    )
    assert len(v1) == 1
    assert v1[0].bairro_slug == "centro"
    assert v1[0].tema_principal == "Trânsito e Sinalização"

    # 2. Falso positivo "Centro Municipal de Educação" e "Parque Infantil" não devem casar bairro
    v_fp = extrair_bairros_da_ementa(
        municipio_id="inhumas-go",
        proposicao_id="inhumas-go-prop-t2",
        ementa="SOLICITA REFORMA DO PARQUE INFANTIL NO CENTRO MUNICIPAL DE EDUCAÇÃO INFANTIL.",
    )
    assert v_fp == []

    # 3. Múltiplos bairros na mesma ementa + classificação Saúde
    v_multi = extrair_bairros_da_ementa(
        municipio_id="inhumas-go",
        proposicao_id="inhumas-go-prop-t3",
        ementa="SOLICITA AMPLIAÇÃO DA UBSF ATENDENDO PARQUE SÃO JORGE E VILA 31 DE MARÇO.",
    )
    assert {v.bairro_slug for v in v_multi} == {"parque-sao-jorge", "vila-31-de-marco"}
    assert all(v.tema_principal == "Saúde" for v in v_multi)

    assert classificar_tema_proposicao("SOLICITA RECAPEAMENTO ASFÁLTICO") == "Infraestrutura e Asfalto"


def test_parse_siconfi_funcao_legislativa_sem_duplicar_subfuncao() -> None:
    payload = {
        "items": [
            {"conta": "01 - Legislativa", "coluna": "Despesas Empenhadas", "valor": 9739153.62, "populacao": 53884},
            {"conta": "01.031 - Ação Legislativa", "coluna": "Despesas Empenhadas", "valor": 9041796.92, "populacao": 53884},
            {"conta": "01 - Legislativa", "coluna": "Despesas Liquidadas", "valor": 9739153.62, "populacao": 53884},
            {"conta": "01 - Legislativa", "coluna": "Despesas Pagas", "valor": 9739153.62, "populacao": 53884},
        ]
    }
    par = MunicipioParSiconfi("5210000", "Inhumas", "GO", eh_foco=True)
    reg = parse_dca_funcao_legislativa(
        payload,
        municipio_id="inhumas-go",
        par=par,
        ano=2025,
        populacao_ente=53884,
        fonte_url="https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?id_ente=5210000",
        coletado_em=datetime(2026, 11, 24, 12, 0, tzinfo=UTC),
        hash_conteudo="a" * 64,
    )
    assert reg.despesa_paga == Decimal("9739153.62")
    assert reg.despesa_paga_per_capita_ano == Decimal("180.74")
    assert reg.despesa_paga_per_capita_mes == Decimal("15.06")

    with pytest.raises(LayoutSiconfiAlteradoError):
        parse_dca_funcao_legislativa(
            {"erro": "layout mudou"},
            municipio_id="inhumas-go",
            par=par,
            ano=2025,
            populacao_ente=53884,
            fonte_url="https://example.invalid",
            coletado_em=datetime(2026, 11, 24, 12, 0, tzinfo=UTC),
            hash_conteudo="b" * 64,
        )


def test_parse_legislacao_fixtures_reais_url_canonica_lgpd_e_layout_quebrado() -> None:
    p1 = json.loads((FIXTURES_LEGISLACAO / "leis_api_page1.json").read_text(encoding="utf-8"))
    p28 = json.loads((FIXTURES_LEGISLACAO / "leis_api_page28_oldest.json").read_text(encoding="utf-8"))
    agora = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)

    total_1, normas_1 = parse_pagina_leis_nucleogov(p1, coletado_em=agora)
    assert total_1 == 406
    assert len(normas_1) == 2
    assert normas_1[0].numero == "3577"
    assert normas_1[0].ano == 2026
    assert normas_1[0].fonte_url == "https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id=407"
    assert "s3." not in normas_1[0].fonte_url.lower()

    total_28, normas_28 = parse_pagina_leis_nucleogov(p28, coletado_em=agora)
    assert total_28 == 406
    assert any(n.categoria_descricao == "Lei Orgânica" and n.ano == 1990 for n in normas_28)

    # Mascaramento preventivo de CPF em ementa
    sujo = {
        "0-x": {
            "total": "1",
            "dados": [
                {
                    "tabela": "leis",
                    "id": "9999",
                    "numero": "9999",
                    "ementa": "CONCEDE TITULO A FULANO CPF 123.456.789-00.",
                    "data_publicacao": "2026-01-01",
                    "categoria_descricao": "Lei Ordinária",
                    "total_anexos": "1",
                }
            ],
        }
    }
    _, limpas = parse_pagina_leis_nucleogov(sujo, coletado_em=agora)
    assert "123.456.789-00" not in limpas[0].ementa
    assert "***.***.***-**" in limpas[0].ementa

    with pytest.raises(LayoutLegislacaoAlteradoError):
        parse_pagina_leis_nucleogov({"sem_dados": {}}, coletado_em=agora)


def test_extracao_pdf_hibrido_com_pdf_minimo_vazio_retorna_pendente_ocr(tmp_path: Path) -> None:
    # Cria PDF válido de 1 página em branco (simula PDF escaneado sem camada de texto nativa)
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >> endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer << /Size 4 /Root 1 0 R >>\nstartxref\n184\n%%EOF\n"
    )
    arq = tmp_path / "escaneado.pdf"
    arq.write_bytes(pdf_bytes)
    res = extrair_texto_pdf_hibrido(arq)
    assert res.total_paginas == 1
    assert res.status_ocr in ("PENDENTE_OCR", "OCR_CONCLUIDO")
    assert res.requer_revisao_humana is True


def test_persistencia_bairros_e_normas_idempotente_no_postgres(pg_uri: str) -> None:
    sql_0003 = (REPO_ROOT / "db" / "migrations" / "0003_fase5_aprofundamento.sql").read_text(encoding="utf-8")
    p1 = json.loads((FIXTURES_LEGISLACAO / "leis_api_page1.json").read_text(encoding="utf-8"))
    _, normas_fx = parse_pagina_leis_nucleogov(p1, coletado_em=datetime(2026, 11, 24, 12, 0, tzinfo=UTC))

    with psycopg.connect(pg_uri) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_0003)
        conn.commit()

        # Idempotência de bairros
        rel_b1 = popular_bairros_e_vinculos_postgres(conn, municipio_id="inhumas-go")
        rel_b2 = popular_bairros_e_vinculos_postgres(conn, municipio_id="inhumas-go")
        assert rel_b1["proposicoes_com_bairro_identificado"] >= 200
        assert rel_b1["total_vinculos_proposicao_bairro"] == rel_b2["total_vinculos_proposicao_bairro"]

        # Idempotência de normas
        persistir_normas_postgres(conn, municipio_id="inhumas-go", normas=normas_fx, documentos_brutos=[])
        res2 = persistir_normas_postgres(conn, municipio_id="inhumas-go", normas=normas_fx, documentos_brutos=[])
        assert res2["novos"] == 0
        assert res2["alterados"] == 0
        assert res2["inalterados"] == len(normas_fx)
