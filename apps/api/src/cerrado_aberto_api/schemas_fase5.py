"""Schemas Pydantic dos endpoints da Fase 5 (Busca Avançada, Bairros, Legislação e Comparativo SICONFI)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from cerrado_aberto_api.schemas import ProvenienciaOut, ResumoCidadaoOut


class ItemBuscaOut(BaseModel):
    tipo: str  # 'proposicao' | 'norma' | 'vereador' | 'sessao' | 'despesa'
    id: str
    titulo: str
    subtitulo: str | None
    trecho_destaque: str | None
    data_referencia: date | None
    ano: int | None
    url_interna: str
    fonte_url: str | None
    relevancia: float


class BuscaUnificadaOut(BaseModel):
    termo: str
    categoria: str
    ano: int | None
    page: int
    per_page: int
    total: int
    total_pages: int
    contagem_por_tipo: dict[str, int]
    items: list[ItemBuscaOut]


class TemaContagemOut(BaseModel):
    tema: str
    quantidade: int


class BairroResumoOut(BaseModel):
    bairro_id: str
    slug: str
    nome_oficial: str
    regiao: str
    tipo_localidade: str
    latitude_aprox: Decimal | None
    longitude_aprox: Decimal | None
    total_proposicoes: int
    tema_mais_frequente: str | None
    ultimo_registro: date | None


class BairrosPainelOut(BaseModel):
    municipio_id: str
    ano_filtro: int | None
    tema_filtro: str | None
    proposicoes_parlamentares_total: int
    proposicoes_com_bairro: int
    proposicoes_sem_bairro: int
    nota_metodologica: str
    temas_disponiveis: list[TemaContagemOut]
    bairros: list[BairroResumoOut]


class ProposicaoBairroItemOut(BaseModel):
    proposicao_id: str
    nome_materia: str
    tipo_descricao_origem: str
    ano: int
    data_publicacao: date | None
    ementa: str | None
    situacao_atual: str | None
    tema_principal: str
    trecho_evidencia: str
    autores_nomes: list[str]
    fonte_url: str


class VereadorBairroContagemOut(BaseModel):
    vereador_id: str
    nome_exibicao: str
    slug: str
    quantidade_proposicoes: int


class BairroDetalheOut(BaseModel):
    bairro: BairroResumoOut
    temas: list[TemaContagemOut]
    vereadores_autores: list[VereadorBairroContagemOut]
    page: int
    per_page: int
    total: int
    total_pages: int
    proposicoes: list[ProposicaoBairroItemOut]


class NormaResumoOut(BaseModel):
    norma_id: str
    tabela_origem: str
    id_origem: int
    numero: str
    ano: int | None
    tipo_norma: str
    categoria_descricao: str
    data_publicacao: date | None
    ementa: str
    total_anexos: int
    status_ocr: str
    extraido_por_ocr: bool
    requer_revisao_humana: bool
    fonte_url: str
    coletado_em: datetime


class NormasListagemOut(BaseModel):
    municipio_id: str
    page: int
    per_page: int
    total: int
    total_pages: int
    categorias_disponiveis: list[str]
    anos_disponiveis: list[int]
    nota_cobertura: str
    items: list[NormaResumoOut]


class NormaDetalheOut(NormaResumoOut):
    data_publicacao_portal: date | None
    texto_extraido: str | None
    ocr_engine_versao: str | None
    ocr_confianca_media: Decimal | None
    motivo_revisao_humana: str | None
    resumo_cidadao: ResumoCidadaoOut
    proveniencia: ProvenienciaOut


class ComparativoMunicipioOut(BaseModel):
    comparativo_id: str
    codigo_ibge: str
    ente_nome: str
    uf: str
    eh_municipio_foco: bool
    ano: int
    populacao_siconfi: int | None
    despesa_empenhada: Decimal | None
    despesa_liquidada: Decimal | None
    despesa_paga: Decimal | None
    despesa_paga_per_capita_ano: Decimal | None
    despesa_paga_per_capita_mes: Decimal | None
    despesa_paga_ano_anterior: Decimal | None
    variacao_pct_ano_anterior: Decimal | None
    fonte_url: str
    coletado_em: datetime


class ComparativoSiconfiOut(BaseModel):
    municipio_id: str
    ano_selecionado: int
    anos_disponiveis: list[int]
    fonte_oficial: str
    anexo_siconfi: str
    funcao_descricao: str
    nota_metodologica: str
    media_per_capita_ano_grupo: Decimal | None
    mediana_per_capita_ano_grupo: Decimal | None
    municipios: list[ComparativoMunicipioOut]
