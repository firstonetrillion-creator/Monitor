# Plano — Fase 5: Aprofundamento (Busca Avançada, Mapa por Bairros, Legislação, Comparativo GO e API Pública)

> **Status:** aprovado pelo responsável e implementado em 24/11/2026 (ver `docs/decisoes/ADR-008-aprofundamento-busca-bairros-legislacao-comparativo.md` e `docs/fase-5/relatorio-fase-5.md`).  
> **Base:** `docs/01-produto.md`, `docs/02-arquitetura.md`, `docs/04-roadmap.md`, `docs/05-etica-legal-editorial.md`, `docs/fontes/legislacao.md`, `docs/decisoes/ADR-004-estrategia-legislacao.md`, skills `postgres-patterns`, `database-migrations`, `api-design`, `scraper-resiliente`, `normalizacao-e-entidades`, `texto-cidadao` e `frontend-cidadao`.

---

## 1. Diagnóstico Técnico Verificado (19/11/2026)

Antes de planejar, verificamos os dados reais e as capacidades do ambiente local:

1. **PostgreSQL 16 portátil (`pgserver` no Windows):**
   - Não empacota as extensões contrib `pg_trgm`/`unaccent`, porém suporta nativamente **Full-Text Search em português (`to_tsvector('portuguese', ...)`, `websearch_to_tsquery('portuguese', ...)`, `ts_rank`, `ts_headline`, índices GIN)** e função SQL `IMMUTABLE` de remoção de acentos via `translate(...)` — funcionando 100% tanto localmente quanto em produção.
2. **Bairros reais nas proposições de Inhumas (`data/pgdata`):**
   - Das `1.174` proposições parlamentares já persistidas (`2025–2026`), **`269` citam bairros, setores, vilas, residenciais ou parques diretamente na ementa** (destaque para `Centro / Setor Central`, `Parque São Jorge`, `Setor Vale das Goiabeiras`, `Vila América`, `Vila 31`, `Setor Teodoro Alves`, `Setor Alegrino Lélis`, `Setor Saleiro`, `Residencial Monte Alegre`, `Setor Paraíso`, `Bairro Anhanguera`, `Setor Amélio Alves`, `Vila Santa Terezinha`, `Jardim Raio`, `Setor Pedrinhas`, `Vila Ana Nery`, `Vila Lucimar`, `Setor Nova Morada`, `Parque Santa Rita`, `Jardim Suíço`, `Vila Marise`, `Vila Mutirão`, `Vila Operária`, `Residencial Santa Bárbara` etc.).
   - Também identificamos falsos positivos óbvios (`Parque Infantil`, `Setor Competente`), o que exige um **dicionário canônico curado de bairros/aliases por `municipio_id`** com lista explícita de exclusão.
3. **Legislação Municipal (`acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis`):**
   - Já reconhecida em `docs/fontes/legislacao.md` e `ADR-004`: **406 leis ativas** (`1990–2026`) via `POST /api` (com Cloudflare WAF exigindo sessão legítima Playwright/XHR, `Crawl-Delay >= 5,0s`, ~9 páginas de 50 itens).
   - **Tesseract OCR não está instalado no PATH desta máquina Windows** hoje. Por isso, o coletor entrega **100% dos metadados + busca nas 406 leis imediatamente** e implementa o **pipeline híbrido `pdfplumber` + Tesseract OCR (`lang='por'`)** com cache por SHA-256 pronto para rodar em lote sobre os PDFs escaneados assim que `tesseract.exe` estiver disponível (ou mediante instalação open-source via `winget install UB-Mannheim.TesseractOCR`).
4. **Comparativo oficial via SICONFI / Tesouro Nacional (validado em 19/11/2026):**
   - API aberta e gratuita `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca` (`DCA-Anexo I-E`, Função `01 - Legislativa`) e `/entes` respondeu `HTTP 200 OK` sem CAPTCHA e sem WAF.
   - Já possui **DCA 2025 e DCA 2024 completos** para **Inhumas (`5210000` — R$ 9.739.153,62 pagos na Função Legislativa em 2025)** e para **7 municípios goianos de porte semelhante (`44k–67k` hab.)**: **Morrinhos (`5213806`)**, **Quirinópolis (`5218508`)**, **Itaberaí (`5210406`)**, **Jaraguá (`5211800`)**, **Porangatu (`5218003`)**, **Uruaçu (`5221601`)** e **Cristalina (`5206206`)**.

