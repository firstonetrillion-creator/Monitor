# Relatório da Fase 5 — Aprofundamento (Busca Avançada, Mapa por Bairros, Legislação, Comparativo SICONFI e API Pública)

> **Projeto:** Cerrado Aberto (`cerradoaberto.org.br`) — Plataforma Cidadã Independente de Transparência Legislativa  
> **Escopo:** Fase 5 (*Aprofundamento*) implementada e validada ponta a ponta em homologação (`db/migrations/0003` + `apps/coleta` + `apps/api` + `apps/web`)  
> **Data:** 24/11/2026  
> **Decisões relacionadas:** [ADR-008](../decisoes/ADR-008-aprofundamento-busca-bairros-legislacao-comparativo.md) · [ADR-004](../decisoes/ADR-004-estrategia-legislacao.md) · [Plano da Fase 5](plano-aprofundamento.md)

---

## 1. Banco de Dados e Coletores (`db/migrations/0003` + `apps/coleta`)

- **Migração SQL aditiva e idempotente:** [0003_fase5_aprofundamento.sql](../../db/migrations/0003_fase5_aprofundamento.sql)
  - Função `IMMUTABLE` `normalizar_texto_busca(TEXT)` (lowercase + remoção de acentos PT-BR sem depender de extensões contrib ausentes no `pgserver` portátil);
  - 5 índices GIN de Full-Text Search `portuguese` (`idx_fts_proposicao_gin`, `idx_fts_norma_gin`, `idx_fts_sessao_gin`, `idx_fts_vereador_gin`, `idx_fts_despesa_gin`);
  - 4 novas tabelas multi-município: `norma`, `bairro`, `proposicao_bairro` e `comparativo_legislativo_siconfi`, além do cadastro da fonte oficial `siconfi_stn`.
- **Mapa de Indicações por Bairro (`bairros.py`):**
  - Catálogo curado de **52 bairros, setores, vilas, residenciais e distritos reais de Inhumas** ([bairros.py](../../apps/coleta/src/cerrado_aberto_coleta/bairros.py)) com aliases normalizados (`Setor Central` → `Centro`, `Vila 31` → `Vila 31 de Março`, `Jardim Raio do Sol` → `Jardim Raio de Sol` etc.) e bloqueio de falsos positivos (`Parque Infantil`, `Centro Municipal de Educação`).
  - **Cobertura verificada (100% transparente):** `52/52` bairros com registros; `231` proposições parlamentares com citação verificável na ementa (`291` vínculos proposição↔bairro) e `943` proposições gerais sem localidade na ementa (nunca atribuídas a bairros).
  - **Top temas:** Infraestrutura e Asfalto (`91`), Trânsito e Sinalização (`72`), Esporte, Cultura e Lazer (`29`), Água e Saneamento (`23`), Saúde (`9`), Educação (`8`), Iluminação e Energia (`6`), Segurança e Ordem Pública (`3`).
- **Legislação Municipal (`legislacao/` + `scripts/coletar-legislacao-leis.mjs`):**
  - Coleta educada concluída em `24/11/2026` via sessão legítima Playwright/XHR (`POST /api`, ação oficial `leis/buscaAvancada`, `9` páginas de `50` itens, `Crawl-Delay = 5,2s`, sem burlar CAPTCHA): **`407` leis municipais únicas** carregadas (desde a Lei Orgânica 001/1990 até a Lei Ordinária 3577/2026) com payloads brutos imutáveis em `data/raw/inhumas-go/legislacao/leis/` e **URL canônica permanente** (`/legislacao/lei/id={id}`, zero URL S3 temporária).
  - Reexecução imediata validada: `novos = 0`, `alterados = 0`, `inalterados = 407`.
  - Pipeline híbrido `pdfplumber` + Tesseract OCR (`por`) implementado e testado em [ocr.py](../../apps/coleta/src/cerrado_aberto_coleta/legislacao/ocr.py) com fallback seguro (`PENDENTE_OCR`) quando o binário local `tesseract` não estiver instalado.
- **Comparativo Oficial SICONFI / Secretaria do Tesouro Nacional (`siconfi/collector.py`):**
  - Execução oficial (`execucao_id=2029ab4e-187d-461d-aa9e-0465f5020f2b`, `17` requisições à API aberta `apidatalake.tesouro.gov.br/ords/siconfi/tt`, payloads brutos SHA-256 em `data/raw/inhumas-go/siconfi/`): **`16` registros consolidados (`2024` e `2025`)** da **Função `01 - Legislativa`** (`DCA-Anexo I-E`, sem duplicar subfunções) para **Inhumas (`5210000`)** e **7 municípios pares de Goiás**:
    - **Inhumas/GO (`2025`):** `R$ 9.739.153,62` pagos · `R$ 182,67 / hab. / ano` (`R$ 15,22 / mês`) · variação vs. 2024: `+21,8%` (população SICONFI `53.315`).
    - **Grupo de 8 cidades GO (`2025`):** Mediana `R$ 188,20 / hab. / ano` · Média `R$ 184,36 / hab. / ano` (`Cristalina`, `Inhumas`, `Quirinópolis`, `Morrinhos`, `Itaberaí`, `Porangatu`, `Jaraguá` e `Uruaçu`).

---

## 2. API Pública FastAPI v1 (`apps/api`)

