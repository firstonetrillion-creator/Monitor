"""Testes das regras de negócio aprovadas no ADR-005 (Custo da Estrutura do Mandato, LGPD, Entidades e OCR)."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from cerrado_aberto_coleta import NOTA_OFICIAL_CEAP
from cerrado_aberto_coleta.custo_mandato import (
    DiariaItem,
    FolhaServidorItem,
    calcular_custo_estrutura_mandato,
)
from cerrado_aberto_coleta.entidades import (
    ResolvedorVereadores,
    classificar_tipo_proposicao,
)
from cerrado_aberto_coleta.normalizacao import mascarar_documento_lgpd, parse_valor_brl
from cerrado_aberto_coleta.storage import LocalVersionedStorage, ResultadoOCR

FIXTURES_TRANSPARENCIA = Path(__file__).parent / "fixtures" / "transparencia"


def test_custo_estrutura_mandato_formula_e_nota_ceap() -> None:
    """Valida a fórmula Subsídio + Folha Bruta do Gabinete + Diárias Atribuíveis e a nota CEAP (ADR-005)."""
    resolvedor = ResolvedorVereadores(municipio_id="inhumas-go")

    # Resolve lotação real encontrada na fixture folha_pagamento_sample.json
    res_lotacao = resolvedor.resolver_por_nome_ou_lotacao("GAB. DO VEREADOR LEANDRO ESSADO")
    assert res_lotacao.confianca == "ALTA"
    assert res_lotacao.vereador_id == "inhumas-go-ver-9"

    itens_folha = [
        FolhaServidorItem(
            matricula="101",
            nome_servidor="ASSESSOR PARLAMENTAR 1",
            lotacao="GAB. DO VEREADOR LEANDRO ESSADO",
            vereador_id_atribuido=res_lotacao.vereador_id,
            competencia_ano=2026,
            competencia_mes=10,
            proventos_brutos=Decimal("5242.73"),
        ),
        # Duplicidade acidental da mesma matrícula na mesma competência deve ser ignorada!
        FolhaServidorItem(
            matricula="101",
            nome_servidor="ASSESSOR PARLAMENTAR 1",
            lotacao="GAB. DO VEREADOR LEANDRO ESSADO",
            vereador_id_atribuido=res_lotacao.vereador_id,
            competencia_ano=2026,
            competencia_mes=10,
            proventos_brutos=Decimal("5242.73"),
        ),
        # Servidor cuja lotação encerrou antes de outubro/2026 não deve entrar
        FolhaServidorItem(
            matricula="102",
            nome_servidor="EX-ASSESSOR",
            lotacao="GAB. DO VEREADOR LEANDRO ESSADO",
            vereador_id_atribuido=res_lotacao.vereador_id,
            competencia_ano=2026,
            competencia_mes=10,
            proventos_brutos=Decimal("3000.00"),
            vigencia_fim=date(2026, 9, 30),
        ),
    ]

    itens_diarias = [
        # Diária sem identificação documental verificável não pode ser atribuída
        DiariaItem(
            diaria_id="d-1",
            beneficiario_nome="Indefinido",
            vereador_id_verificado="inhumas-go-ver-9",
            identificacao_documental_verificavel=False,
            data_pagamento=date(2026, 10, 15),
            valor_empenhado_liquido=Decimal("500.00"),
            valor_liquidado=Decimal("500.00"),
            valor_pago=Decimal("500.00"),
        ),
        # Diária verificável
        DiariaItem(
            diaria_id="d-2",
            beneficiario_nome="LEANDRO VIEIRA ESSADO",
            vereador_id_verificado="inhumas-go-ver-9",
            identificacao_documental_verificavel=True,
            data_pagamento=date(2026, 10, 20),
            valor_empenhado_liquido=Decimal("450.00"),
            valor_liquidado=Decimal("450.00"),
            valor_pago=Decimal("400.00"),
        ),
    ]

    resultado = calcular_custo_estrutura_mandato(
        municipio_id="inhumas-go",
        vereador_id="inhumas-go-ver-9",
        competencia_ano=2026,
        competencia_mes=10,
        subsidio_bruto_vereador=Decimal("10435.56"),
        itens_folha_gabinete=itens_folha,
        itens_diarias=itens_diarias,
        fonte_url="https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/servidores_cnt",
    )

    assert resultado.nota_cota_parlamentar == NOTA_OFICIAL_CEAP
    assert resultado.quantidade_servidores_gabinete == 1
    assert resultado.folha_bruta_gabinete == Decimal("5242.73")
    assert resultado.diarias_atribuiveis_pagas == Decimal("400.00")
    assert resultado.diarias_atribuiveis_empenhadas == Decimal("450.00")
    assert resultado.diarias_atribuiveis_liquidadas == Decimal("450.00")
    assert resultado.custo_estrutura_mandato_total == Decimal("16078.29")
    assert len(resultado.avisos) == 2  # 1 duplicidade ignorada + 1 diária não verificável ignorada


def test_dados_ausentes_nunca_viram_zero() -> None:
    """Garante que períodos sem dados (ex.: lacuna SIGEP pré-2026) retornem None e nunca 0 (ADR-005)."""
    assert parse_valor_brl(None) is None
    assert parse_valor_brl("") is None

    resultado_lacuna = calcular_custo_estrutura_mandato(
        municipio_id="inhumas-go",
        vereador_id="inhumas-go-ver-9",
        competencia_ano=2023,
        competencia_mes=5,
        subsidio_bruto_vereador=None,
        itens_folha_gabinete=None,
        itens_diarias=None,
        fonte_url="https://acessoainformacao.inhumas.go.leg.br/",
    )
    assert resultado_lacuna.subsidio_bruto_vereador is None
    assert resultado_lacuna.folha_bruta_gabinete is None
    assert resultado_lacuna.diarias_atribuiveis_pagas is None
    assert resultado_lacuna.custo_estrutura_mandato_total is None


def test_resolucao_entidades_proibe_fusao_automatica_silenciosa() -> None:
    """Nomes desconhecidos devem retornar confiança BAIXA_REVISAO_HUMANA e vereador_id=None."""
    resolvedor = ResolvedorVereadores(municipio_id="inhumas-go")
    desconhecido = resolvedor.resolver_por_nome_ou_lotacao("GAB. DO VEREADOR NOME INEXISTENTE")
    assert desconhecido.vereador_id is None
    assert desconhecido.confianca == "BAIXA_REVISAO_HUMANA"


def test_classificacao_proposicoes_exclui_atas_e_julgamento_contas() -> None:
    """Atas (144) e Julgamento de Contas (211) não são contabilizados na produção parlamentar."""
    ata = classificar_tipo_proposicao(144, "ATA DA SESSÃO")
    assert ata.eh_proposicao_parlamentar is False
    assert ata.contabilizar_producao_vereador is False

    contas = classificar_tipo_proposicao(211, "Julgamento de Contas")
    assert contas.eh_proposicao_parlamentar is False
    assert contas.contabilizar_producao_vereador is False

    pl = classificar_tipo_proposicao(1, "Projeto de Lei")
    assert pl.eh_proposicao_parlamentar is True
    assert pl.contabilizar_producao_vereador is True


def test_storage_pdf_preserva_original_e_separa_ocr_com_flag_revisao(tmp_path: Path) -> None:
    """Testa regras de armazenamento bruto e governança de OCR (ADR-005, Decisão 5)."""
    storage = LocalVersionedStorage(tmp_path / "raw")
    pdf_ficticio = b"%PDF-1.4 Conteudo binario original imutavel da Lei 3577/2026"

    meta = storage.salvar_bruto(
        municipio_id="inhumas-go",
        fonte_id="legislacao_nucleogov",
        fonte_url="https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id=407",
        conteudo=pdf_ficticio,
        mime_type="application/pdf",
        extensao="pdf",
        versao_coletor="cerrado-aberto-coleta/0.1.0",
        url_temporaria=True,
    )

    resultado_ocr = ResultadoOCR(
        hash_documento_original=meta.hash_conteudo,
        extraido_por_ocr=True,
        texto_extraido="LEI Nº 3.577 DE 22 DE SETEMBRO DE 2026 - Paroquia Santana...",
        ocr_engine_versao="tesseract-5.4.0-por",
        ocr_confianca_media=78.5,
        requer_revisao_humana=True,
        motivo_revisao_humana="Divergência entre ementa do portal ('PAROQUIA SANTADA') e texto OCR ('Paroquia Santana').",
    )

    meta_atualizado = storage.salvar_resultado_ocr(meta, resultado_ocr)
    assert meta_atualizado.processado_ocr is True
    assert meta_atualizado.extraido_por_ocr is True
    assert meta_atualizado.requer_revisao_humana is True

    # Verifica que o PDF original permanece 100% intacto
    assert storage.ler_bruto(meta.caminho_armazenamento) == pdf_ficticio
    # E que o texto OCR foi salvo em arquivo separado (.pdf.ocr.txt)
    caminho_ocr = (tmp_path / "raw" / meta.caminho_armazenamento).with_suffix(".pdf.ocr.txt")
    assert caminho_ocr.exists()
    assert "Paroquia Santana" in caminho_ocr.read_text(encoding="utf-8")


def test_lgpd_mascaramento_em_fixtures_transparencia() -> None:
    """Garante que CPFs sejam mascarados como ***.***.***-** e CNPJs válidos preservados."""
    despesas = json.loads(
        (FIXTURES_TRANSPARENCIA / "despesas_centi_list.json").read_text(encoding="utf-8")
    )
    for item in despesas:
        doc_tratado, tipo_doc = mascarar_documento_lgpd(item.get("CnpjCpf"))
        if tipo_doc == "CPF_MASCARADO":
            assert doc_tratado == "***.***.***-**"
        elif tipo_doc == "CNPJ":
            assert len(doc_tratado) == 14
            assert doc_tratado.isdigit()
