-- =============================================================================
-- Cerrado Aberto — Plataforma Cidadã Independente de Transparência Legislativa
-- Migração 0003: Fase 5 — Busca Avançada (FTS), Bairros, Legislação e SICONFI
-- Banco: PostgreSQL 16+ (100% compatível com pgserver sem extensões contrib)
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Função IMMUTABLE de normalização textual PT-BR (sem dependência de unaccent)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION normalizar_texto_busca(texto TEXT)
RETURNS TEXT
LANGUAGE SQL
IMMUTABLE
STRICT
PARALLEL SAFE
AS $$
    SELECT LOWER(
        TRANSLATE(
            texto,
            'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑÝáàâãäéèêëíìîïóòôõöúùûüçñý',
            'AAAAAEEEEIIIIOOOOOUUUUCNYaaaaaeeeeiiiiooooouuuucny'
        )
    );
$$;

-- -----------------------------------------------------------------------------
-- 2. Fonte oficial adicional: SICONFI / Secretaria do Tesouro Nacional
-- -----------------------------------------------------------------------------

INSERT INTO fonte (fonte_id, municipio_id, nome, url_base, tipo_acesso, crawl_delay_segundos, ativa, observacoes)
SELECT
    'siconfi_stn',
    'inhumas-go',
    'SICONFI — Secretaria do Tesouro Nacional (DCA Anexo I-E)',
    'https://apidatalake.tesouro.gov.br/ords/siconfi/tt',
    'REST_JSON',
    1.0,
    TRUE,
    'API pública oficial do Tesouro Nacional para comparativo da Função 01 - Legislativa entre municípios de Goiás.'
WHERE EXISTS (SELECT 1 FROM municipio WHERE municipio_id = 'inhumas-go')
ON CONFLICT (fonte_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3. Tabela de Legislação Municipal (`norma` — ADR-004)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS norma (
    norma_id VARCHAR(80) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    tabela_origem VARCHAR(32) NOT NULL DEFAULT 'leis', -- 'leis', 'decretos', 'resolucoes', 'portarias'
    id_origem INTEGER NOT NULL,
    numero VARCHAR(40) NOT NULL,
    ano INTEGER,
    tipo_norma VARCHAR(80) NOT NULL, -- 'Lei Ordinária', 'Lei Orgânica', 'Lei Complementar', etc.
    categoria_id_origem VARCHAR(32),
    categoria_descricao VARCHAR(120) NOT NULL,
    data_publicacao DATE,
    data_publicacao_portal DATE,
    ementa TEXT NOT NULL,
    total_anexos INTEGER NOT NULL DEFAULT 0,
    texto_extraido TEXT,
    status_ocr VARCHAR(32) NOT NULL DEFAULT 'METADADOS_APENAS',
        -- 'METADADOS_APENAS', 'TEXTO_NATIVO_PDF', 'OCR_CONCLUIDO', 'PENDENTE_OCR'
    extraido_por_ocr BOOLEAN NOT NULL DEFAULT FALSE,
    ocr_engine_versao VARCHAR(64),
    ocr_confianca_media NUMERIC(5,2),
    requer_revisao_humana BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_revisao_humana TEXT,
    documento_bruto_id UUID REFERENCES documento_bruto(documento_id),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL, -- URL canônica /legislacao/lei/id={id}, nunca URL temporária S3
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, tabela_origem, id_origem)
);

CREATE INDEX IF NOT EXISTS idx_norma_municipio_ano
    ON norma (municipio_id, ano DESC, data_publicacao DESC);

CREATE INDEX IF NOT EXISTS idx_norma_categoria
    ON norma (municipio_id, categoria_descricao);

CREATE INDEX IF NOT EXISTS idx_norma_numero
    ON norma (municipio_id, numero);

-- -----------------------------------------------------------------------------
-- 4. Catálogo Canônico de Bairros/Localidades e Vínculo com Proposições
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS bairro (
    bairro_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    slug VARCHAR(96) NOT NULL,
    nome_oficial VARCHAR(160) NOT NULL,
    regiao VARCHAR(64) NOT NULL, -- 'Central', 'Norte', 'Sul', 'Leste', 'Oeste', 'Distrito / Rural'
    tipo_localidade VARCHAR(40) NOT NULL DEFAULT 'BAIRRO', -- 'BAIRRO', 'DISTRITO', 'ZONA_RURAL'
    latitude_aprox NUMERIC(9,6),
    longitude_aprox NUMERIC(9,6),
    aliases_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (municipio_id, slug)
);

