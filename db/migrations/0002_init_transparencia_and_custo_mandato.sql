-- =============================================================================
-- Cerrado Aberto — Plataforma Cidadã Independente de Transparência Legislativa
-- Migração 0002: Portal da Transparência CENTI/NúcleoGov e Custo da Estrutura do Mandato (Fase 2)
-- Banco: PostgreSQL 16+
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Fornecedores e Favorecidos (com proteção LGPD para Pessoa Física)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fornecedor (
    fornecedor_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    nome VARCHAR(250) NOT NULL,
    chave_busca VARCHAR(250) NOT NULL,
    documento_mascarado_ou_cnpj VARCHAR(32) NOT NULL, -- CNPJ 14 dígitos (PJ) ou '***.***.***-**' (PF)
    tipo_pessoa VARCHAR(32) NOT NULL, -- 'PESSOA_JURIDICA' ou 'PESSOA_FISICA'
    cnpj_valido BOOLEAN,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, chave_busca, documento_mascarado_ou_cnpj)
);

CREATE INDEX IF NOT EXISTS idx_fornecedor_chave_busca
    ON fornecedor (municipio_id, chave_busca);

-- -----------------------------------------------------------------------------
-- 2. Folha de Pagamento, Subsídios e Lotação de Gabinete (servidores_cnt)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS folha_pagamento (
    folha_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    referencia VARCHAR(40) NOT NULL,
    matricula VARCHAR(32) NOT NULL,
    nome_servidor VARCHAR(200) NOT NULL,
    cpf_mascarado VARCHAR(16) NOT NULL DEFAULT '***.***.***-**',
    situacao VARCHAR(60),
    orgao VARCHAR(160) NOT NULL,
    cargo VARCHAR(160) NOT NULL,
    funcao VARCHAR(160),
    lotacao VARCHAR(160) NOT NULL,
    local_trabalho VARCHAR(160),
    decreto_nomeacao VARCHAR(120),
    possui_estabilidade VARCHAR(32),
    data_admissao DATE,
    data_exoneracao DATE,
    tipo_admissao VARCHAR(80),
    carga_horaria VARCHAR(40),
    tipo_folha VARCHAR(80) NOT NULL,
    movimentacao VARCHAR(60),
    salario_base NUMERIC(14,2),
    remuneracao_bruta NUMERIC(14,2),
    descontos NUMERIC(14,2),
    remuneracao_liquida NUMERIC(14,2),
    eh_vereador BOOLEAN NOT NULL DEFAULT FALSE,
    vereador_id VARCHAR(64) REFERENCES vereador(vereador_id),
    gabinete_vereador_id VARCHAR(64) REFERENCES vereador(vereador_id),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, ano, mes, matricula, tipo_folha)
);

CREATE INDEX IF NOT EXISTS idx_folha_pagamento_competencia
    ON folha_pagamento (municipio_id, ano, mes);

CREATE INDEX IF NOT EXISTS idx_folha_pagamento_vereador
    ON folha_pagamento (municipio_id, vereador_id, ano, mes);

CREATE INDEX IF NOT EXISTS idx_folha_pagamento_gabinete
    ON folha_pagamento (municipio_id, gabinete_vereador_id, ano, mes);

-- -----------------------------------------------------------------------------
-- 3. Despesas, Empenhos, Liquidações e Pagamentos (cntdespesas)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS despesa_empenho (
    empenho_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    numero_empenho VARCHAR(40) NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    data_empenho DATE NOT NULL,
    fornecedor_id VARCHAR(80) NOT NULL REFERENCES fornecedor(fornecedor_id),
    favorecido_nome VARCHAR(250) NOT NULL,
    documento_favorecido VARCHAR(32) NOT NULL,
    tipo_pessoa_favorecido VARCHAR(32) NOT NULL,
    valor_empenhado_bruto NUMERIC(14,2) NOT NULL,
    valor_anulacao NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    valor_empenhado_liquido NUMERIC(14,2) NOT NULL,
    valor_liquidado NUMERIC(14,2) NOT NULL,
    valor_pago NUMERIC(14,2) NOT NULL,
    saldo_pagar NUMERIC(14,2) NOT NULL,
    historico TEXT NOT NULL,
    orgao VARCHAR(160),
    processo_licitatorio VARCHAR(160),
    destinacao_recurso VARCHAR(200),
    unidade VARCHAR(160),
    funcao VARCHAR(120),
    subfuncao VARCHAR(120),
    programa VARCHAR(160),
    acao VARCHAR(160),
    categoria_economica VARCHAR(160),
    grupo_despesa VARCHAR(160),
    modalidade_aplicacao VARCHAR(250),
    elemento_despesa VARCHAR(160),
    subelemento_despesa VARCHAR(200),
    fonte_recurso VARCHAR(160),
    eh_diaria BOOLEAN NOT NULL DEFAULT FALSE,
    vereador_beneficiario_id VARCHAR(64) REFERENCES vereador(vereador_id),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, numero_empenho, data_empenho)
);

CREATE INDEX IF NOT EXISTS idx_despesa_empenho_data
    ON despesa_empenho (municipio_id, ano, mes, data_empenho DESC);

