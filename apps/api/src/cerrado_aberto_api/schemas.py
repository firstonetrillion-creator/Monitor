"""Modelos Pydantic v2 para contratos e documentação OpenAPI da API de leitura do Cerrado Aberto."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProvenienciaOut(BaseModel):
    """Metadados obrigatórios de rastreabilidade (AGENTS.md Seção 4.1)."""

    municipio_id: str = Field(description="Identificador do município (ex.: inhumas-go).")
    fonte_id: str = Field(description="Identificador da fonte oficial (ex.: nexlegis).")
    fonte_url: str = Field(description="URL oficial exata de onde o registro foi coletado.")
    coletado_em: datetime = Field(description="Instante UTC da coleta.")
    hash_conteudo: str = Field(description="Hash SHA-256 hexadecimal do documento bruto original.")
    versao_coletor: str = Field(description="Versão do coletor que gerou o registro.")


class PaginacaoOut[T](BaseModel):
    """Envelope padrão de paginação para listagens da API."""

    page: int = Field(ge=1, description="Página atual (1-indexed).")
    per_page: int = Field(ge=1, le=100, description="Quantidade máxima de itens por página.")
    total: int = Field(ge=0, description="Total de registros encontrados para os filtros aplicados.")
    total_pages: int = Field(ge=0, description="Total de páginas disponíveis.")
    items: list[T] = Field(description="Itens da página solicitada.")


# -----------------------------------------------------------------------------
# 1. Vereadores
# -----------------------------------------------------------------------------


class VereadorResumoOut(BaseModel):
    vereador_id: str
    municipio_id: str
    id_origem_nexlegis: int | None = None
    nome_civil: str | None = Field(
        default=None,
        description="Nome civil quando disponível na fonte (preservado como NULL quando ausente).",
    )
    nome_politico: str
    nome_exibicao: str
    slug: str
    partido_sigla: str | None = Field(
        default=None,
        description="Sigla partidária quando confirmada (preservada como NULL quando ausente).",
    )
    condicao_mandato_2025_2028: str | None = Field(
        default=None,
        description="TITULAR, SUPLENTE ou NULL (para parlamentares de legislaturas anteriores).",
    )
    avatar_url: str | None = None
    sessoes_presente_2025: int = 0
    sessoes_ausente_ou_justificado_2025: int = 0
    total_proposicoes_parlamentares_2025: int = Field(
        default=0,
        description=(
            "Total de proposições parlamentares de 2025 vinculadas ao vereador, "
            "excluindo atas (144/145) e atos administrativos conforme ADR-005."
        ),
    )
    sessoes_presente_2026: int = 0
    sessoes_ausente_ou_justificado_2026: int = 0
    total_proposicoes_parlamentares_2026: int = Field(
        default=0,
        description=(
            "Total de proposições parlamentares de 2026 vinculadas ao vereador, "
            "excluindo atas (144/145) e atos administrativos conforme ADR-005."
        ),
    )
    custo_estrutura_mandato_acumulado_2026: Decimal | None = Field(
        default=None,
        description=(
            "Soma das competências fechadas de 2026 do Custo da Estrutura do Mandato "
            "(Subsídio + Folha Bruta do Gabinete + Diárias Atribuíveis). NULL quando houver "
            "lacuna parcial de lotação ou competência não encerrada."
        ),
    )
    competencias_custo_fechadas_2026: int = 0
    proveniencia: ProvenienciaOut


class AliasVereadorOut(BaseModel):
    alias_texto: str
    tipo_alias: str
    fonte_origem: str
    confianca: str


class MandatoVereadorOut(BaseModel):
    mandato_id: str
    legislatura_id: str
    partido_id: str | None = None
    condicao: str
    cargo_mesa: str | None = None
    votos_eleicao: int | None = None
    valido_de: date
    valido_ate: date | None = None


class ResumoPresenca2026Out(BaseModel):
    total_sessoes_registradas: int
    presentes: int
    faltas_justificadas: int
    ausentes: int
    licencas: int


class ProducaoPorTipoOut(BaseModel):
    ano: int
    tipo_id_origem: int
    tipo_proposicao: str
    categoria: str
    total_proposicoes: int


class ProposicaoRecenteVereadorOut(BaseModel):
    proposicao_id: str
    id_origem_nexlegis: int
    nome_materia: str
    tipo_id_origem: int
    tipo_descricao_origem: str
    ano: int
    numero: str
    ementa: str
    data_publicacao: date | None = None
    eh_proposicao_parlamentar: bool
    contabilizar_producao_vereador: bool


class VotoRecenteVereadorOut(BaseModel):
    voto_id: str
    votacao_id: str
    sessao_id: str
    nome_sessao: str
    data_sessao: date
    proposicao_id: str
    nome_materia: str
    voto_descricao: str
    voto_normalizado: str


class VereadorDetalheOut(BaseModel):
    vereador_id: str
    municipio_id: str
    id_origem_nexlegis: int | None = None
    nome_civil: str | None = None
    nome_politico: str
    nome_exibicao: str
    slug: str
    email_publico: str | None = None
    avatar_url: str | None = None
    biografia_texto: str | None = None
    aliases: list[AliasVereadorOut]
    mandatos: list[MandatoVereadorOut]
    resumo_presenca_2025: ResumoPresenca2026Out | None = None
    total_proposicoes_parlamentares_2025: int = 0
    producao_por_tipo_2025: list[ProducaoPorTipoOut] = Field(default_factory=list)
    resumo_presenca_2026: ResumoPresenca2026Out
    total_proposicoes_parlamentares_2026: int
    producao_por_tipo_2026: list[ProducaoPorTipoOut]
    nota_metodologica_producao: str = Field(
        default=(
            "A contagem de produção legislativa parlamentar exclui Atas de Sessão "
            "(tipo_id 144 e 145), Julgamentos de Contas (tipo_id 211), Balanços Gerais (tipo_id 213) "
            "e atos exclusivos do Executivo, conforme ADR-005 (Decisão 4)."
        )
    )
    proposicoes_recentes: list[ProposicaoRecenteVereadorOut]
    votos_recentes_2025: list[VotoRecenteVereadorOut] = Field(default_factory=list)
    votos_recentes_2026: list[VotoRecenteVereadorOut]
    custo_estrutura_mandato_2026: CustoMandatoResumoAnualOut | None = None
    proveniencia: ProvenienciaOut


# -----------------------------------------------------------------------------
# 2. Sessões Plenárias
# -----------------------------------------------------------------------------


class SessaoResumoOut(BaseModel):
    sessao_id: str
    municipio_id: str
    legislatura_id: str | None = None
    id_origem_nexlegis: int
    ids_origem_duplicados: list[int] = Field(default_factory=list)
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
    quorum: int | None = None
    ata_pdf_url: str | None = None
    total_presentes: int = 0
    total_ausentes_ou_justificados: int = 0
    total_itens_pauta: int = 0
    total_votacoes: int = 0
    proveniencia: ProvenienciaOut


class PresencaSessaoOut(BaseModel):
    presenca_id: str
    vereador_id: str
    nome_politico: str
    nome_exibicao: str
    slug: str
    situacao_id_origem: int
    situacao_descricao: str
    status_normalizado: str


class PautaItemSessaoOut(BaseModel):
    pauta_item_id: str
    ordem: int
    turno: int
    tipo_pauta_id_origem: int | None = None
    tipo_pauta_descricao: str | None = None
    proposicao_id: str
    id_origem_proposicao: int
    nome_materia: str
    tipo_id_origem: int
    tipo_descricao_origem: str
    ementa: str
    eh_proposicao_parlamentar: bool
    unanime_flag_api: bool
    has_votos: bool


class VotoNominalItemOut(BaseModel):
    voto_id: str
    vereador_id: str
    nome_politico: str
    nome_exibicao: str
    voto_id_origem: int
    voto_descricao: str
    voto_normalizado: str


class VotacaoSessaoOut(BaseModel):
    votacao_id: str
    id_origem_nexlegis: int
    proposicao_id: str
    nome_materia: str
    tipo_turno_id: int | None = None
    unanime_flag_api: bool
    has_votos: bool
    placar_favoravel: int
    placar_contrario: int
    placar_abstencao: int
    placar_ausente: int
    discussed_at: datetime | None = None
    started_at: datetime | None = None
    closed_at: datetime | None = None
    tempo_decorrido_segundos: int | None = None
    votos_nominais: list[VotoNominalItemOut]


class ResumoCidadaoOut(BaseModel):
    """Resumo em linguagem simples (skill texto-cidadao / docs/05 Regra 6)."""

    rotulo_transparencia: str = (
        "Resumo automático gerado a partir dos registros oficiais — confira sempre o documento original."
    )
    metodo_geracao: str = "AUTOMATICO_DETERMINISTICO"
    revisado_por_humano: bool = False
    o_que_e: str
    o_que_propoe: str
    situacao_e_resultado: str
    texto_resumo_3_linhas: str
    fonte_url: str
    coletado_em: datetime


class ContagemTipoBoletimOut(BaseModel):
    tipo_descricao: str
    quantidade: int


class DestaquePautaBoletimOut(BaseModel):
    proposicao_id: str
    nome_materia: str
    tipo_descricao_origem: str
    ementa_original: str
    autores_nomes: list[str]
    placar_resumo: str
    resumo_cidadao: ResumoCidadaoOut


class PanoramaFinanceiroBoletimOut(BaseModel):
    ano: int
    despesa_paga_acumulada: Decimal | None = None
    despesa_empenhada_liquida: Decimal | None = None
    duodecimo_recebido_acumulado: Decimal | None = None
    duodecimo_devolvido_acumulado: Decimal | None = None
    populacao_ibge_2026: int
    meses_apurados: int
    valor_por_habitante_mes: Decimal | None = None
    ultima_coleta_transparencia: datetime | None = None


class SlideInstagramOut(BaseModel):
    numero: int
    etiqueta: str
    titulo: str
    subtitulo: str
    itens: list[str]
    rodape_fonte: str


class SessaoOpcaoBoletimOut(BaseModel):
    sessao_id: str
    nome_sessao: str
    data_abertura: date
    tipo_descricao: str


class BoletimSemanalOut(BaseModel):
    municipio_id: str
    handle_instagram_oficial: str = "@cerradoaberto"
    dominio_oficial: str = "cerradoaberto.org.br"
    sessao_id: str
    nome_sessao: str
    tipo_descricao: str
    data_abertura: date
    horario_abertura: str | None = None
    ata_pdf_url: str | None = None
    total_presentes: int
    total_faltas_justificadas: int
    total_ausentes: int
    total_licencas: int
    total_itens_pauta: int
    total_proposicoes_parlamentares: int
    total_votacoes: int
    contagem_por_tipo: list[ContagemTipoBoletimOut]
    destaques_pauta: list[DestaquePautaBoletimOut]
    resumo_sessao: ResumoCidadaoOut
    panorama_financeiro_2026: PanoramaFinanceiroBoletimOut
    alerta_whatsapp: str
    legenda_instagram: str
    slides_instagram: list[SlideInstagramOut]
    sessoes_disponiveis: list[SessaoOpcaoBoletimOut]
    proveniencia: ProvenienciaOut


class SessaoDetalheOut(BaseModel):
    sessao_id: str
    municipio_id: str
    legislatura_id: str | None = None
    id_origem_nexlegis: int
    ids_origem_duplicados: list[int] = Field(default_factory=list)
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
    presencas: list[PresencaSessaoOut]
    pauta_itens: list[PautaItemSessaoOut]
    votacoes: list[VotacaoSessaoOut]
    resumo_cidadao: ResumoCidadaoOut | None = None
    proveniencia: ProvenienciaOut


# -----------------------------------------------------------------------------
# 3. Matérias e Proposições Legislativas
# -----------------------------------------------------------------------------


class AutorMateriaOut(BaseModel):
    autoria_id: str
    tipo_autor: str
    vereador_id: str | None = None
    nome_politico: str | None = None
    nome_exibicao: str | None = None
    slug: str | None = None
    autor_institucional: str | None = None


class MateriaResumoOut(BaseModel):
    proposicao_id: str
    municipio_id: str
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
    categoria_classificada: str
    eh_proposicao_parlamentar: bool
    contabilizar_producao_vereador: bool
    autores: list[AutorMateriaOut]
    proveniencia: ProvenienciaOut


class TramitacaoMateriaOut(BaseModel):
    tramitacao_id: str
    id_origem_nexlegis: int
    data_tramitacao: date
    local_origem: str | None = None
    local_destino: str | None = None
    situacao_descricao: str | None = None
    prioridade_descricao: str | None = None
    prazo_descricao: str | None = None
    justificativa: str | None = None


class DeliberacaoMateriaSessaoOut(BaseModel):
    sessao_id: str
    id_origem_sessao: int
    nome_sessao: str
    data_sessao: date
    ordem: int
    turno: int
    tipo_pauta_descricao: str | None = None
    votacao_id: str | None = None
    placar_favoravel: int = 0
    placar_contrario: int = 0
    placar_abstencao: int = 0
    votos_nominais: list[VotoNominalItemOut] = Field(default_factory=list)


class MateriaDetalheOut(BaseModel):
    proposicao_id: str
    municipio_id: str
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
    categoria_classificada: str
    eh_proposicao_parlamentar: bool
    contabilizar_producao_vereador: bool
    justificativa_classificacao: str | None = None
    autores: list[AutorMateriaOut]
    tramitacoes: list[TramitacaoMateriaOut]
    deliberacoes_em_sessao: list[DeliberacaoMateriaSessaoOut]
    resumo_cidadao: ResumoCidadaoOut | None = None
    proveniencia: ProvenienciaOut


# -----------------------------------------------------------------------------
# 4. Health & Transparência de Escopo
# -----------------------------------------------------------------------------


class LacunaHistoricaOut(BaseModel):
    lacuna_id: str
    fonte_id: str
    entidade_afetada: str
    data_inicio_lacuna: date | None = None
    data_fim_lacuna: date | None = None
    motivo_oficial: str
    evidencia_url: str | None = None
    pedido_lai_previsto: bool


class HealthOut(BaseModel):
    status: str
    plataforma: str = "Cerrado Aberto"
    natureza: str = (
        "Iniciativa cidadã independente de monitoramento e interpretação de dados públicos, "
        "sem vínculo institucional ou político com a Câmara Municipal."
    )
    banco_dados: str
    versao_postgresql: str
    modo_acesso: str = "SOMENTE_LEITURA"
    municipio_padrao: str
    escopo_dados_ativo: str = (
        "Fase 1 (Nexlegis 2025–2026) + Fase 2 (Portal da Transparência CENTI/NúcleoGov 2026)"
    )
    contagens_persistidas: dict[str, int]
    lacunas_historicas_documentadas: list[LacunaHistoricaOut]
    ultima_coleta_por_fonte: list[ColetaFonteOut] = Field(
        default_factory=list,
        description="Instante da coleta mais recente de documentos brutos, por fonte oficial.",
    )


# -----------------------------------------------------------------------------
# 5. Transparência CENTI/NúcleoGov e Custo da Estrutura do Mandato (Fase 2 — 2026)
# -----------------------------------------------------------------------------


class CustoMandatoMensalOut(BaseModel):
    custo_mensal_id: str
    vereador_id: str
    nome_politico: str | None = None
    nome_exibicao: str | None = None
    ano: int
    mes: int
    competencia_status: str
    subsidio_bruto_vereador: Decimal | None = None
    subsidio_mensal_base: Decimal | None = None
    adicionais_ferias_decimo_terceiro_vereador: Decimal | None = None
    folha_bruta_gabinete: Decimal | None = None
    folha_mensal_gabinete: Decimal | None = None
    adicionais_ferias_decimo_terceiro_gabinete: Decimal | None = None
    quantidade_servidores_gabinete: int | None = None
    diarias_atribuiveis_empenhadas: Decimal | None = None
    diarias_atribuiveis_liquidadas: Decimal | None = None
    diarias_atribuiveis_pagas: Decimal | None = None
    custo_estrutura_mandato_total: Decimal | None = None
    nota_cota_parlamentar: str
    periodo_declaracao_ceap: str
    metodologia_resumo: str
    limitacoes_dados: str
    avisos: list[str] = Field(default_factory=list)
    proveniencia: ProvenienciaOut


class CustoMandatoResumoAnualOut(BaseModel):
    ano: int
    competencias_fechadas: int
    competencias_lacuna_parcial: int
    competencias_abertas_null: int
    subsidio_bruto_acumulado: Decimal | None = None
    folha_bruta_gabinete_acumulada: Decimal | None = None
    diarias_atribuiveis_pagas_acumuladas: Decimal | None = None
    custo_estrutura_mandato_acumulado: Decimal | None = None
    nota_cota_parlamentar: str
    periodo_declaracao_ceap: str
    metodologia_resumo: str
    limitacoes_gerais: str
    series_mensais: list[CustoMandatoMensalOut]


class FolhaPagamentoOut(BaseModel):
    folha_id: str
    ano: int
    mes: int
    referencia: str
    matricula: str
    nome_servidor: str
    cpf_mascarado: str
    situacao: str | None = None
    orgao: str
    cargo: str
    funcao: str | None = None
    lotacao: str
    data_admissao: date | None = None
    data_exoneracao: date | None = None
    tipo_admissao: str | None = None
    tipo_folha: str
    movimentacao: str | None = None
    salario_base: Decimal | None = None
    remuneracao_bruta: Decimal | None = None
    descontos: Decimal | None = None
    remuneracao_liquida: Decimal | None = None
    eh_vereador: bool
    vereador_id: str | None = None
    gabinete_vereador_id: str | None = None
    proveniencia: ProvenienciaOut


class DespesaEmpenhoOut(BaseModel):
    empenho_id: str
    numero_empenho: str
    ano: int
    mes: int
    data_empenho: date
    fornecedor_id: str
    favorecido_nome: str
    documento_favorecido: str
    tipo_pessoa_favorecido: str
    valor_empenhado_bruto: Decimal
    valor_anulacao: Decimal
    valor_empenhado_liquido: Decimal
    valor_liquidado: Decimal
    valor_pago: Decimal
    saldo_pagar: Decimal
    historico: str
    processo_licitatorio: str | None = None
    elemento_despesa: str | None = None
    subelemento_despesa: str | None = None
    fonte_recurso: str | None = None
    eh_diaria: bool
    vereador_beneficiario_id: str | None = None
    proveniencia: ProvenienciaOut


class DiariaOut(BaseModel):
    diaria_id: str
    empenho_id: str | None = None
    numero_empenho: str
    ano: int
    mes: int
    data_concessao: date
    beneficiario_nome: str
    cpf_mascarado: str
    tipo_beneficiario: str
    vereador_id_verificado: str | None = None
    gabinete_vereador_id: str | None = None
    cargo_beneficiario: str | None = None
    identificacao_documental_verificavel: bool
    destino_ou_finalidade: str
    valor_empenhado_liquido: Decimal
    valor_liquidado: Decimal
    valor_pago: Decimal
    origem_registro: str
    proveniencia: ProvenienciaOut


class DuodecimoOut(BaseModel):
    duodecimo_id: str
    id_origem: str
    ano: int
    mes: int
    data_lancamento: date
    tipo_codigo: str
    tipo_natureza: str
    descricao: str
    valor: Decimal
    proveniencia: ProvenienciaOut


class DeclaracaoTransparenciaOut(BaseModel):
    declaracao_id: str
    tipo_declaracao: str
    titulo_oficial: str
    texto_integral: str
    data_inicio_cobertura: date
    data_fim_cobertura: date
    data_atualizacao: date | None = None
    signatario_presidente: str | None = None
    signatario_certificador: str | None = None
    observacao_cruzamento: str | None = None
    proveniencia: ProvenienciaOut


class TotaisDespesaOut(BaseModel):
    """Somatórios dos estágios da despesa calculados no PostgreSQL (nunca no frontend)."""

    quantidade_empenhos: int
    valor_empenhado_bruto: Decimal
    valor_anulacao: Decimal
    valor_empenhado_liquido: Decimal
    valor_liquidado: Decimal
    valor_pago: Decimal
    saldo_pagar: Decimal


class DespesaPorElementoOut(TotaisDespesaOut):
    elemento_despesa: str | None = Field(
        default=None, description="Classificação contábil (elemento de despesa); NULL se ausente na fonte."
    )


class FavorecidoDespesaOut(TotaisDespesaOut):
    fornecedor_id: str
    favorecido_nome: str
    documento_favorecido: str
    tipo_pessoa_favorecido: str


class DespesasResumoOut(BaseModel):
    """Resumo agregado das despesas para os mesmos filtros de `/api/v1/transparencia/despesas`."""

    ano: int
    data_primeiro_empenho: date | None = None
    data_ultimo_empenho: date | None = None
    totais: TotaisDespesaOut
    por_elemento: list[DespesaPorElementoOut] = Field(
        description="Totais por elemento de despesa, ordenados pelo código do elemento."
    )
    favorecidos: list[FavorecidoDespesaOut] = Field(
        description="Favorecidos com empenhos no recorte, em ordem alfabética (para filtros)."
    )
    nota_metodologica: str
    fonte_url: str | None = None
    ultima_coleta_em: datetime | None = None


class ColetaFonteOut(BaseModel):
    fonte_id: str
    ultima_coleta_em: datetime
    documentos_brutos: int


VereadorDetalheOut.model_rebuild()
HealthOut.model_rebuild()
