"""Contratos de dados normalizados para o Portal da Transparência CENTI/NúcleoGov (Exercício 2026)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class FolhaPagamentoRegistro:
    folha_id: str
    municipio_id: str
    ano: int
    mes: int
    referencia: str
    matricula: str
    nome_servidor: str
    cpf_mascarado: str
    situacao: str | None
    orgao: str
    cargo: str
    funcao: str | None
    lotacao: str
    local_trabalho: str | None
    decreto_nomeacao: str | None
    possui_estabilidade: str | None
    data_admissao: date | None
    data_exoneracao: date | None
    tipo_admissao: str | None
    carga_horaria: str | None
    tipo_folha: str
    movimentacao: str | None
    salario_base: Decimal | None
    remuneracao_bruta: Decimal | None
    descontos: Decimal | None
    remuneracao_liquida: Decimal | None
    eh_vereador: bool
    vereador_id: str | None
    gabinete_vereador_id: str | None
    fonte_id: str
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str


@dataclass(frozen=True)
class FornecedorRegistro:
    fornecedor_id: str
    municipio_id: str
    nome: str
    chave_busca: str
    documento_mascarado_ou_cnpj: str
    tipo_pessoa: str  # 'PESSOA_JURIDICA' ou 'PESSOA_FISICA'
    cnpj_valido: bool | None
    fonte_id: str
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str


@dataclass(frozen=True)
class DespesaEmpenhoRegistro:
    empenho_id: str
    municipio_id: str
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
    orgao: str | None
    processo_licitatorio: str | None
    destinacao_recurso: str | None
    unidade: str | None
    funcao: str | None
    subfuncao: str | None
    programa: str | None
    acao: str | None
    categoria_economica: str | None
    grupo_despesa: str | None
    modalidade_aplicacao: str | None
    elemento_despesa: str | None
    subelemento_despesa: str | None
    fonte_recurso: str | None
    eh_diaria: bool
    vereador_beneficiario_id: str | None
    fonte_id: str
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str


@dataclass(frozen=True)
class DiariaRegistro:
    diaria_id: str
    municipio_id: str
    empenho_id: str | None
    numero_empenho: str
    ano: int
    mes: int
    data_concessao: date
    beneficiario_nome: str
    cpf_mascarado: str
    tipo_beneficiario: str  # 'VEREADOR', 'SERVIDOR_GABINETE', 'SERVIDOR_ADMINISTRATIVO'
    vereador_id_verificado: str | None
    gabinete_vereador_id: str | None
    cargo_beneficiario: str | None
    identificacao_documental_verificavel: bool
    destino_ou_finalidade: str
    valor_empenhado_liquido: Decimal
    valor_liquidado: Decimal
    valor_pago: Decimal
    origem_registro: str
    fonte_id: str
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str


@dataclass(frozen=True)
class DuodecimoRegistro:
    duodecimo_id: str
    municipio_id: str
    id_origem: str
    ano: int
    mes: int
    data_lancamento: date
    tipo_codigo: str
    tipo_natureza: str  # 'RECEITA_REPASSE' ou 'DEVOLUCAO_DUODECIMO'
    descricao: str
    valor: Decimal
    arquivo_nome: str | None
    fonte_id: str
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str


@dataclass(frozen=True)
class DeclaracaoTransparenciaRegistro:
    declaracao_id: str
    municipio_id: str
    tipo_declaracao: str
    titulo_oficial: str
    texto_integral: str
    data_inicio_cobertura: date
    data_fim_cobertura: date
    data_atualizacao: date | None
    signatario_presidente: str | None
    signatario_certificador: str | None
    observacao_cruzamento: str | None
    fonte_id: str
    fonte_url: str
    coletado_em: datetime
    hash_conteudo: str
    versao_coletor: str


@dataclass(frozen=True)
class CustoEstruturaMandatoMensalRegistro:
    custo_mensal_id: str
    municipio_id: str
    vereador_id: str
    ano: int
    mes: int
    competencia_status: str  # 'FECHADA', 'ABERTA_SEM_PUBLICACAO', 'LACUNA_PARCIAL_LOTACAO'
    subsidio_bruto_vereador: Decimal | None
    subsidio_mensal_base: Decimal | None
    adicionais_ferias_decimo_terceiro_vereador: Decimal | None
    folha_bruta_gabinete: Decimal | None
    folha_mensal_gabinete: Decimal | None
    adicionais_ferias_decimo_terceiro_gabinete: Decimal | None
    quantidade_servidores_gabinete: int | None
    diarias_atribuiveis_empenhadas: Decimal | None
    diarias_atribuiveis_liquidadas: Decimal | None
    diarias_atribuiveis_pagas: Decimal | None
    custo_estrutura_mandato_total: Decimal | None
    nota_cota_parlamentar: str
    periodo_declaracao_ceap: str
    metodologia_resumo: str
    limitacoes_dados: str
    avisos: list[str] = field(default_factory=list)
    fonte_id: str = "transparencia_centi"
    fonte_url: str = ""
    coletado_em: datetime | None = None
    hash_conteudo: str = ""
    versao_coletor: str = ""
