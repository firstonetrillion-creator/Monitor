"""Testes de unidade e integração offline do coletor Nexlegis (Fase 1) contra fixtures reais."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from cerrado_aberto_coleta.config import criar_config_municipio_padrao
from cerrado_aberto_coleta.nexlegis import (
    InMemoryNexlegisRepository,
    LayoutQuebradoError,
    NexlegisFetcher,
    NexlegisParser,
)
from cerrado_aberto_coleta.qualidade import avaliar_qualidade_repositorio
from cerrado_aberto_coleta.storage import LocalVersionedStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "nexlegis"


def _salvar_fixture_no_storage(
    storage: LocalVersionedStorage, nome_arquivo: str, url_origem: str
):
    conteudo = (FIXTURES_DIR / nome_arquivo).read_bytes()
    meta = storage.salvar_bruto(
        municipio_id="inhumas-go",
        fonte_id="nexlegis",
        fonte_url=url_origem,
        conteudo=conteudo,
        mime_type="application/json",
        extensao="json",
        versao_coletor="cerrado-aberto-coleta/0.1.0",
    )
    return conteudo, meta


def test_pipeline_completo_fixtures_reais_e_idempotencia(tmp_path: Path) -> None:
    """Valida fetch/storage -> parse -> load nas 5 fixtures reais do Nexlegis e testa idempotência."""
    storage = LocalVersionedStorage(tmp_path / "raw")
    parser = NexlegisParser(municipio_id="inhumas-go")
    repo = InMemoryNexlegisRepository()

    # 1. Vereadores
    b_ver, m_ver = _salvar_fixture_no_storage(
        storage,
        "vereadores_list_page1.json",
        "https://inhumas.nexlegis.com.br/api/vereadores?page=1",
    )
    vereadores = parser.parse_vereadores_list(b_ver, m_ver)
    assert len(vereadores) == 15
    res_ver_1 = repo.carregar_vereadores(vereadores)
    assert res_ver_1.novos == 15
    assert res_ver_1.inalterados == 0

    # Reexecução idempotente de vereadores
    res_ver_2 = repo.carregar_vereadores(vereadores)
    assert res_ver_2.novos == 0
    assert res_ver_2.alterados == 0
    assert res_ver_2.inalterados == 15

    # 2. Lista de sessões
    b_ses, m_ses = _salvar_fixture_no_storage(
        storage,
        "sessoes_list_page1.json",
        "https://inhumas.nexlegis.com.br/api/sessoes?page=1&per_page=2",
    )
    sessoes = parser.parse_sessoes_list(b_ses, m_ses)
    assert len(sessoes) == 2
    res_ses_1 = repo.carregar_sessoes(sessoes)
    assert res_ses_1.novos == 2

    # 3. Detalhe da sessão 969 (presenças, pauta com ATA 144, votação e votos nominais)
    b_det, m_det = _salvar_fixture_no_storage(
        storage,
        "sessao_969_detail.json",
        "https://inhumas.nexlegis.com.br/api/sessoes/969",
    )
    pacote_det = parser.parse_sessao_detalhe(b_det, m_det)
    assert pacote_det.sessao.id_origem_nexlegis == 969
    assert len(pacote_det.presencas) == 2
    assert len(pacote_det.pauta_itens) == 1
    assert len(pacote_det.votacoes) == 1
    assert len(pacote_det.votos_nominais) == 2

    res_det_1 = repo.carregar_pacote_sessao_detalhe(pacote_det)
    assert res_det_1.lidos > 0

    # Reexecução idempotente do detalhe da sessão
    res_det_2 = repo.carregar_pacote_sessao_detalhe(pacote_det)
    assert res_det_2.novos == 0
    assert res_det_2.alterados == 0

    # 4. Matérias: página 1 (Requerimento 312/2026 - tipo_id 5) e página 2716 (Julgamento de Contas - tipo_id 211)
    b_mat1, m_mat1 = _salvar_fixture_no_storage(
        storage,
        "materias_list_page1.json",
        "https://inhumas.nexlegis.com.br/api/materias?page=1&per_page=1",
    )
    pacote_mat1 = parser.parse_materias_list(b_mat1, m_mat1)
    assert pacote_mat1.total_api == 2716
    assert len(pacote_mat1.proposicoes) == 1
    assert pacote_mat1.proposicoes[0].eh_proposicao_parlamentar is True
    assert pacote_mat1.proposicoes[0].contabilizar_producao_vereador is True

    b_mat_old, m_mat_old = _salvar_fixture_no_storage(
        storage,
        "materias_oldest_page2716.json",
        "https://inhumas.nexlegis.com.br/api/materias/927",
    )
    pacote_mat_old = parser.parse_materia_detalhe(b_mat_old, m_mat_old)
    assert len(pacote_mat_old.proposicoes) == 1
    # Julgamento de Contas (tipo_id 211) deve ser preservado no banco mas NÃO contabilizado como proposição parlamentar
    assert pacote_mat_old.proposicoes[0].tipo_id_origem == 211
    assert pacote_mat_old.proposicoes[0].eh_proposicao_parlamentar is False
    assert pacote_mat_old.proposicoes[0].contabilizar_producao_vereador is False

    repo.carregar_pacote_materias(pacote_mat1)
    repo.carregar_pacote_materias(pacote_mat_old)

    # 5. Verifica que todas as 3 matérias (Requerimento 2770, Ata 2771 e Julgamento de Contas 927) estão no banco
    assert len(repo.proposicoes.ativos) == 3

    # Mas apenas o Requerimento 312/2026 (do Prof. Kelvy Fernandes, id 149) entra na contagem de produção parlamentar!
    producao = repo.contar_producao_legislativa_por_vereador()
    assert producao == {"inhumas-go-ver-149": 1}

    # 6. Avalia relatório de qualidade
    relatorio = avaliar_qualidade_repositorio(repo, municipio_id="inhumas-go")
    assert relatorio.proveniencia_100_porcento is True
    assert relatorio.aprovado_para_publicacao is True
    assert relatorio.total_proposicoes_armazenadas == 3
    assert relatorio.total_proposicoes_parlamentares == 1
    assert relatorio.total_documentos_administrativos_separados == 2


def test_deduplicacao_sessoes_mesma_chave_natural(tmp_path: Path) -> None:
    """Garante que duas sessões com mesmo (municipio, tipo_id, numero, ano, data) sejam deduplicadas."""
    storage = LocalVersionedStorage(tmp_path / "raw")
    parser = NexlegisParser(municipio_id="inhumas-go")

    payload_duplicado = {
        "data": [
            {
                "id": 969,
                "numero": "053",
                "ano": 2026,
                "data": "2026-11-10",
                "tipo_id": 1,
                "nome_sessao": "Sessão Ordinária 053/2026",
                "slug": "sessao-ordinaria-053-2026",
                "tipo": {"id": 1, "descricao": "Sessão Ordinária"},
            },
            {
                "id": 1002,
                "numero": "053",
                "ano": 2026,
                "data": "2026-11-10",
                "tipo_id": 1,
                "nome_sessao": "Sessão Ordinária 053/2026",
                "slug": "sessao-ordinaria-053-2026-dup",
                "tipo": {"id": 1, "descricao": "Sessão Ordinária"},
            },
        ]
    }
    bruto = json.dumps(payload_duplicado).encode("utf-8")
    meta = storage.salvar_bruto(
        municipio_id="inhumas-go",
        fonte_id="nexlegis",
        fonte_url="https://inhumas.nexlegis.com.br/api/sessoes?page=1",
        conteudo=bruto,
        mime_type="application/json",
        extensao="json",
        versao_coletor="cerrado-aberto-coleta/0.1.0",
    )

    sessoes = parser.parse_sessoes_list(bruto, meta)
    assert len(sessoes) == 1
    assert sessoes[0].id_origem_nexlegis == 969
    assert sessoes[0].ids_origem_duplicados == (1002,)


def test_layout_quebrado_dispara_erro_explicito_com_url_e_hash(tmp_path: Path) -> None:
    """Garante que mudança de estrutura na API nunca grave lixo silenciosamente."""
    storage = LocalVersionedStorage(tmp_path / "raw")
    parser = NexlegisParser(municipio_id="inhumas-go")

    # Caso 1: JSON sem a chave 'data'
    bruto_sem_data = b'{"unexpected_key": []}'
    meta_1 = storage.salvar_bruto(
        municipio_id="inhumas-go",
        fonte_id="nexlegis",
        fonte_url="https://inhumas.nexlegis.com.br/api/materias?page=1",
        conteudo=bruto_sem_data,
        mime_type="application/json",
        extensao="json",
        versao_coletor="cerrado-aberto-coleta/0.1.0",
    )
    with pytest.raises(LayoutQuebradoError) as exc_info:
        parser.parse_materias_list(bruto_sem_data, meta_1)
    assert meta_1.fonte_url in str(exc_info.value)
    assert meta_1.hash_conteudo in str(exc_info.value)

    # Caso 2: Item sem campos obrigatórios ('ementa' ausente)
    bruto_incompleto = json.dumps(
        {"data": [{"id": 999, "numero": "001", "ano": 2026, "tipo_id": 1}]}
    ).encode("utf-8")
    meta_2 = storage.salvar_bruto(
        municipio_id="inhumas-go",
        fonte_id="nexlegis",
        fonte_url="https://inhumas.nexlegis.com.br/api/materias?page=2",
        conteudo=bruto_incompleto,
        mime_type="application/json",
        extensao="json",
        versao_coletor="cerrado-aberto-coleta/0.1.0",
    )
    with pytest.raises(LayoutQuebradoError) as exc_info_2:
        parser.parse_materias_list(bruto_incompleto, meta_2)
    assert "ementa" in str(exc_info_2.value)


def test_fetcher_com_mock_transport_respeita_rate_limit_e_salva_bruto(tmp_path: Path) -> None:
    """Testa a etapa 1 (Fetch) usando MockTransport (sem tocar na rede real)."""
    storage = LocalVersionedStorage(tmp_path / "raw")
    cfg = criar_config_municipio_padrao(raw_dir=tmp_path / "raw")
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert "CerradoAbertoBot/0.1" in request.headers.get("user-agent", "")
        return httpx.Response(200, json={"data": [], "total": 0})

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        headers={"User-Agent": cfg.user_agent},
    )
    fetcher = NexlegisFetcher(cfg, storage, http_client=client, sleep_fn=sleeps.append)

    b1, m1 = fetcher.fetch_json_endpoint("/vereadores")
    _b2, m2 = fetcher.fetch_json_endpoint("/sessoes?page=1")

    assert len(b1) > 0
    assert m1.fonte_url == "https://inhumas.nexlegis.com.br/api/vereadores"
    assert m2.fonte_url == "https://inhumas.nexlegis.com.br/api/sessoes?page=1"
    # Segunda chamada deve acionar o rate limiter
    assert len(sleeps) == 1
    assert sleeps[0] > 0


def test_sessao_especial_com_numero_nulo_normaliza_para_sn(tmp_path: Path) -> None:
    """Garante que sessões especiais com 'numero': null na API (ex.: id 93) sejam normalizadas como 'S/N'."""
    storage = LocalVersionedStorage(tmp_path / "raw")
    parser = NexlegisParser(municipio_id="inhumas-go")
    payload = {
        "data": [
            {
                "id": 93,
                "numero": None,
                "ano": 2024,
                "data": "2024-11-28",
                "tipo_id": 4,
                "nome_sessao": "Sessão Especial 2024",
                "slug": "sessao-especial-2024",
                "tipo": {"id": 4, "descricao": "Sessão Especial"},
            }
        ]
    }
    bruto = json.dumps(payload).encode("utf-8")
    meta = storage.salvar_bruto(
        municipio_id="inhumas-go",
        fonte_id="nexlegis",
        fonte_url="https://inhumas.nexlegis.com.br/api/sessoes?page=3&per_page=50",
        conteudo=bruto,
        mime_type="application/json",
        extensao="json",
        versao_coletor="cerrado-aberto-coleta/0.1.0",
    )
    sessoes = parser.parse_sessoes_list(bruto, meta)
    assert len(sessoes) == 1
    assert sessoes[0].id_origem_nexlegis == 93
    assert sessoes[0].numero == "S/N"