CREATE TABLE IF NOT EXISTS proposicao_bairro (
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id),
    proposicao_id VARCHAR(80) NOT NULL REFERENCES proposicao(proposicao_id) ON DELETE CASCADE,
    bairro_id VARCHAR(96) NOT NULL REFERENCES bairro(bairro_id) ON DELETE CASCADE,
    tema_principal VARCHAR(80) NOT NULL,
    trecho_evidencia VARCHAR(240) NOT NULL,
    metodo_extracao VARCHAR(48) NOT NULL DEFAULT 'REGEX_DICIONARIO_CURADO',
    versao_extrator VARCHAR(48) NOT NULL,
    extraido_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (proposicao_id, bairro_id)
);

CREATE INDEX IF NOT EXISTS idx_proposicao_bairro_bairro
    ON proposicao_bairro (municipio_id, bairro_id, tema_principal);

CREATE INDEX IF NOT EXISTS idx_proposicao_bairro_tema
    ON proposicao_bairro (municipio_id, tema_principal);

-- -----------------------------------------------------------------------------
-- 5. Comparativo Intermunicipal Oficial — SICONFI / Tesouro Nacional
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS comparativo_legislativo_siconfi (
    comparativo_id VARCHAR(96) PRIMARY KEY,
    municipio_id VARCHAR(64) NOT NULL REFERENCES municipio(municipio_id), -- município foco (ex.: 'inhumas-go')
    codigo_ibge CHAR(7) NOT NULL,
    ente_nome VARCHAR(160) NOT NULL,
    uf CHAR(2) NOT NULL,
    eh_municipio_foco BOOLEAN NOT NULL DEFAULT FALSE,
    ano INTEGER NOT NULL,
    anexo_siconfi VARCHAR(48) NOT NULL DEFAULT 'DCA-Anexo I-E',
    funcao_codigo VARCHAR(16) NOT NULL DEFAULT '01',
    funcao_descricao VARCHAR(80) NOT NULL DEFAULT '01 - Legislativa',
    populacao_siconfi INTEGER,
    despesa_empenhada NUMERIC(16,2),
    despesa_liquidada NUMERIC(16,2),
    despesa_paga NUMERIC(16,2),
    despesa_paga_per_capita_ano NUMERIC(12,2),
    despesa_paga_per_capita_mes NUMERIC(12,2),
    documento_bruto_id UUID REFERENCES documento_bruto(documento_id),
    fonte_id VARCHAR(64) NOT NULL REFERENCES fonte(fonte_id),
    fonte_url TEXT NOT NULL,
    coletado_em TIMESTAMPTZ NOT NULL,
    hash_conteudo CHAR(64) NOT NULL,
    versao_coletor VARCHAR(64) NOT NULL,
    UNIQUE (municipio_id, codigo_ibge, ano)
);

CREATE INDEX IF NOT EXISTS idx_comparativo_siconfi_municipio_ano
    ON comparativo_legislativo_siconfi (municipio_id, ano DESC, populacao_siconfi DESC);

-- -----------------------------------------------------------------------------
-- 6. Índices GIN de Full-Text Search (Português + Normalizado sem Acentos)
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_fts_proposicao_gin
    ON proposicao USING GIN (
        to_tsvector(
            'portuguese',
            normalizar_texto_busca(
                COALESCE(nome_materia, '') || ' ' ||
                COALESCE(tipo_descricao_origem, '') || ' ' ||
                COALESCE(ementa, '')
            )
        )
    );

CREATE INDEX IF NOT EXISTS idx_fts_norma_gin
    ON norma USING GIN (
        to_tsvector(
            'portuguese',
            normalizar_texto_busca(
                COALESCE(numero, '') || ' ' ||
                COALESCE(categoria_descricao, '') || ' ' ||
                COALESCE(ementa, '') || ' ' ||
                COALESCE(texto_extraido, '')
            )
        )
    );

CREATE INDEX IF NOT EXISTS idx_fts_sessao_gin
    ON sessao USING GIN (
        to_tsvector(
            'portuguese',
            normalizar_texto_busca(
                COALESCE(nome_sessao, '') || ' ' ||
                COALESCE(tipo_descricao, '')
            )
        )
    );

CREATE INDEX IF NOT EXISTS idx_fts_vereador_gin
    ON vereador USING GIN (
        to_tsvector(
            'portuguese',
            normalizar_texto_busca(
                COALESCE(nome_exibicao, '') || ' ' ||
                COALESCE(nome_civil, '') || ' ' ||
                COALESCE(nome_politico, '')
            )
        )
    );

CREATE INDEX IF NOT EXISTS idx_fts_despesa_gin
    ON despesa_empenho USING GIN (
        to_tsvector(
            'portuguese',
            normalizar_texto_busca(
                COALESCE(numero_empenho, '') || ' ' ||
                COALESCE(favorecido_nome, '') || ' ' ||
                COALESCE(elemento_despesa, '') || ' ' ||
                COALESCE(historico, '')
            )
        )
    );

COMMIT;