---

## 2. Os 5 Pilares da Fase 5

### Pilar 1 — Migração SQL `0003` + Busca Avançada Unificada (`/busca` e `GET /api/v1/busca`)
- **Banco (`db/migrations/0003_fase5_aprofundamento.sql`):**
  - Função `IMMUTABLE` `normalizar_texto_busca(TEXT)` (lowercase + remoção de acentos sem dependência de extensão externa);
  - Índices GIN de Full-Text Search (`portuguese`) em `proposicao`, `sessao`, `vereador`, `despesa_empenho`, `fornecedor` e na nova tabela `norma`;
  - Novas tabelas normalizadas e multi-município:
    - `norma` (leis/decretos/resoluções municipais, URL canônica, proveniência SHA-256 e metadados de OCR conforme `ADR-004`);
    - `bairro` e `proposicao_bairro` (dicionário canônico de bairros/aliases por `municipio_id`, tema normalizado e método de extração determinístico);
    - `comparativo_legislativo_siconfi` (dados oficiais da Função `01 - Legislativa` do SICONFI/Tesouro Nacional para Inhumas e municípios pares de Goiás, anos `2024` e `2025`, com proveniência completa).
- **API (`GET /api/v1/busca`):**
  - Busca unificada em linguagem natural (`q`), com filtros por `categoria` (`todos`, `proposicoes`, `leis`, `vereadores`, `sessoes`, `despesas`), `ano`, `bairro_id` e paginação;
  - Ordenação por relevância (`ts_rank`), destaque de trecho encontrado (`ts_headline`) e link direto para a página interna + documento oficial.
- **UI (`/busca` + barra de busca rápida na Home `/`):**
  - Campo único em português claro (*"Busque por assunto, bairro, vereador, fornecedor ou número de lei — ex.: asfalto, UBSF, Parque São Jorge, 3577"*), abas por tipo, contagem por categoria e zero CPF.

### Pilar 2 — Mapa e Painel de Indicações e Requerimentos por Bairro (`/bairros` e `GET /api/v1/bairros`)
- **Motor determinístico (`apps/coleta/src/cerrado_aberto_coleta/bairros.py`):**
  - Dicionário canônico curado de bairros, setores, vilas, residenciais e distritos de Inhumas (unificando variantes como `Setor Central` → `Centro`, `Vila 31` → `Vila 31 de Março`, `Setor Santa Bárbara` / `Residencial Santa Bárbara` → `Residencial Santa Bárbara`), coordenadas geográficas aproximadas do centroide do bairro (para visualização cartográfica local) e classificação temática determinística (`Infraestrutura e Asfalto`, `Trânsito e Sinalização`, `Saúde`, `Educação`, `Iluminação e Energia`, `Água e Saneamento`, `Esporte, Cultura e Lazer`, `Outros`).
  - Bloqueio explícito de falsos positivos (`Parque Infantil`, `Setor Competente`, `Setor Público`).
  - Transparência metodológica: exibe claramente quantas proposições mencionam bairro na ementa (`~269`) vs. quantas não especificam localidade (nunca inferindo bairro que não está no texto!).
- **API (`GET /api/v1/bairros` e `GET /api/v1/bairros/{slug}`):**
  - Totais por bairro, distribuição por tema, vereadores que mais apresentaram pedidos naquele bairro (em ordem neutra) e lista paginada de proposições vinculadas.
- **UI (`/bairros`):**
  - **Mapa interativo vetorial (SVG/Observable Plot 100% local — sem API paga nem rastreamento externo)** posicionando os bairros de Inhumas com bolhas proporcionais ao volume de pedidos + filtro por tema/ano/vereador + lista de proposições do bairro selecionado + alternativa completa em tabela HTML acessível WCAG e botão **Baixar CSV**.

### Pilar 3 — Legislação Municipal Pesquisável (`/legislacao`, `/legislacao/[id]` e `GET /api/v1/legislacao`)
- **Coletor resiliente (`apps/coleta/src/cerrado_aberto_coleta/legislacao/`):**
  - Coleta de metadados das **406 leis ativas** (`POST https://acessoainformacao.inhumas.go.leg.br/api`, ~9 requisições paginadas com `Crawl-Delay >= 5,0s`, bruto imutável SHA-256 em `data/raw/inhumas-go/legislacao/`, URL canônica `https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id={id}`, nunca salvando URL temporária S3 como link público);
  - Pipeline híbrido `pdfplumber` + Tesseract OCR (`lang='por'`) para anexos PDF (armazenando binário original, `extraido_por_ocr`, `ocr_confianca_media` e `requer_revisao_humana` conforme `ADR-004`), com execução opcional em lote de PDFs recentes (`2025–2026`).
