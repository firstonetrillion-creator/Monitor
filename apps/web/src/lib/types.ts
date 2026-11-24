/** Contratos TypeScript alinhados aos schemas OpenAPI da API FastAPI v1 (somente leitura). */

export interface ProvenienciaOut {
  municipio_id: string;
  fonte_id: string;
  fonte_url: string;
  coletado_em: string;
  hash_conteudo: string;
  versao_coletor: string;
}

export interface PaginacaoOut<T> {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  items: T[];
}

export interface LacunaHistoricaOut {
  lacuna_id: string;
  fonte_id: string;
  entidade_afetada: string;
  data_inicio_lacuna: string | null;
  data_fim_lacuna: string | null;
  motivo_oficial: string;
  evidencia_url: string | null;
  pedido_lai_previsto: boolean;
}

export interface ColetaFonteOut {
  fonte_id: string;
  ultima_coleta_em: string;
  documentos_brutos: number;
}

export interface HealthOut {
  status: string;
  plataforma: string;
  natureza: string;
  banco_dados: string;
  versao_postgresql: string;
  modo_acesso: string;
  municipio_padrao: string;
  escopo_dados_ativo: string;
  contagens_persistidas: Record<string, number>;
  lacunas_historicas_documentadas: LacunaHistoricaOut[];
  ultima_coleta_por_fonte: ColetaFonteOut[];
}

export type CompetenciaStatus =
  | "FECHADA"
  | "ABERTA_SEM_PUBLICACAO"
  | "LACUNA_PARCIAL_LOTACAO";

export interface CustoMandatoMensalOut {
  custo_mensal_id: string;
  vereador_id: string;
  nome_politico: string | null;
  nome_exibicao: string | null;
  ano: number;
  mes: number;
  competencia_status: CompetenciaStatus | string;
  subsidio_bruto_vereador: string | null;
  subsidio_mensal_base: string | null;
  adicionais_ferias_decimo_terceiro_vereador: string | null;
  folha_bruta_gabinete: string | null;
  folha_mensal_gabinete: string | null;
  adicionais_ferias_decimo_terceiro_gabinete: string | null;
  quantidade_servidores_gabinete: number | null;
  diarias_atribuiveis_empenhadas: string | null;
  diarias_atribuiveis_liquidadas: string | null;
  diarias_atribuiveis_pagas: string | null;
  custo_estrutura_mandato_total: string | null;
  nota_cota_parlamentar: string;
  periodo_declaracao_ceap: string;
  metodologia_resumo: string;
  limitacoes_dados: string;
  avisos: string[];
  proveniencia: ProvenienciaOut;
}

export interface CustoMandatoResumoAnualOut {
  ano: number;
  competencias_fechadas: number;
  competencias_lacuna_parcial: number;
  competencias_abertas_null: number;
  subsidio_bruto_acumulado: string | null;
  folha_bruta_gabinete_acumulada: string | null;
  diarias_atribuiveis_pagas_acumuladas: string | null;
  custo_estrutura_mandato_acumulado: string | null;
  nota_cota_parlamentar: string;
  periodo_declaracao_ceap: string;
  metodologia_resumo: string;
  limitacoes_gerais: string;
  series_mensais: CustoMandatoMensalOut[];
}

export interface VereadorResumoOut {
  vereador_id: string;
  municipio_id: string;
  id_origem_nexlegis: number | null;
  nome_civil: string | null;
  nome_politico: string;
  nome_exibicao: string;
  slug: string;
  partido_sigla: string | null;
  condicao_mandato_2025_2028: string | null;
  avatar_url: string | null;
  sessoes_presente_2025: number;
  sessoes_ausente_ou_justificado_2025: number;
  total_proposicoes_parlamentares_2025: number;
  sessoes_presente_2026: number;
  sessoes_ausente_ou_justificado_2026: number;
  total_proposicoes_parlamentares_2026: number;
  custo_estrutura_mandato_acumulado_2026: string | null;
  competencias_custo_fechadas_2026: number;
  proveniencia: ProvenienciaOut;
}

export interface AliasVereadorOut {
  alias_texto: string;
  tipo_alias: string;
  fonte_origem: string;
  confianca: string;
}

export interface MandatoVereadorOut {
  mandato_id: string;
  legislatura_id: string;
  partido_id: string | null;
  condicao: string;
  cargo_mesa: string | null;
  votos_eleicao: number | null;
  valido_de: string;
  valido_ate: string | null;
}

export interface ResumoPresencaOut {
  total_sessoes_registradas: number;
  presentes: number;
  faltas_justificadas: number;
  ausentes: number;
  licencas: number;
}

