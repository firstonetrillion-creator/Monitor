-- =============================================================================
-- Cerrado Aberto — Plataforma Cidadã Independente de Transparência Legislativa
-- Migração 0001: Fundação de Dados, Proveniência, Multi-Município e Nexlegis
-- Banco: PostgreSQL 16+
-- =============================================================================

BEGIN;

DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE EXTENSION IF NOT EXISTS unaccent;
EXCEPTION
    WHEN OTHERS THEN
        NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 1. Estrutura Multi-Município e Fontes Oficiais
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS municipio (
    municipio_id VARCHAR(64) PRIMARY KEY,
    codigo_ibge CHAR(7) NOT NULL UNIQUE,
    nome VARCHAR(120) NOT NULL,
    uf CHAR(2) NOT NULL,
    populacao_estimada INTEGER,
    ano_populacao INTEGER,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS casa_legislativa (
    casa_id VARCHAR(64) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    nome_oficial VARCHAR(200) NOT NULL,
    cnpj CHAR(14),
    endereco VARCHAR(300),
    site_institucional_url TEXT,
    portal_transparencia_url TEXT,
    sistema_legislativo_url TEXT,
    esic_url TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS legislatura (
    legislatura_id VARCHAR(64) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    numero INTEGER,
    ano_inicio INTEGER NOT NULL,
    ano_fim INTEGER NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    cadeiras INTEGER NOT NULL DEFAULT 13,
    UNIQUE (municipio_id, ano_inicio, ano_fim)
);

CREATE TABLE IF NOT EXISTS partido (
    partido_id VARCHAR(32) PRIMARY KEY,
    sigla VARCHAR(32) NOT NULL UNIQUE,
    nome_oficial VARCHAR(160) NOT NULL,
    numero_tse INTEGER
);

CREATE TABLE IF NOT EXISTS fonte (
    fonte_id VARCHAR(64) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    nome VARCHAR(120) NOT NULL,
    url_base TEXT NOT NULL,
    tipo_acesso VARCHAR(40) NOT NULL, -- 'REST_JSON', 'XHR_POST_JSON', 'HTML', 'PDF_S3'
    crawl_delay_segundos NUMERIC(5,2) NOT NULL DEFAULT 5.0,
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes TEXT
);

-- -----------------------------------------------------------------------------
-- 2. Observabilidade, Proveniência, Armazenamento Bruto e Lacunas Históricas
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS coleta_execucao (
    execucao_id UUID PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    versao_coletor VARCHAR(64) NOT NULL,
    iniciado_em TIMESTAMPTZ NOT NULL,
    finalizado_em TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL, -- 'EM_ANDAMENTO', 'SUCESSO', 'ERRO', 'PARCIAL'
    registros_lidos INTEGER NOT NULL DEFAULT 0,
    registros_novos INTEGER NOT NULL DEFAULT 0,
    registros_alterados INTEGER NOT NULL DEFAULT 0,
    registros_inalterados INTEGER NOT NULL DEFAULT 0,
    registros_erro INTEGER NOT NULL DEFAULT 0,
    hash_esquema_observado VARCHAR(64),
    relatorio_qualidade JSONB,
    erro_mensagem TEXT
);

CREATE TABLE IF NOT EXISTS documento_bruto (
    documento_id UUID PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    execucao_id UUID REFERENCES coleta_execucao(execucao_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL, -- SHA-256
    versao_coletor VARCHAR(64) NOT NULL,
    storage_backend VARCHAR(32) NOT NULL DEFAULT 'local', -- 'local' ou 's3'
    caminho_armazenamento TEXT NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    tamanho_bytes BIGINT NOT NULL,
    status_http INTEGER,
    url_temporaria BOOLEAN NOT NULL DEFAULT FALSE,
    processado_ocr BOOLEAN NOT NULL DEFAULT FALSE,
    extraido_por_ocr BOOLEAN NOT NULL DEFAULT FALSE,
    ocr_engine_versao VARCHAR(64),
    ocr_confianca_media NUMERIC(5,2),
    requer_revisao_humana BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_revisao_humana TEXT,
    texto_extraido TEXT,
    UNIQUE (municipio_id, fonte_id, hash_conteudo, fonte_url)
);

CREATE TABLE IF NOT EXISTS lacuna_historica (
    lacuna_id VARCHAR(64) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    entidade_afetada VARCHAR(80) NOT NULL,
    data_inicio_lacuna DATE,
    data_fim_lacuna DATE,
    motivo_oficial TEXT NOT NULL,
    evidencia_url TEXT,
    pedido_lai_previsto BOOLEAN NOT NULL DEFAULT TRUE,
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    registrado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 3. Entidades Mestre: Vereadores, Aliases e Mandatos
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS vereador (
    vereador_id VARCHAR(64) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    id_origem_nexlegis INTEGER,
    nome_civil VARCHAR(200),
    nome_politico VARCHAR(160) NOT NULL,
    nome_exibicao VARCHAR(160) NOT NULL,
    slug VARCHAR(160) NOT NULL,
    chave_busca VARCHAR(200) NOT NULL,
    email_publico VARCHAR(200),
    avatar_url TEXT,
    biografia_html TEXT,
    biografia_texto TEXT,
    -- Proveniência obrigatória
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    valido_de TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valido_ate TIMESTAMPTZ,
    UNIQUE (municipio_id, id_origem_nexlegis),
    UNIQUE (municipio_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_vereador_chave_busca
    ON vereador (municipio_id, chave_busca);

DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_vereador_chave_busca_trgm
        ON vereador USING gin (chave_busca gin_trgm_ops);
EXCEPTION
    WHEN OTHERS THEN
        NULL;
END $$;

CREATE TABLE IF NOT EXISTS vereador_alias (
    alias_id SERIAL PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    vereador_id VARCHAR(64) NOT NULL REFERENCES vereador(vereador_id),
    alias_texto VARCHAR(200) NOT NULL,
    alias_chave_busca VARCHAR(200) NOT NULL,
    tipo_alias VARCHAR(40) NOT NULL, -- 'NOME_POLITICO', 'NOME_CIVIL', 'LOTACAO_GABINETE', 'VARIACAO_GRAFIA'
    fonte_origem VARCHAR(64) NOT NULL,
    confianca VARCHAR(20) NOT NULL DEFAULT 'ALTA', -- 'ALTA' (curado), 'MEDIA', 'BAIXA'
    curado_por VARCHAR(100) NOT NULL DEFAULT 'curadoria_inicial_fase_1',
    decidido_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (municipio_id, alias_chave_busca, tipo_alias)
);

CREATE TABLE IF NOT EXISTS mandato (
    mandato_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    vereador_id VARCHAR(64) NOT NULL REFERENCES vereador(vereador_id),
    legislatura_id VARCHAR(64) NOT NULL REFERENCES legislatura(legislatura_id),
    partido_id VARCHAR(32) REFERENCES partido(partido_id),
    condicao VARCHAR(32) NOT NULL DEFAULT 'TITULAR', -- 'TITULAR', 'SUPLENTE'
    cargo_mesa VARCHAR(80),
    votos_eleicao INTEGER,
    valido_de DATE NOT NULL,
    valido_ate DATE,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 4. Vocabulário Controlado e Classificação de Proposições (ADR-005, Decisão 4)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS de_para_tipo_proposicao (
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    tipo_id_origem INTEGER NOT NULL,
    descricao_origem VARCHAR(120) NOT NULL,
    codigo_normalizado VARCHAR(64) NOT NULL,
    nome_exibicao VARCHAR(120) NOT NULL,
    categoria VARCHAR(64) NOT NULL,
    -- 'PROPOSICAO_PARLAMENTAR', 'PROPOSICAO_EXECUTIVO', 'ATO_ADMINISTRATIVO_SESSAO', 'JULGAMENTO_EXTERNO'
    eh_proposicao_parlamentar BOOLEAN NOT NULL,
    contabilizar_producao_vereador BOOLEAN NOT NULL,
    justificativa_classificacao TEXT NOT NULL,
    versao_regra VARCHAR(32) NOT NULL DEFAULT 'ADR-005-v1',
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (municipio_id, tipo_id_origem)
);

-- -----------------------------------------------------------------------------
-- 5. Atividade Legislativa: Sessões, Presenças, Proposições, Pautas e Votações
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sessao (
    sessao_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    legislatura_id VARCHAR(64) REFERENCES legislatura(legislatura_id),
    id_origem_nexlegis INTEGER NOT NULL,
    ids_origem_duplicados INTEGER[] NOT NULL DEFAULT '{}',
    tipo_id_origem INTEGER NOT NULL,
    tipo_descricao VARCHAR(100) NOT NULL,
    numero VARCHAR(32) NOT NULL,
    ano INTEGER NOT NULL,
    nome_sessao VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL,
    data_abertura DATE NOT NULL,
    horario_abertura TIME,
    data_encerramento DATE,
    horario_encerramento TIME,
    inicio_sessao_real TIMESTAMPTZ,
    presidente_vereador_id VARCHAR(64) REFERENCES vereador(vereador_id),
    quorum INTEGER,
    ata_pdf_url TEXT,
    -- Proveniência obrigatória
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    valido_de TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valido_ate TIMESTAMPTZ,
    UNIQUE (municipio_id, id_origem_nexlegis),
    UNIQUE (municipio_id, tipo_id_origem, numero, ano, data_abertura)
);

CREATE TABLE IF NOT EXISTS presenca (
    presenca_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    sessao_id VARCHAR(80) NOT NULL REFERENCES sessao(sessao_id),
    vereador_id VARCHAR(64) NOT NULL REFERENCES vereador(vereador_id),
    situacao_id_origem INTEGER NOT NULL,
    situacao_descricao VARCHAR(80) NOT NULL,
    status_normalizado VARCHAR(40) NOT NULL, -- 'PRESENTE', 'FALTA_JUSTIFICADA', 'AUSENTE', 'LICENCA'
    -- Proveniência obrigatória
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, sessao_id, vereador_id)
);

CREATE TABLE IF NOT EXISTS proposicao (
    proposicao_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    id_origem_nexlegis INTEGER NOT NULL,
    tipo_id_origem INTEGER NOT NULL,
    tipo_descricao_origem VARCHAR(120) NOT NULL,
    numero VARCHAR(32) NOT NULL,
    ano INTEGER NOT NULL,
    nome_materia VARCHAR(200) NOT NULL,
    slug VARCHAR(220),
    ementa TEXT NOT NULL,
    data_publicacao DATE,
    ultima_movimentacao DATE,
    situacao_atual VARCHAR(100),
    local_origem VARCHAR(120),
    local_destino VARCHAR(120),
    autoria_codigo_origem INTEGER,
    anexo_principal_url TEXT,
    anexo_principal_nome VARCHAR(255),
    anexo_principal_mime VARCHAR(120),
    anexo_principal_tamanho BIGINT,
    -- Classificação derivada de de_para_tipo_proposicao (ADR-005)
    categoria_classificada VARCHAR(64) NOT NULL,
    eh_proposicao_parlamentar BOOLEAN NOT NULL,
    contabilizar_producao_vereador BOOLEAN NOT NULL,
    -- Proveniência obrigatória
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    valido_de TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valido_ate TIMESTAMPTZ,
    UNIQUE (municipio_id, id_origem_nexlegis),
    FOREIGN KEY (municipio_id, tipo_id_origem)
        REFERENCES de_para_tipo_proposicao(municipio_id, tipo_id_origem)
);

CREATE TABLE IF NOT EXISTS autoria (
    autoria_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    proposicao_id VARCHAR(80) NOT NULL REFERENCES proposicao(proposicao_id),
    vereador_id VARCHAR(64) REFERENCES vereador(vereador_id),
    autor_institucional VARCHAR(160), -- ex.: 'PODER EXECUTIVO', 'MESA DIRETORA', 'SECRETARIA GERAL'
    tipo_autor VARCHAR(40) NOT NULL, -- 'VEREADOR', 'EXECUTIVO', 'MESA_DIRETORA', 'OUTRO'
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS tramitacao (
    tramitacao_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    proposicao_id VARCHAR(80) NOT NULL REFERENCES proposicao(proposicao_id),
    id_origem_nexlegis INTEGER NOT NULL,
    data_tramitacao DATE NOT NULL,
    local_origem VARCHAR(120),
    local_destino VARCHAR(120),
    situacao_descricao VARCHAR(120),
    prioridade_descricao VARCHAR(80),
    prazo_descricao VARCHAR(80),
    justificativa TEXT,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, id_origem_nexlegis)
);

CREATE TABLE IF NOT EXISTS pauta_item (
    pauta_item_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    sessao_id VARCHAR(80) NOT NULL REFERENCES sessao(sessao_id),
    proposicao_id VARCHAR(80) NOT NULL REFERENCES proposicao(proposicao_id),
    ordem INTEGER NOT NULL DEFAULT 0,
    turno INTEGER NOT NULL DEFAULT 1,
    tipo_pauta_id_origem INTEGER,
    tipo_pauta_descricao VARCHAR(80),
    unanime BOOLEAN NOT NULL DEFAULT FALSE,
    has_votos BOOLEAN NOT NULL DEFAULT FALSE,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, sessao_id, proposicao_id, turno, ordem)
);

CREATE TABLE IF NOT EXISTS votacao (
    votacao_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    id_origem_nexlegis INTEGER NOT NULL,
    sessao_id VARCHAR(80) NOT NULL REFERENCES sessao(sessao_id),
    proposicao_id VARCHAR(80) NOT NULL REFERENCES proposicao(proposicao_id),
    tipo_turno_id INTEGER,
    unanime BOOLEAN NOT NULL DEFAULT FALSE,
    has_votos BOOLEAN NOT NULL DEFAULT FALSE,
    discussed_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    tempo_decorrido_segundos INTEGER,
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, id_origem_nexlegis)
);

CREATE TABLE IF NOT EXISTS voto (
    voto_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    votacao_id VARCHAR(80) NOT NULL REFERENCES votacao(votacao_id),
    vereador_id VARCHAR(64) NOT NULL REFERENCES vereador(vereador_id),
    voto_id_origem INTEGER NOT NULL,
    voto_descricao VARCHAR(80) NOT NULL,
    voto_normalizado VARCHAR(40) NOT NULL, -- 'FAVORAVEL', 'CONTRARIO', 'ABSTENCAO', 'AUSENTE'
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, votacao_id, vereador_id)
);

-- -----------------------------------------------------------------------------
-- 6. Views Analíticas com Regras de Negócio Documentadas (ADR-005)
-- -----------------------------------------------------------------------------

-- View de produção parlamentar que exclui Atas (144), Julgamentos de Contas (211)
-- e outros atos administrativos, mantendo todos os registros intactos na tabela proposicao.
CREATE OR REPLACE VIEW vw_producao_legislativa_vereador AS
SELECT
    v.municipio_id,
    v.vereador_id,
    v.nome_politico,
    v.slug,
    p.ano,
    p.tipo_id_origem,
    tp.nome_exibicao AS tipo_proposicao,
    tp.categoria,
    COUNT(DISTINCT p.proposicao_id) AS total_proposicoes,
    MAX(p.coletado_em) AS ultima_coleta_em
FROM vereador v
JOIN autoria a
    ON a.municipio_id = v.municipio_id
   AND a.vereador_id = v.vereador_id
JOIN proposicao p
    ON p.municipio_id = a.municipio_id
   AND p.proposicao_id = a.proposicao_id
   AND p.valido_ate IS NULL
JOIN de_para_tipo_proposicao tp
    ON tp.municipio_id = p.municipio_id
   AND tp.tipo_id_origem = p.tipo_id_origem
WHERE v.valido_ate IS NULL
  AND p.contabilizar_producao_vereador = TRUE
  AND tp.contabilizar_producao_vereador = TRUE
GROUP BY
    v.municipio_id,
    v.vereador_id,
    v.nome_politico,
    v.slug,
    p.ano,
    p.tipo_id_origem,
    tp.nome_exibicao,
    tp.categoria;

-- -----------------------------------------------------------------------------
-- 7. Carga Inicial de Sementes (Inhumas/GO, Fontes, Vocabulário Controlado e Lacunas)
-- -----------------------------------------------------------------------------

INSERT INTO municipio (municipio_id, codigo_ibge, nome, uf, populacao_estimada, ano_populacao)
VALUES ('inhumas-go', '5210000', 'Inhumas', 'GO', 52204, 2022)
ON CONFLICT (municipio_id) DO NOTHING;

INSERT INTO casa_legislativa (
    casa_id, municipio_id, nome_oficial, endereco,
    site_institucional_url, portal_transparencia_url, sistema_legislativo_url, esic_url
)
VALUES (
    'cm-inhumas-go',
    'inhumas-go',
    'Câmara Municipal de Inhumas',
    'Praça Santana, nº 227, Centro, Inhumas - GO, CEP 75400-000',
    'https://inhumas.go.leg.br/',
    'https://acessoainformacao.inhumas.go.leg.br/',
    'https://inhumas.nexlegis.com.br/',
    'https://acessoainformacao.inhumas.go.leg.br/cidadao/informacao/sic'
)
ON CONFLICT (casa_id) DO NOTHING;

INSERT INTO legislatura (legislatura_id, municipio_id, numero, ano_inicio, ano_fim, data_inicio, data_fim, cadeiras)
VALUES
    ('inhumas-go-2017-2020', 'inhumas-go', 18, 2017, 2020, '2017-01-01', '2020-12-31', 13),
    ('inhumas-go-2021-2024', 'inhumas-go', 19, 2021, 2024, '2021-01-01', '2024-12-31', 13),
    ('inhumas-go-2025-2028', 'inhumas-go', 20, 2025, 2028, '2025-01-01', '2028-12-31', 15)
ON CONFLICT (legislatura_id) DO NOTHING;

INSERT INTO partido (partido_id, sigla, nome_oficial, numero_tse)
VALUES
    ('PSD', 'PSD', 'Partido Social Democrático', 55),
    ('PL', 'PL', 'Partido Liberal', 22),
    ('PSB', 'PSB', 'Partido Socialista Brasileiro', 40),
    ('PP', 'PP', 'Progressistas', 11),
    ('MDB', 'MDB', 'Movimento Democrático Brasileiro', 15),
    ('UNIAO', 'UNIÃO', 'União Brasil', 44),
    ('DEM', 'DEM', 'Democratas (extinto/fundido ao União Brasil)', 25),
    ('PSL', 'PSL', 'Partido Social Liberal (extinto/fundido ao União Brasil)', 17),
    ('PSDB', 'PSDB', 'Partido da Social Democracia Brasileira', 45),
    ('PCDOB', 'PCdoB', 'Partido Comunista do Brasil', 65)
ON CONFLICT (partido_id) DO NOTHING;

INSERT INTO fonte (fonte_id, municipio_id, nome, url_base, tipo_acesso, crawl_delay_segundos, observacoes)
VALUES
    ('nexlegis', 'inhumas-go', 'Nexlegis — Sistema de Processo Legislativo', 'https://inhumas.nexlegis.com.br/api', 'REST_JSON', 3.0, 'API REST pública em JSON sem autenticação.'),
    ('transparencia_centi', 'inhumas-go', 'Portal da Transparência CENTI', 'https://acessoainformacao.inhumas.go.leg.br/api/centi', 'XHR_POST_JSON', 5.0, 'ERP CENTI migrado em 02/09/2026.'),
    ('transparencia_nucleogov', 'inhumas-go', 'Portal da Transparência NúcleoGov', 'https://acessoainformacao.inhumas.go.leg.br/api', 'XHR_POST_JSON', 5.0, 'Módulos sgduodecimo e sggastosparlamentares.'),
    ('legislacao_nucleogov', 'inhumas-go', 'Legislação Municipal NúcleoGov', 'https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis', 'XHR_POST_JSON', 5.0, 'Metadados em JSON + PDFs digitalizados no S3 com URL temporária.')
ON CONFLICT (fonte_id) DO NOTHING;

INSERT INTO de_para_tipo_proposicao (
    municipio_id, tipo_id_origem, descricao_origem, codigo_normalizado,
    nome_exibicao, categoria, eh_proposicao_parlamentar, contabilizar_producao_vereador, justificativa_classificacao
)
VALUES
    ('inhumas-go', 1, 'Moção de Aplausos', 'MOCAO_DE_APLAUSOS', 'Moção de Aplausos', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Manifestação formal de aplauso ou reconhecimento de autoria parlamentar.'),
    ('inhumas-go', 2, 'Projeto de Lei do Legislativo', 'PROJETO_LEI_LEGISLATIVO', 'Projeto de Lei do Legislativo', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Proposição de lei de iniciativa de vereador ou Mesa Diretora.'),
    ('inhumas-go', 3, 'Projeto de Decreto Legislativo', 'PROJETO_DECRETO_LEGISLATIVO', 'Projeto de Decreto Legislativo', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Matéria de competência exclusiva do Legislativo (inclui títulos e honrarias).'),
    ('inhumas-go', 4, 'Projeto de Lei', 'PROJETO_DE_LEI', 'Projeto de Lei', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Proposição legislativa substantiva submetida ao Plenário.'),
    ('inhumas-go', 5, 'Requerimento', 'REQUERIMENTO', 'Requerimento', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Pedido formal de providências ou informações feito por vereador.'),
    ('inhumas-go', 6, 'Indicação', 'INDICACAO', 'Indicação', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Sugestão de obra ou serviço público encaminhada ao Executivo por vereador.'),
    ('inhumas-go', 7, 'Moção', 'MOCAO', 'Moção', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Manifestação formal de aplauso, pesar, apoio ou apelo de autoria parlamentar.'),
    ('inhumas-go', 8, 'Projeto de Decreto Legislativo', 'PROJETO_DECRETO_LEGISLATIVO', 'Projeto de Decreto Legislativo', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Matéria de competência exclusiva do Legislativo (tipo_id 8 verificado no Lote 1).'),
    ('inhumas-go', 10, 'Projeto de Lei Complementar', 'PROJETO_LEI_COMPLEMENTAR', 'Projeto de Lei Complementar', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Proposição legislativa de lei complementar submetida ao Plenário (tipo_id 10 verificado no Lote 2).'),
    ('inhumas-go', 12, 'Projeto de Resolução', 'PROJETO_RESOLUCAO', 'Projeto de Resolução', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Matéria destinada a regular assuntos de economia interna da Câmara (tipo_id 12 verificado no Lote 1).'),
    ('inhumas-go', 14, 'Veto', 'VETO', 'Veto', 'ATO_EXECUTIVO_SUBMETIDO', FALSE, FALSE, 'Excluído da contagem de produção parlamentar conforme ADR-005 (Decisão 4): ato do Executivo submetido à deliberação (tipo_id 14 verificado no Lote 2).'),
    ('inhumas-go', 112, 'Emenda', 'EMENDA', 'Emenda', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Proposta acessória parlamentar para alterar texto de projeto em tramitação (tipo_id 112 verificado no Lote 1).'),
    ('inhumas-go', 113, 'PROJETO DE LEI DO LEGISLATIVO', 'PROJETO_LEI_LEGISLATIVO', 'Projeto de Lei do Legislativo', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Projeto de lei de iniciativa parlamentar (tipo_id 113 verificado no Lote 1).'),
    ('inhumas-go', 144, 'ATA DA SESSÃO', 'ATA_DA_SESSAO', 'Ata da Sessão', 'ATO_ADMINISTRATIVO_SESSAO', FALSE, FALSE, 'Excluída da contagem de produção parlamentar conforme ADR-005 (Decisão 4): registro administrativo oficial da sessão ordinária.'),
    ('inhumas-go', 145, 'ATA DA SESSAO EXTRAORDINARIA', 'ATA_DA_SESSAO_EXTRAORDINARIA', 'Ata da Sessão Extraordinária', 'ATO_ADMINISTRATIVO_SESSAO', FALSE, FALSE, 'Excluída da contagem de produção parlamentar conforme ADR-005 (Decisão 4): registro administrativo oficial de sessão extraordinária.'),
    ('inhumas-go', 210, 'Veto ao Autógrafo de Lei', 'VETO_AO_AUTOGRAFO_DE_LEI', 'Veto ao Autógrafo de Lei', 'ATO_EXECUTIVO_SUBMETIDO', FALSE, FALSE, 'Excluído da contagem de produção parlamentar conforme ADR-005 (Decisão 4): ato do Executivo submetido à deliberação do Plenário.'),
    ('inhumas-go', 211, 'Julgamento de Contas', 'JULGAMENTO_DE_CONTAS', 'Julgamento de Contas', 'JULGAMENTO_EXTERNO', FALSE, FALSE, 'Excluído da contagem de produção parlamentar conforme ADR-005 (Decisão 4): processo de apreciação das contas anuais do Executivo (TCM-GO).'),
    ('inhumas-go', 213, 'BALANÇO GERAL', 'BALANCO_GERAL', 'Balanço Geral', 'PRESTACAO_DE_CONTAS', FALSE, FALSE, 'Excluído da contagem de produção parlamentar conforme ADR-005 (Decisão 4): prestação de contas / balanço contábil da Prefeitura Municipal.'),
    ('inhumas-go', 214, 'Moção de Apoio', 'MOCAO_DE_APOIO', 'Moção de Apoio', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Manifestação formal de apoio parlamentar (tipo_id 214 verificado no Lote 2).'),
    ('inhumas-go', 243, 'PROJETO DE LEI COMPLEMENTAR DO LEGISLATIVO', 'PROJETO_LEI_COMPLEMENTAR_LEGISLATIVO', 'Projeto de Lei Complementar do Legislativo', 'PROPOSICAO_PARLAMENTAR', TRUE, TRUE, 'Projeto de lei complementar de iniciativa parlamentar (tipo_id 243 verificado no Lote 2).'),
    ('inhumas-go', 375, 'MENSAGEM DO PREFEITO', 'MENSAGEM_DO_PREFEITO', 'Mensagem do Prefeito', 'EXPEDIENTE_EXECUTIVO', FALSE, FALSE, 'Excluída da contagem de produção parlamentar conforme ADR-005 (Decisão 4): expediente/mensagem modificativa oriunda do Poder Executivo.')
ON CONFLICT (municipio_id, tipo_id_origem) DO NOTHING;

INSERT INTO lacuna_historica (
    lacuna_id, municipio_id, fonte_id, entidade_afetada,
    data_inicio_lacuna, data_fim_lacuna, motivo_oficial, evidencia_url, pedido_lai_previsto
)
VALUES
    (
        'inhumas-go-sigep-financeiro-2017-2025',
        'inhumas-go',
        'transparencia_nucleogov',
        'receita_duodecimo, despesa, folha_pagamento',
        '2017-01-01',
        '2025-12-31',
        'Migração gradual do sistema antigo (SIGEP) para o novo sistema (CENTI/NúcleoGov) comunicada oficialmente em 02/09/2026. Dados ausentes não devem ser estimados nem convertidos em zero (ADR-005).',
        'https://inhumas.go.leg.br/comunicado-migracao/',
        TRUE
    ),
    (
        'inhumas-go-legislacao-1991-2004',
        'inhumas-go',
        'legislacao_nucleogov',
        'norma',
        '1991-01-01',
        '2004-12-31',
        'Ausência de leis promulgadas entre 1991 e 2004 na consulta pública atual da NúcleoGov (salto da Lei 2.032/1990 para a Lei 2.765/2005).',
        'https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis',
        TRUE
    )
ON CONFLICT (lacuna_id) DO NOTHING;

COMMIT;
