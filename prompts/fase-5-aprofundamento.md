# Prompt de Execução — Fase 5: Aprofundamento

> **Pré-requisito:** aprovação explícita do responsável nas decisões `D1–D5` de `docs/fase-5/plano-aprofundamento.md`.

## Contexto obrigatório
Leia antes de alterar código:
1. `AGENTS.md` e `docs/05-etica-legal-editorial.md`
2. `docs/fase-5/plano-aprofundamento.md`
3. `docs/fontes/legislacao.md` e `docs/decisoes/ADR-004-estrategia-legislacao.md`
4. Skills: `postgres-patterns`, `database-migrations`, `api-design`, `scraper-resiliente`, `normalizacao-e-entidades`, `qualidade-de-dados`, `texto-cidadao`, `frontend-cidadao` e `modern-web-guidance`.

## Escopo das 4 etapas
1. **Etapa 1 (Banco + Coletores `apps/coleta`):**
   - Criar `db/migrations/0003_fase5_aprofundamento.sql` (`normalizar_texto_busca`, índices GIN FTS `portuguese`, tabelas `norma`, `bairro`, `proposicao_bairro`, `comparativo_legislativo_siconfi`).
   - Implementar e testar `bairros.py`, `siconfi/` (DCA `2024` e `2025` Função `01 - Legislativa` de Inhumas + 7 pares de Goiás) e `legislacao/` (metadados das 406 leis + pipeline `pdfplumber`/Tesseract OCR conforme `ADR-004`).
   - Persistir no PostgreSQL 16 de forma 100% idempotente e sem CPF.
2. **Etapa 2 (API FastAPI `apps/api`):**
   - Criar endpoints somente leitura `GET /api/v1/busca`, `GET /api/v1/bairros`, `GET /api/v1/bairros/{slug}`, `GET /api/v1/legislacao`, `GET /api/v1/legislacao/{id}` e `GET /api/v1/comparativo`.
   - Adicionar rate limiting configurável por IP e enriquecer OpenAPI.
   - Validar com `ruff` e `pytest` (incluindo LGPD e neutralidade).
3. **Etapa 3 (Frontend Next.js `apps/web`):**
   - Criar `/busca`, `/bairros`, `/legislacao`, `/legislacao/[id]`, `/comparativo` e `/dados-abertos`, além da busca rápida na Home (`/`) e links de navegação.
   - Garantir preservação de `NULL`, fonte/data em tudo, mapas/gráficos acessíveis com tabela alternativa e CSV, linguagem neutra e zero dependências pagas.
4. **Etapa 4 (Verificação e Documentação):**
   - Expandir `apps/web/tests/mvp.spec.ts` para todas as novas rotas (desktop + mobile + `axe-core` WCAG 2.1 A/AA).
   - Salvar capturas em `docs/fase-5/capturas/`.
   - Criar `docs/decisoes/ADR-008-aprofundamento-busca-bairros-legislacao-comparativo.md` e `docs/fase-5/relatorio-fase-5.md`; atualizar `docs/04-roadmap.md` e `AGENTS.md`.
