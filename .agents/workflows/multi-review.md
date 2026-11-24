---
description: "Multi-agent specialist code review panel with concrete failure-scenario filtering and synthesis"
---
# Multi-Agent Code Review (`/multi-review`)

Review the current change or target scope using a parallel panel of independent specialist reviewers, then synthesize their findings into one deduplicated, ranked report.

## 1. Fix Scope & Snapshot
Record the exact target (`git diff`, files modified, or module path) plus connected callers, contracts, and tests. All reviewers operate in **read-only mode**: no edits, commits, or publishing during review.

## 2. Dispatch the Panel in Parallel
Send the same target scope to the applicable specialist lenses in `.agents/agents/`:
- **Backend / Python / Data (`python-reviewer`, `fastapi-reviewer`, `database-reviewer`, `silent-failure-hunter`)**: async correctness, Pydantic/OpenAPI contracts, SQL idempotency, provenance fields (`fonte_url`, `coletado_em`, `hash_conteudo`, `versao_coletor`), and swallowed exceptions.
- **Frontend / TypeScript / A11y (`typescript-reviewer`, `react-reviewer`, `a11y-architect`)**: strict typing, preservation of `NULL` (never coerced to `0`), WCAG 2.1/2.2 keyboard & screen-reader semantics, and `<DadoComFonte>` provenance display.
- **Security & LGPD (`security-reviewer`)**: OWASP Top 10, zero full CPF exposure, XSS sanitization on raw legislative strings, and secret handling.
- **Editorial Neutrality (`texto-cidadao` skill)**: neutral citizen-facing language, zero value judgment, clear explanation of acronyms and limitations.

Each reviewer must format every finding as:
`file:line — SEVERITY — one-sentence claim — concrete failure scenario (the exact input, data state, or user action that causes this to break or violate AGENTS.md)`

> Findings without a concrete failure scenario are discarded as hunches.

## 3. Synthesize & Rank
1. **Deduplicate**: collapse identical underlying issues flagged by multiple lenses into one entry and note which reviewers agreed.
2. **Verify & Filter**: verify each claim against the actual files before keeping or dropping it.
3. **Rank**:
   - **CRITICAL**: Security/LGPD breach, data corruption, missing provenance, or editorial value judgment (`AGENTS.md` violation).
   - **HIGH**: Real functional bug, silent failure, broken accessibility, or `NULL` coerced to zero.
   - **MEDIUM**: Maintainability, file > 800 lines, or missing test coverage.
   - **LOW**: Minor style suggestion.