export interface ProducaoPorTipoOut {
  ano: number;
  tipo_id_origem: number;
  tipo_proposicao: string;
  categoria: string;
  total_proposicoes: number;
}

export interface ProposicaoRecenteVereadorOut {
  proposicao_id: string;
  id_origem_nexlegis: number;
  nome_materia: string;
  tipo_id_origem: number;
  tipo_descricao_origem: string;
  ano: number;
  numero: string;
  ementa: string;
  data_publicacao: string | null;
  eh_proposicao_parlamentar: boolean;
  contabilizar_producao_vereador: boolean;
}

export interface VotoRecenteVereadorOut {
  voto_id: string;
  votacao_id: string;
  sessao_id: string;
  nome_sessao: string;
  data_sessao: string;
  proposicao_id: string;
  nome_materia: string;
  voto_descricao: string;
  voto_normalizado: string;
}

export interface VereadorDetalheOut {
  vereador_id: string;
  municipio_id: string;
  id_origem_nexlegis: number | null;
  nome_civil: string | null;
  nome_politico: string;
  nome_exibicao: string;
  slug: string;
  email_publico: string | null;
  avatar_url: string | null;
  biografia_texto: string | null;
  aliases: AliasVereadorOut[];
  mandatos: MandatoVereadorOut[];
  resumo_presenca_2025: ResumoPresencaOut | null;
  total_proposicoes_parlamentares_2025: number;
  producao_por_tipo_2025: ProducaoPorTipoOut[];
  resumo_presenca_2026: ResumoPresencaOut;
  total_proposicoes_parlamentares_2026: number;
  producao_por_tipo_2026: ProducaoPorTipoOut[];
  nota_metodologica_producao: string;
  proposicoes_recentes: ProposicaoRecenteVereadorOut[];
  votos_recentes_2025: VotoRecenteVereadorOut[];
  votos_recentes_2026: VotoRecenteVereadorOut[];
  custo_estrutura_mandato_2026: CustoMandatoResumoAnualOut | null;
  proveniencia: ProvenienciaOut;
}

export interface SessaoResumoOut {
  sessao_id: string;
  municipio_id: string;
  legislatura_id: string | null;
  id_origem_nexlegis: number;
  ids_origem_duplicados: number[];
  tipo_id_origem: number;
  tipo_descricao: string;
  numero: string;
  ano: number;
  nome_sessao: string;
  slug: string;
  data_abertura: string;
  horario_abertura: string | null;
  data_encerramento: string | null;
  horario_encerramento: string | null;
  quorum: number | null;
  ata_pdf_url: string | null;
  total_presentes: number;
  total_ausentes_ou_justificados: number;
  total_itens_pauta: number;
  total_votacoes: number;
  proveniencia: ProvenienciaOut;
}

export interface PresencaSessaoOut {
  presenca_id: string;
  vereador_id: string;
  nome_politico: string;
  nome_exibicao: string;
  slug: string;
  situacao_id_origem: number;
  situacao_descricao: string;
  status_normalizado: string;
}

export interface PautaItemSessaoOut {
  pauta_item_id: string;
  ordem: number;
  turno: number;
  tipo_pauta_id_origem: number | null;
  tipo_pauta_descricao: string | null;
  proposicao_id: string;
  id_origem_proposicao: number;
  nome_materia: string;
  tipo_id_origem: number;
  tipo_descricao_origem: string;
  ementa: string;
  eh_proposicao_parlamentar: boolean;
  unanime_flag_api: boolean;
  has_votos: boolean;
}

export interface VotoNominalItemOut {
  voto_id: string;
  vereador_id: string;
  nome_politico: string;
  nome_exibicao: string;
  voto_id_origem: number;
  voto_descricao: string;
  voto_normalizado: string;
}

export interface VotacaoSessaoOut {
  votacao_id: string;
  id_origem_nexlegis: number;
  proposicao_id: string;
  nome_materia: string;
  tipo_turno_id: number | null;
  unanime_flag_api: boolean;
  has_votos: boolean;
  placar_favoravel: number;
  placar_contrario: number;
  placar_abstencao: number;
  placar_ausente: number;
  discussed_at: string | null;
  started_at: string | null;
  closed_at: string | null;
  tempo_decorrido_segundos: number | null;
  votos_nominais: VotoNominalItemOut[];
}

export interface ResumoCidadaoOut {
  rotulo_transparencia: string;
  metodo_geracao: string;
  revisado_por_humano: boolean;
  o_que_e: string;
  o_que_propoe: string;
  situacao_e_resultado: string;
  texto_resumo_3_linhas: string;
  fonte_url: string;
  coletado_em: string;
}

