# ADR-001 — Stack inicial e confirmação pós-Fase 0

- **Status:** Proposta para aprovação (revisada ao fim da Fase 0 em 2026-11-12)
- **Decisão:**
  - **Coleta:** Python 3.12 + `uv` + `httpx` para consumo direto das APIs JSON descobertas na Fase 0 (`GET https://inhumas.nexlegis.com.br/api/*`, `POST https://acessoainformacao.inhumas.go.leg.br/api/centi` e `POST https://acessoainformacao.inhumas.go.leg.br/api`); `selectolax` para páginas HTML auxiliares; **Playwright mantido apenas como fallback de contingência** (não necessário no caminho crítico inicial).
  - **PDF e OCR:** `pdfplumber` + **Tesseract OCR (`por`) obrigatório** no pipeline de documentos, pois o reconhecimento comprovou que leis recentes (ex.: Lei 3.577/2026) são publicadas como PDF escaneado em imagem sem camada de texto.
  - **Banco e Backend:** PostgreSQL 16 (`pg_trgm`, full-text `portuguese`) + migrações SQL versionadas + FastAPI.
  - **Frontend:** Next.js (App Router) + Tailwind + Observable Plot.
  - **Testes e Qualidade:** `pytest` (com fixtures reais salvas em `apps/coleta/tests/fixtures/`) e `playwright test` para E2E web.
- **Motivo:** As três fontes principais expõem endpoints JSON estruturados sem bloqueio de CAPTCHA ou login, tornando a coleta via `httpx` mais rápida, barata, determinística e fácil de testar do que automação de navegador.
- **Consequências:** Menor consumo de memória/CPU nos coletores e em GitHub Actions/cron; necessidade de incluir `tesseract-ocr` e `tesseract-ocr-por` no ambiente de execução do extrator de documentos.