- **6 novos endpoints somente leitura (`GET`)** em [fase5_router.py](../../apps/api/src/cerrado_aberto_api/fase5_router.py) + contratos em [schemas_fase5.py](../../apps/api/src/cerrado_aberto_api/schemas_fase5.py):
  - `GET /api/v1/busca` (Full-Text Search unificado em proposições, leis, vereadores, sessões e despesas)
  - `GET /api/v1/bairros` e `GET /api/v1/bairros/{slug}`
  - `GET /api/v1/legislacao` e `GET /api/v1/legislacao/{id}` (com `resumo_cidadao` automático)
  - `GET /api/v1/comparativo` (`2024` e `2025`, ordenação neutra por população)
- **Rate Limiting por IP:** [rate_limit.py](../../apps/api/src/cerrado_aberto_api/rate_limit.py) — janela deslizante configurável (`CERRADO_RATE_LIMIT_RPM`, padrão `240` req/min), cabeçalhos `X-RateLimit-Limit` / `X-RateLimit-Remaining` e resposta `429` com `Retry-After`.
- **Observabilidade (`/api/v1/health`):** ampliada para reportar contagens de `norma`, `bairro`, `proposicao_bairro` e `comparativo_legislativo_siconfi`, além da última coleta de `legislacao_nucleogov` e `siconfi_stn`.

---

## 3. Novas Telas Cidadãs (`apps/web`)

| Rota | Descrição e diferenciais de acessibilidade / neutralidade |
|---|---|
| **`/busca`** (+ barra rápida na Home `/`) | Busca unificada em linguagem natural com `<form>` nativo IME-safe, sugestões rápidas, abas em linha única rolável (`role="tablist"`, borda inferior sólida sem depender só de cor) e links diretos para o documento oficial. |
| **`/bairros`** | Mapa vetorial SVG 100% local (`MapaBairrosSvg.tsx`, sem API paga nem rastreamento externo), painel de cobertura transparente (`231` com bairro vs. `943` sem localidade), filtros por ano/tema/nome, tabela HTML completa e exportação CSV. |
| **`/legislacao` e `/legislacao/[id]`** | Catálogo pesquisável das `407` leis municipais (`1990–2026`), filtro por categoria/ano, exportação CSV, resumo automático em linguagem simples (`ResumoCidadaoBox`), transparência sobre PDF/OCR (`ADR-004`) e proveniência SHA-256. |
| **`/comparativo`** | Comparativo oficial SICONFI (`2025` / `2024`) de Inhumas × 7 municípios pares de Goiás, ordenado de forma neutra por população, gráfico horizontal Observable Plot com alternativa em tabela + CSV e nota metodológica sem juízo de valor. |
| **`/dados-abertos`** | Portal da API Pública para jornalistas e pesquisadores: exemplos copiáveis em `cURL`, `Python (httpx)` e `JavaScript (fetch)` em abas acessíveis com `BotaoCopiar` e catálogo clicável de todos os endpoints `GET /api/v1/*`. |

---

## 4. Matriz de Verificação Automatizada (Executada em 24/11/2026)

| Camada / Comando | Resultado | Cobertura verificada |
|---|---|---|
| `uv run --directory apps/coleta ruff check src tests` | **PASS (`0` erros)** | PEP 8, tipagem e imports em `apps/coleta` |
| `uv run --directory apps/coleta pytest -q` | **PASS (`26 passed` em 70,69s)** | Bairros (aliases/falsos positivos/temas), SICONFI (sem duplicar subfunção, layout quebrado), Legislação (fixtures reais, URL canônica, LGPD, OCR fallback, idempotência) + todas as suítes das Fases 1–4 |
| `uv run --directory apps/api ruff check src tests` | **PASS (`0` erros)** | FastAPI, Pydantic e segurança em `apps/api` |
| `uv run --directory apps/api pytest -q` | **PASS (`16 passed` em 22,05s)** | Busca FTS sem acento, Bairros, Legislação (407 leis, zero S3), Comparativo SICONFI neutro, Rate Limit `429`, OpenAPI completo (21 rotas) e proteção LGPD |
| `npm --prefix apps/web run lint` | **PASS (`0` erros, `0` avisos)** | ESLint + limite de linhas em `apps/web` |
| `npm --prefix apps/web run build` | **PASS (`23` rotas, TypeScript limpo)** | Build de produção Next.js 16.4.6 (Turbopack) |
| `npm --prefix apps/web run test:e2e` | **PASS (`24 passed` em 3,2m)** | `12` testes desktop (`1280×800`) + `12` testes mobile (`390×844`): **`0` violações críticas/sérias `axe-core` WCAG 2.1 A/AA**, `0` CPF completo, `0` palavras proibidas, `0` overflow horizontal mobile, downloads CSV e PNG verificados |

---

## 5. Capturas Geradas e Pendência Opcional

- **Capturas completas:** `docs/fase-5/capturas/` (desktop e mobile de todas as telas das Fases 3, 4 e 5, incluindo `14-busca-*`, `15-bairros-*`, `16-legislacao-*`, `17-legislacao-detalhe-desktop`, `18-comparativo-*`, `19-dados-abertos-*`).
- **Pendência opcional de ambiente:** caso o responsável deseje rodar **OCR em lote** nos PDFs digitalizados das leis municipais localmente no Windows, basta instalar o Tesseract open-source (`winget install UB-Mannheim.TesseractOCR` com pacote de idioma `por`) — o pipeline `apps/coleta/src/cerrado_aberto_coleta/legislacao/ocr.py` detecta o executável automaticamente.