export interface ContagemTipoBoletimOut {
  tipo_descricao: string;
  quantidade: number;
}

export interface DestaquePautaBoletimOut {
  proposicao_id: string;
  nome_materia: string;
  tipo_descricao_origem: string;
  ementa_original: string;
  autores_nomes: string[];
  placar_resumo: string;
  resumo_cidadao: ResumoCidadaoOut;
}

export interface PanoramaFinanceiroBoletimOut {
  ano: number;
  despesa_paga_acumulada: string | null;
  despesa_empenhada_liquida: string | null;
  duodecimo_recebido_acumulado: string | null;
  duodecimo_devolvido_acumulado: string | null;
  populacao_ibge_2026: number;
  meses_apurados: number;
  valor_por_habitante_mes: string | null;
  ultima_coleta_transparencia: string | null;
}

export interface SlideInstagramOut {
  numero: number;
  etiqueta: string;
  titulo: string;
  subtitulo: string;
  itens: string[];
  rodape_fonte: string;
}

export interface SessaoOpcaoBoletimOut {
  sessao_id: string;
  nome_sessao: string;
  data_abertura: string;
  tipo_descricao: string;
}

export interface BoletimSemanalOut {
  municipio_id: string;
  handle_instagram_oficial: string;
  dominio_oficial: string;
  sessao_id: string;
  nome_sessao: string;
  tipo_descricao: string;
  data_abertura: string;
  horario_abertura: string | null;
  ata_pdf_url: string | null;
  total_presentes: number;
  total_faltas_justificadas: number;
  total_ausentes: number;
  total_licencas: number;
  total_itens_pauta: number;
  total_proposicoes_parlamentares: number;
  total_votacoes: number;
  contagem_por_tipo: ContagemTipoBoletimOut[];
  destaques_pauta: DestaquePautaBoletimOut[];
  resumo_sessao: ResumoCidadaoOut;
  panorama_financeiro_2026: PanoramaFinanceiroBoletimOut;
  alerta_whatsapp: string;
  legenda_instagram: string;
  slides_instagram: SlideInstagramOut[];
  sessoes_disponiveis: SessaoOpcaoBoletimOut[];
  proveniencia: ProvenienciaOut;
}

export interface SessaoDetalheOut {
  sessao_id: string;
  municipio_id: string;
  legislatura_id: string | null;
  id_origem_nexlegis: number;
  ids_origem_duplicados: number[];
  tipo_id_origem: number;
  tipo_descricao: string;
  numero: string;
  ano: number;
  nome_sessao: string;
  slug: string;
  data_abertura: string;
  horario_abertura: string | null;
  data_encerramento: string | null;
  horario_encerramento: string | null;
  inicio_sessao_real: string | null;
  presidente_vereador_id: string | null;
  quorum: number | null;
  ata_pdf_url: string | null;
  presencas: PresencaSessaoOut[];
  pauta_itens: PautaItemSessaoOut[];
  votacoes: VotacaoSessaoOut[];
  resumo_cidadao: ResumoCidadaoOut | null;
  proveniencia: ProvenienciaOut;
}

export interface AutorMateriaOut {
  autoria_id: string;
  tipo_autor: string;
  vereador_id: string | null;
  nome_politico: string | null;
  nome_exibicao: string | null;
  slug: string | null;
  autor_institucional: string | null;
}

export interface MateriaResumoOut {
  proposicao_id: string;
  municipio_id: string;
  id_origem_nexlegis: number;
  tipo_id_origem: number;
  tipo_descricao_origem: string;
  numero: string;
  ano: number;
  nome_materia: string;
  slug: string | null;
  ementa: string;
  data_publicacao: string | null;
  ultima_movimentacao: string | null;
  situacao_atual: string | null;
  categoria_classificada: string;
  eh_proposicao_parlamentar: boolean;
  contabilizar_producao_vereador: boolean;
  autores: AutorMateriaOut[];
  proveniencia: ProvenienciaOut;
}

export interface TramitacaoMateriaOut {
  tramitacao_id: string;
  id_origem_nexlegis: number;
  data_tramitacao: string;
  local_origem: string | null;
  local_destino: string | null;
  situacao_descricao: string | null;
  prioridade_descricao: string | null;
  prazo_descricao: string | null;
  justificativa: string | null;
}

export interface DeliberacaoMateriaSessaoOut {
  sessao_id: string;
  id_origem_sessao: number;
  nome_sessao: string;
  data_sessao: string;
  ordem: number;
  turno: number;
  tipo_pauta_descricao: string | null;
  votacao_id: string | null;
  placar_favoravel: number;
  placar_contrario: number;
  placar_abstencao: number;
  votos_nominais: VotoNominalItemOut[];
}