CREATE INDEX IF NOT EXISTS idx_despesa_empenho_elemento
    ON despesa_empenho (municipio_id, elemento_despesa);

ALTER TABLE despesa_empenho
    ALTER COLUMN categoria_economica TYPE VARCHAR(160),
    ALTER COLUMN grupo_despesa TYPE VARCHAR(160),
    ALTER COLUMN modalidade_aplicacao TYPE VARCHAR(250),
    ALTER COLUMN elemento_despesa TYPE VARCHAR(160),
    ALTER COLUMN subelemento_despesa TYPE VARCHAR(200);

-- -----------------------------------------------------------------------------
-- 4. Diárias (Cruzamento cntdiarias + Elemento 14 de cntdespesas)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS diaria (
    diaria_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    empenho_id VARCHAR(80) REFERENCES despesa_empenho(empenho_id),
    numero_empenho VARCHAR(40) NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    data_concessao DATE NOT NULL,
    beneficiario_nome VARCHAR(200) NOT NULL,
    cpf_mascarado VARCHAR(16) NOT NULL DEFAULT '***.***.***-**',
    tipo_beneficiario VARCHAR(40) NOT NULL, -- 'VEREADOR', 'SERVIDOR_GABINETE', 'SERVIDOR_ADMINISTRATIVO'
    vereador_id_verificado VARCHAR(64) REFERENCES vereador(vereador_id),
    gabinete_vereador_id VARCHAR(64) REFERENCES vereador(vereador_id),
    cargo_beneficiario VARCHAR(160),
    identificacao_documental_verificavel BOOLEAN NOT NULL DEFAULT TRUE,
    destino_ou_finalidade TEXT NOT NULL,
    valor_empenhado_liquido NUMERIC(14,2) NOT NULL,
    valor_liquidado NUMERIC(14,2) NOT NULL,
    valor_pago NUMERIC(14,2) NOT NULL,
    origem_registro VARCHAR(60) NOT NULL,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, numero_empenho)
);

-- -----------------------------------------------------------------------------
-- 5. Receitas e Devoluções de Duodécimo (sgduodecimo)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS receita_duodecimo (
    duodecimo_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    id_origem VARCHAR(32) NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    data_lancamento DATE NOT NULL,
    tipo_codigo VARCHAR(16) NOT NULL,
    tipo_natureza VARCHAR(40) NOT NULL, -- 'RECEITA_REPASSE' ou 'DEVOLUCAO_DUODECIMO'
    descricao VARCHAR(250) NOT NULL,
    valor NUMERIC(14,2) NOT NULL,
    arquivo_nome VARCHAR(255),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, id_origem)
);

-- -----------------------------------------------------------------------------
-- 6. Declarações Oficiais de Transparência (CEAP e Diárias)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS declaracao_oficial_transparencia (
    declaracao_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    tipo_declaracao VARCHAR(60) NOT NULL,
    titulo_oficial VARCHAR(200) NOT NULL,
    texto_integral TEXT NOT NULL,
    data_inicio_cobertura DATE NOT NULL,
    data_fim_cobertura DATE NOT NULL,
    data_atualizacao DATE,
    signatario_presidente VARCHAR(160),
    signatario_certificador VARCHAR(160),
    observacao_cruzamento TEXT,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 7. Indicador Composto: Custo da Estrutura do Mandato por Competência (ADR-005)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS custo_estrutura_mandato_mensal (
    custo_mensal_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    vereador_id VARCHAR(64) NOT NULL REFERENCES vereador(vereador_id),
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    competencia_status VARCHAR(40) NOT NULL, -- 'FECHADA', 'ABERTA_SEM_PUBLICACAO', 'LACUNA_PARCIAL_LOTACAO'
    subsidio_bruto_vereador NUMERIC(14,2),
    subsidio_mensal_base NUMERIC(14,2),
    adicionais_ferias_decimo_terceiro_vereador NUMERIC(14,2),
    folha_bruta_gabinete NUMERIC(14,2),
    folha_mensal_gabinete NUMERIC(14,2),
    adicionais_ferias_decimo_terceiro_gabinete NUMERIC(14,2),
    quantidade_servidores_gabinete INTEGER,
    diarias_atribuiveis_empenhadas NUMERIC(14,2),
    diarias_atribuiveis_liquidadas NUMERIC(14,2),
    diarias_atribuiveis_pagas NUMERIC(14,2),
    custo_estrutura_mandato_total NUMERIC(14,2),
    nota_cota_parlamentar TEXT NOT NULL,
    periodo_declaracao_ceap VARCHAR(40) NOT NULL DEFAULT '2020–2026',
    metodologia_resumo TEXT NOT NULL,
    limitacoes_dados TEXT NOT NULL,
    avisos JSONB NOT NULL DEFAULT '[]'::jsonb,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, vereador_id, ano, mes)
);

CREATE INDEX IF NOT EXISTS idx_custo_estrutura_mandato_vereador
    ON custo_estrutura_mandato_mensal (municipio_id, vereador_id, ano, mes);

COMMIT;