- **API (`GET /api/v1/legislacao` e `GET /api/v1/legislacao/{id}`):**
  - Busca FTS em português em número, ementa e texto extraído (quando disponível), filtros por `ano`, `categoria` (Lei Ordinária, Lei Orgânica, LDO, LOA, Código Tributário etc.), resumo cidadão automático (`ResumoCidadaoBox`) e aviso claro da cobertura (`406` leis cadastradas no portal desde 1990).
- **UI (`/legislacao` e `/legislacao/[id]`):**
  - Catálogo pesquisável com filtros por categoria/ano, selo de método de extração (*"Metadados oficiais"* / *"Texto integral extraído por OCR — confira o PDF oficial"*), exportação CSV e link direto para a página oficial da lei.

### Pilar 4 — Comparativo com Municípios Semelhantes de Goiás (`/comparativo` e `GET /api/v1/comparativo`)
- **Coletor oficial SICONFI (`apps/coleta/src/cerrado_aberto_coleta/siconfi/`):**
  - Coleta 100% oficial via `GET https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes` + `/dca?no_anexo=DCA-Anexo+I-E` para **Inhumas (`5210000`)** e **7 municípios pares de Goiás (`44k–67k` hab.)**: `Morrinhos`, `Quirinópolis`, `Itaberaí`, `Jaraguá`, `Porangatu`, `Uruaçu` e `Cristalina`, nos exercícios fechados **`2024` e `2025`** (~17 requisições no total, `Crawl-Delay >= 1,0s`, bruto imutável SHA-256).
  - Calcula despesa paga total da Função `01 - Legislativa`, valor per capita/ano, valor per capita/mês e variação 2024→2025.
- **Regras éticas inegociáveis (`docs/05-etica-legal-editorial.md`):**
  - **Proibido ranking sensacionalista** (*"mais cara"*, *"gastona"*, *"pior"*). Ordenação neutra (alfabética ou por porte populacional), gráfico horizontal Observable Plot com destaque visual discreto para Inhumas + tabela comparativa + nota metodológica explicando que o SICONFI agrega a **Função `01 - Legislativa`** declarada ao Tesouro Nacional e que diferenças podem decorrer do número de vereadores, sede própria, previdência ou obras pontuais.

### Pilar 5 — Portal da API Pública e Dados Abertos (`/dados-abertos` + Rate Limiting na API)
- **Backend (`apps/api`):**
  - Middleware leve de **rate limiting em memória por IP** (`120 req/min` configurável por variável de ambiente, retornando `429 Too Many Requests` com `Retry-After` e cabeçalhos `X-RateLimit-*`, conforme `common-security.md` e `api-design`);
  - Metadados OpenAPI enriquecidos (descrição de licença aberta, termos de uso neutro, política LGPD e exemplos de resposta).
- **Frontend (`/dados-abertos`):**
  - Guia prático para jornalistas, desenvolvedores e pesquisadores: lista interativa de todos os endpoints `GET /api/v1/*`, blocos copiáveis (`BotaoCopiar`) com exemplos `curl` e Python, atalhos para download direto em CSV/JSON de cada conjunto de dados, link para OpenAPI/Swagger e regra de citação das fontes oficiais.

---

## 3. Decisões para sua Aprovação (D1–D5)

