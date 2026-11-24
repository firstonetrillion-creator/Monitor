---
description: "Executa a bateria completa de quality gates do Cerrado Aberto (docs, ESLint, pytest, LGPD e proveniência)."
---
# Cerrado Aberto Quality Gate (`/quality-gate`)

Execute e reporte com evidências frescas (`exit code` e resumo da saída) cada um dos 4 portões de qualidade do repositório:

## 1. Integridade da Documentação e JSONs
```powershell
node scripts/validate-docs.mjs
```

## 2. Qualidade e Fronteiras do Frontend (`apps/web`)
```powershell
npm --prefix apps/web run lint
```
*(Verifica regras Next.js, TypeScript, `quality/max-lines` <= 800 e `quality/no-direct-console`)*

## 3. Testes Automatizados de Coleta e API (`apps/coleta` e `apps/api`)
```powershell
uv run --directory apps/coleta pytest
uv run --directory apps/api pytest
```

## 4. Checklist Inegociável (`AGENTS.md`)
- [ ] **Proveniência:** 100% dos números exibidos possuem `fonte_url`, `coletado_em` e link para `/como-calculamos`.
- [ ] **Preservação de `NULL`:** nenhum dado ausente foi convertido silenciosamente em `0`.
- [ ] **LGPD:** zero CPF completo exposto na API ou no HTML gerado.
- [ ] **Neutralidade Editorial (`texto-cidadao`):** zero juízo de valor ou adjetivação opinativa em textos voltados ao cidadão.