export interface MateriaDetalheOut {
  proposicao_id: string;
  municipio_id: string;
  id_origem_nexlegis: number;
  tipo_id_origem: number;
  tipo_descricao_origem: string;
  numero: string;
  ano: number;
  nome_materia: string;
  slug: string | null;
  ementa: string;
  data_publicacao: string | null;
  ultima_movimentacao: string | null;
  situacao_atual: string | null;
  local_origem: string | null;
  local_destino: string | null;
  autoria_codigo_origem: number | null;
  anexo_principal_url: string | null;
  anexo_principal_nome: string | null;
  anexo_principal_mime: string | null;
  anexo_principal_tamanho: number | null;
  categoria_classificada: string;
  eh_proposicao_parlamentar: boolean;
  contabilizar_producao_vereador: boolean;
  justificativa_classificacao: string | null;
  autores: AutorMateriaOut[];
  tramitacoes: TramitacaoMateriaOut[];
  deliberacoes_em_sessao: DeliberacaoMateriaSessaoOut[];
  resumo_cidadao: ResumoCidadaoOut | null;
  proveniencia: ProvenienciaOut;
}

export interface FolhaPagamentoOut {
  folha_id: string;
  ano: number;
  mes: number;
  referencia: string;
  matricula: string;
  nome_servidor: string;
  cpf_mascarado: string;
  situacao: string | null;
  orgao: string;
  cargo: string;
  funcao: string | null;
  lotacao: string;
  data_admissao: string | null;
  data_exoneracao: string | null;
  tipo_admissao: string | null;
  tipo_folha: string;
  movimentacao: string | null;
  salario_base: string | null;
  remuneracao_bruta: string | null;
  descontos: string | null;
  remuneracao_liquida: string | null;
  eh_vereador: boolean;
  vereador_id: string | null;
  gabinete_vereador_id: string | null;
  proveniencia: ProvenienciaOut;
}

export interface DespesaEmpenhoOut {
  empenho_id: string;
  numero_empenho: string;
  ano: number;
  mes: number;
  data_empenho: string;
  fornecedor_id: string;
  favorecido_nome: string;
  documento_favorecido: string;
  tipo_pessoa_favorecido: string;
  valor_empenhado_bruto: string;
  valor_anulacao: string;
  valor_empenhado_liquido: string;
  valor_liquidado: string;
  valor_pago: string;
  saldo_pagar: string;
  historico: string;
  processo_licitatorio: string | null;
  elemento_despesa: string | null;
  subelemento_despesa: string | null;
  fonte_recurso: string | null;
  eh_diaria: boolean;
  vereador_beneficiario_id: string | null;
  proveniencia: ProvenienciaOut;
}

export interface TotaisDespesaOut {
  quantidade_empenhos: number;
  valor_empenhado_bruto: string;
  valor_anulacao: string;
  valor_empenhado_liquido: string;
  valor_liquidado: string;
  valor_pago: string;
  saldo_pagar: string;
}

export interface DespesaPorElementoOut extends TotaisDespesaOut {
  elemento_despesa: string | null;
}

export interface FavorecidoDespesaOut extends TotaisDespesaOut {
  fornecedor_id: string;
  favorecido_nome: string;
  documento_favorecido: string;
  tipo_pessoa_favorecido: string;
}

export interface DespesasResumoOut {
  ano: number;
  data_primeiro_empenho: string | null;
  data_ultimo_empenho: string | null;
  totais: TotaisDespesaOut;
  por_elemento: DespesaPorElementoOut[];
  favorecidos: FavorecidoDespesaOut[];
  nota_metodologica: string;
  fonte_url: string | null;
  ultima_coleta_em: string | null;
}

export interface DiariaOut {
  diaria_id: string;
  empenho_id: string | null;
  numero_empenho: string;
  ano: number;
  mes: number;
  data_concessao: string;
  beneficiario_nome: string;
  cpf_mascarado: string;
  tipo_beneficiario: string;
  vereador_id_verificado: string | null;
  gabinete_vereador_id: string | null;
  cargo_beneficiario: string | null;
  identificacao_documental_verificavel: boolean;
  destino_ou_finalidade: string;
  valor_empenhado_liquido: string;
  valor_liquidado: string;
  valor_pago: string;
  origem_registro: string;
  proveniencia: ProvenienciaOut;
}

export interface DuodecimoOut {
  duodecimo_id: string;
  id_origem: string;
  ano: number;
  mes: number;
  data_lancamento: string;
  tipo_codigo: string;
  tipo_natureza: string;
  descricao: string;
  valor: string;
  proveniencia: ProvenienciaOut;
}

