# ADR-008 — Aprofundamento: Busca Avançada FTS, Mapa por Bairros, Legislação, Comparativo SICONFI e API Pública (Fase 5)

- **Status:** Aceito (aprovado pelo responsável em 24/11/2026)
- **Data:** 2026-11-24
- **Contexto:** Execução da Fase 5 (*Aprofundamento*) do **Cerrado Aberto**, ampliando o sistema para busca unificada em linguagem natural, mapeamento territorial por bairros de Inhumas, acervo pesquisável de legislação municipal, comparativo intermunicipal oficial com municípios pares de Goiás e portal da API pública para jornalistas e pesquisadores.

---

## Decisões Aprovadas (D1–D5)

### D1 — Migração SQL `0003` e Full-Text Search Portátil sem Extensões Externas
- **Contexto técnico:** O binário portátil `pgserver` no Windows não inclui módulos contrib (`pg_trgm`/`unaccent`), porém o núcleo do PostgreSQL 16 oferece Full-Text Search nativo em português (`portuguese`, `to_tsvector`, `websearch_to_tsquery`, `ts_rank`, índices `GIN`).
- **Decisão:** Criar [0003_fase5_aprofundamento.sql](../../db/migrations/0003_fase5_aprofundamento.sql) de forma 100% aditiva e idempotente, definindo a função `IMMUTABLE` `normalizar_texto_busca(TEXT)` (via `TRANSLATE` + `LOWER`), 5 índices GIN FTS (`proposicao`, `norma`, `sessao`, `vereador`, `despesa_empenho`) e as tabelas multi-município `norma`, `bairro`, `proposicao_bairro` e `comparativo_legislativo_siconfi`, além do cadastro da fonte oficial `siconfi_stn`.

### D2 — Legislação Municipal Pesquisável (407 Leis) e Pipeline Híbrido `pdfplumber` + Tesseract OCR
- **Decisão:** Coletar os metadados das **407 leis municipais** cadastradas desde 1990 em `acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis` via sessão legítima Playwright/XHR (`POST /api`, ação oficial `leis/buscaAvancada`, `9` páginas de `50` registros, `Crawl-Delay = 5,2s`, sem tentar contornar CAPTCHA), registrando sempre a **URL canônica permanente** (`/legislacao/lei/id={id}`) e nunca a URL temporária do Amazon S3 (`X-Amz-Expires=2400`).
- **OCR:** Implementar o pipeline híbrido `pdfplumber` + Tesseract OCR (`lang='por'`) em `apps/coleta/src/cerrado_aberto_coleta/legislacao/ocr.py` com fallback seguro (`status_ocr = 'PENDENTE_OCR'` + `requer_revisao_humana = TRUE`) quando o binário local `tesseract` não estiver instalado, garantindo busca imediata por número, ano, categoria e ementa em todo o acervo sem custo externo.

### D3 — Comparativo Intermunicipal Oficial via SICONFI / Secretaria do Tesouro Nacional
- **Decisão:** Integrar a API pública oficial do Tesouro Nacional (`https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes` e `/dca`, anexo `DCA-Anexo I-E`, **Função `01 - Legislativa`** — sem somar subfunções como `01.031`) nos exercícios consolidados **`2024` e `2025`** para **Inhumas (`5210000`)** e **7 municípios goianos de porte semelhante (`44k–67k` hab.)**: `Morrinhos`, `Quirinópolis`, `Itaberaí`, `Jaraguá`, `Porangatu`, `Uruaçu` e `Cristalina`.
- **Ética editorial (`docs/05-etica-legal-editorial.md`):** Ordenação neutra por população (nunca ranking sensacionalista), exibindo média, mediana e variação interanual com nota metodológica transparente sobre diferenças estruturais entre Câmaras.

### D4 — Mapa de Indicações por Bairro 100% Local e Auditável
- **Decisão:** Construir um catálogo canônico curado por `municipio_id` (`52` bairros, setores, vilas, residenciais e distritos reais de Inhumas em `bairros.py`) com aliases normalizados, classificação temática determinística e bloqueio explícito de falsos positivos (ex.: `Parque Infantil`, `Centro Municipal de Educação`).
- **Visualização:** Renderizar mapa cartográfico vetorial SVG local (`MapaBairrosSvg.tsx`) sem Google Maps pago nem rastreamento externo, sempre acompanhado de tabela HTML acessível WCAG, exportação CSV e transparência de cobertura (`231` proposições com bairro citado na ementa vs. `943` sem localidade na ementa).

### D5 — Portal da API Pública (`/dados-abertos`) e Rate Limiting Configurável
- **Decisão:** Adicionar middleware de rate limiting em janela deslizante por IP (`apps/api/src/cerrado_aberto_api/rate_limit.py`, configurável via `CERRADO_RATE_LIMIT_RPM`, padrão `240` req/min, cabeçalhos `X-RateLimit-Limit` / `X-RateLimit-Remaining` e resposta `429` com `Retry-After`) e publicar a página `/dados-abertos` com exemplos copiáveis (`cURL`, `Python`, `JavaScript`) e catálogo clicável de todos os endpoints somente leitura `GET /api/v1/*`.