| # | Decisão | Recomendação |
|---|---|---|
| **D1** | **Migração SQL `0003_fase5_aprofundamento.sql`:** criar tabelas `norma`, `bairro`, `proposicao_bairro`, `comparativo_legislativo_siconfi` e índices GIN Full-Text Search em português (usando função `IMMUTABLE` compatível com `pgserver`). | **Aprovar** — 100% aditiva e compatível com todas as migrações `0001`/`0002` existentes. |
| **D2** | **Coleta de Legislação (`acessoainformacao.inhumas.go.leg.br`):** coletar em lote educado os metadados das **406 leis** (~9 requisições paginadas via sessão Playwright/XHR por causa do Cloudflare WAF, `Crawl-Delay >= 5,0s`). | **Aprovar coleta dos metadados das 406 leis**; deixar o download/OCR de PDFs escaneados (`pdfplumber` + Tesseract `por`) implementado, testado com fixture e pronto para rodar em lote opcional após instalação do Tesseract local. |
| **D3** | **Coleta oficial SICONFI (Tesouro Nacional):** buscar os dados abertos da **Função `01 - Legislativa`** (`DCA 2024 e 2025`) para Inhumas e os 7 municípios goianos de porte semelhante (~17 requisições HTTP abertas, zero custo). | **Aprovar** — garante comparativo intermunicipal 100% oficial, auditável e sem suposições. |
| **D4** | **Mapa de Indicações por Bairro (`/bairros`):** usar mapa cartográfico vetorial local (Observable Plot / SVG com coordenadas aproximadas dos bairros de Inhumas + tabela WCAG completa + filtro por tema/vereador), sem Google Maps pago nem tiles externos. | **Aprovar** — custo zero, zero rastreamento de terceiros, 100% acessível e testável offline no Playwright. |
| **D5** | **Escopo de entrega da Fase 5:** executar os 5 pilares em 4 etapas ordenadas (Banco/Coletores → API/Busca/Rate Limit → 5 Telas Web → E2E Playwright/Axe + ADR-008 + Relatório). | **Aprovar execução completa em 4 etapas** com validação automatizada em cada camada. |

---

## 4. Etapas de Execução (após sua aprovação)

1. **Etapa 1 — Migração `0003` + Coletores (`apps/coleta`):** criar `db/migrations/0003_fase5_aprofundamento.sql`, extrator de bairros de Inhumas (`bairros.py`), coletor oficial SICONFI (`siconfi/`), coletor de Legislação + pipeline PDF/OCR (`legislacao/`), rodar as coletas autorizadas (`D2` e `D3`) e validar com `pytest` + `ruff`.
2. **Etapa 2 — API v1 Aprofundada (`apps/api`):** criar endpoints `GET /api/v1/busca`, `GET /api/v1/bairros`, `GET /api/v1/bairros/{slug}`, `GET /api/v1/legislacao`, `GET /api/v1/legislacao/{id}` e `GET /api/v1/comparativo`, adicionar rate limiting configurável e testar tudo com `pytest` (incluindo LGPD e neutralidade).
3. **Etapa 3 — 5 Novas Telas Cidadãs (`apps/web`):** construir `/busca`, `/bairros`, `/legislacao`, `/legislacao/[id]`, `/comparativo` e `/dados-abertos`, integrar na navegação (`SiteHeader`, `SiteFooter` e busca rápida na Home `/`), seguindo `frontend-cidadao`, `texto-cidadao` e `modern-web-guidance`.
4. **Etapa 4 — Qualidade, Acessibilidade, Capturas e `ADR-008`:** expandir `apps/web/tests/mvp.spec.ts` cobrindo todas as novas rotas (desktop + mobile + `axe-core` WCAG 2.1 A/AA + zero CPF + zero vocabulário proibido), salvar capturas em `docs/fase-5/capturas/`, registrar `ADR-008`, atualizar `docs/04-roadmap.md`, `AGENTS.md` e gerar `docs/fase-5/relatorio-fase-5.md` + `walkthrough.md`.

---

## 5. Riscos e Mitigações

- **Cloudflare WAF em `acessoainformacao.inhumas.go.leg.br`:** já mapeado na Fase 2 (`docs/fontes/transparencia.md`); será respeitado usando sessão de navegador Playwright com `Crawl-Delay >= 5,0s` e sem paralelismo. Se houver bloqueio temporário de borda, o coletor falha de forma limpa preservando fixtures e sem nunca tentar burlar CAPTCHA.
- **Ausência de `tesseract.exe` no Windows local:** o pipeline de OCR será estruturado e testado com fallback gracioso (`pdfplumber` nativo + marcação `PENDENTE_OCR` quando Tesseract não estiver instalado), sem impedir a pesquisa imediata nos metadados das 406 leis.
- **Ambiguidade de nomes de bairros em ementas:** dicionário explícito de aliases + exclusão de falsos positivos + contagem transparente de proposições sem menção de bairro na ementa.
- **Interpretação indevida no comparativo intermunicipal:** texto editorial neutro, ordenação não sensacionalista e nota metodológica sobre diferenças entre Câmaras (número de cadeiras, sede, regime previdenciário e população IBGE/SICONFI).