export interface DeclaracaoTransparenciaOut {
  declaracao_id: string;
  tipo_declaracao: string;
  titulo_oficial: string;
  texto_integral: string;
  data_inicio_cobertura: string;
  data_fim_cobertura: string;
  data_atualizacao: string | null;
  signatario_presidente: string | null;
  signatario_certificador: string | null;
  observacao_cruzamento: string | null;
  proveniencia: ProvenienciaOut;
}

export interface ItemBuscaOut {
  tipo: "proposicao" | "norma" | "vereador" | "sessao" | "despesa";
  id: string;
  titulo: string;
  subtitulo: string | null;
  trecho_destaque: string | null;
  data_referencia: string | null;
  ano: number | null;
  url_interna: string;
  fonte_url: string | null;
  relevancia: number;
}

export interface BuscaUnificadaOut {
  termo: string;
  categoria: string;
  ano: number | null;
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  contagem_por_tipo: Record<string, number>;
  items: ItemBuscaOut[];
}

export interface TemaContagemOut {
  tema: string;
  quantidade: number;
}

export interface BairroResumoOut {
  bairro_id: string;
  slug: string;
  nome_oficial: string;
  regiao: string;
  tipo_localidade: string;
  latitude_aprox: string | null;
  longitude_aprox: string | null;
  total_proposicoes: number;
  tema_mais_frequente: string | null;
  ultimo_registro: string | null;
}

export interface BairrosPainelOut {
  municipio_id: string;
  ano_filtro: number | null;
  tema_filtro: string | null;
  proposicoes_parlamentares_total: number;
  proposicoes_com_bairro: number;
  proposicoes_sem_bairro: number;
  nota_metodologica: string;
  temas_disponiveis: TemaContagemOut[];
  bairros: BairroResumoOut[];
}

export interface ProposicaoBairroItemOut {
  proposicao_id: string;
  nome_materia: string;
  tipo_descricao_origem: string;
  ano: number;
  data_publicacao: string | null;
  ementa: string | null;
  situacao_atual: string | null;
  tema_principal: string;
  trecho_evidencia: string;
  autores_nomes: string[];
  fonte_url: string;
}

export interface VereadorBairroContagemOut {
  vereador_id: string;
  nome_exibicao: string;
  slug: string;
  quantidade_proposicoes: number;
}

export interface BairroDetalheOut {
  bairro: BairroResumoOut;
  temas: TemaContagemOut[];
  vereadores_autores: VereadorBairroContagemOut[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  proposicoes: ProposicaoBairroItemOut[];
}

export interface NormaResumoOut {
  norma_id: string;
  tabela_origem: string;
  id_origem: number;
  numero: string;
  ano: number | null;
  tipo_norma: string;
  categoria_descricao: string;
  data_publicacao: string | null;
  ementa: string;
  total_anexos: number;
  status_ocr: string;
  extraido_por_ocr: boolean;
  requer_revisao_humana: boolean;
  fonte_url: string;
  coletado_em: string;
}

export interface NormasListagemOut {
  municipio_id: string;
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  categorias_disponiveis: string[];
  anos_disponiveis: number[];
  nota_cobertura: string;
  items: NormaResumoOut[];
}

export interface NormaDetalheOut extends NormaResumoOut {
  data_publicacao_portal: string | null;
  texto_extraido: string | null;
  ocr_engine_versao: string | null;
  ocr_confianca_media: string | null;
  motivo_revisao_humana: string | null;
  resumo_cidadao: ResumoCidadaoOut;
  proveniencia: ProvenienciaOut;
}

export interface ComparativoMunicipioOut {
  comparativo_id: string;
  codigo_ibge: string;
  ente_nome: string;
  uf: string;
  eh_municipio_foco: boolean;
  ano: number;
  populacao_siconfi: number | null;
  despesa_empenhada: string | null;
  despesa_liquidada: string | null;
  despesa_paga: string | null;
  despesa_paga_per_capita_ano: string | null;
  despesa_paga_per_capita_mes: string | null;
  despesa_paga_ano_anterior: string | null;
  variacao_pct_ano_anterior: string | null;
  fonte_url: string;
  coletado_em: string;
}

export interface ComparativoSiconfiOut {
  municipio_id: string;
  ano_selecionado: number;
  anos_disponiveis: number[];
  fonte_oficial: string;
  anexo_siconfi: string;
  funcao_descricao: string;
  nota_metodologica: string;
  media_per_capita_ano_grupo: string | null;
  mediana_per_capita_ano_grupo: string | null;
  municipios: ComparativoMunicipioOut[];
}
