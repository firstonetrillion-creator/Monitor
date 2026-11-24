"""Schemas Pydantic para validação de entrada (API Nexlegis) e registros tratados com proveniência."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProvenienciaMixin(BaseModel):
    """Campos obrigatórios de proveniência em todo registro tratado (AGENTS.md Seção 4.1)."""

    model_config = ConfigDict(frozen=True)

    municipio_id: str = Field(min_length=2)
    fonte_id: str = Field(default="nexlegis", min_length=2)
    fonte_url: str = Field(min_length=8)
    coletado_em: str = Field(min_length=10)
    hash_conteudo: str = Field(min_length=64, max_length=64)
    versao_coletor: str = Field(min_length=3)


class VereadorRegistro(ProvenienciaMixin):
    vereador_id: str
    id_origem_nexlegis: int
    nome_civil: str | None = None
    nome_politico: str
    nome_exibicao: str
    slug: str
    chave_busca: str
    email_publico: str | None = None
    avatar_url: str | None = None
    biografia_html: str | None = None
    biografia_texto: str | None = None


class SessaoRegistro(ProvenienciaMixin):
    sessao_id: str
    id_origem_nexlegis: int
    ids_origem_duplicados: tuple[int, ...] = ()
    tipo_id_origem: int
    tipo_descricao: str
    numero: str
    ano: int
    nome_sessao: str
    slug: str
    data_abertura: date
    horario_abertura: str | None = None
    data_encerramento: date | None = None
    horario_encerramento: str | None = None
    inicio_sessao_real: datetime | None = None
    presidente_vereador_id: str | None = None
    quorum: int | None = None
    ata_pdf_url: str | None = None


class PresencaRegistro(ProvenienciaMixin):
    presenca_id: str
    sessao_id: str
    vereador_id: str
    situacao_id_origem: int
    situacao_descricao: str
    status_normalizado: str  # 'PRESENTE', 'FALTA_JUSTIFICADA', 'AUSENTE', 'LICENCA'


class ProposicaoRegistro(ProvenienciaMixin):
    proposicao_id: str
    id_origem_nexlegis: int
    tipo_id_origem: int
    tipo_descricao_origem: str
    numero: str
    ano: int
    nome_materia: str
    slug: str | None = None
    ementa: str
    data_publicacao: date | None = None
    ultima_movimentacao: date | None = None
    situacao_atual: str | None = None
    local_origem: str | None = None
    local_destino: str | None = None
    autoria_codigo_origem: int | None = None
    anexo_principal_url: str | None = None
    anexo_principal_nome: str | None = None
    anexo_principal_mime: str | None = None
    anexo_principal_tamanho: int | None = None
    # Classificação (ADR-005, Decisão 4)
    categoria_classificada: str
    eh_proposicao_parlamentar: bool
    contabilizar_producao_vereador: bool


class AutoriaRegistro(ProvenienciaMixin):
    autoria_id: str
    proposicao_id: str
    vereador_id: str | None = None
    autor_institucional: str | None = None
    tipo_autor: str  # 'VEREADOR', 'EXECUTIVO', 'MESA_DIRETORA', 'OUTRO'


class TramitacaoRegistro(ProvenienciaMixin):
    tramitacao_id: str
    proposicao_id: str
    id_origem_nexlegis: int
    data_tramitacao: date
    local_origem: str | None = None
    local_destino: str | None = None
    situacao_descricao: str | None = None
    prioridade_descricao: str | None = None
    prazo_descricao: str | None = None
    justificativa: str | None = None


class PautaItemRegistro(ProvenienciaMixin):
    pauta_item_id: str
    sessao_id: str
    proposicao_id: str
    ordem: int
    turno: int
    tipo_pauta_id_origem: int | None = None
    tipo_pauta_descricao: str | None = None
    unanime: bool = False
    has_votos: bool = False


class VotacaoRegistro(ProvenienciaMixin):
    votacao_id: str
    id_origem_nexlegis: int
    sessao_id: str
    proposicao_id: str
    tipo_turno_id: int | None = None
    unanime: bool = False
    has_votos: bool = False
    discussed_at: datetime | None = None
    started_at: datetime | None = None
    closed_at: datetime | None = None
    tempo_decorrido_segundos: int | None = None


class VotoNominalRegistro(ProvenienciaMixin):
    voto_id: str
    votacao_id: str
    vereador_id: str
    voto_id_origem: int
    voto_descricao: str
    voto_normalizado: str  # 'FAVORAVEL', 'CONTRARIO', 'ABSTENCAO', 'AUSENTE'


class PacoteSessaoDetalheParseado(BaseModel):
    """Resultado consolidado do parse de um detalhe de sessão (`/api/sessoes/{id}`)."""

    model_config = ConfigDict(frozen=True)

    sessao: SessaoRegistro
    presencas: tuple[PresencaRegistro, ...]
    proposicoes_pauta: tuple[ProposicaoRegistro, ...]
    pauta_itens: tuple[PautaItemRegistro, ...]
    votacoes: tuple[VotacaoRegistro, ...]
    votos_nominais: tuple[VotoNominalRegistro, ...]


class PacoteMateriasParseado(BaseModel):
    """Resultado consolidado do parse de uma página de `/api/materias`."""

    model_config = ConfigDict(frozen=True)

    proposicoes: tuple[ProposicaoRegistro, ...]
    autorias: tuple[AutoriaRegistro, ...]
    tramitacoes: tuple[TramitacaoRegistro, ...]
    total_api: int
    pagina_atual: int
    ultima_pagina: int
