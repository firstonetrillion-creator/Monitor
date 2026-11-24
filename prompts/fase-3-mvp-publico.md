# Tarefa — Fase 3: MVP público em beta fechado (executar só após aprovação do plano)

**Skills:** `frontend-cidadao`, `texto-cidadao`, `qualidade-de-dados`
**Pré-requisitos:** Fases 1 e 2 concluídas (API FastAPI v1 com dados 2025–2026 do Nexlegis e 2026 do Portal da Transparência) e plano `docs/fase-3/plano-mvp-publico.md` aprovado, incluindo as decisões D1–D7.

## Objetivo
Construir o site cidadão em `apps/web` (Next.js + Tailwind + Observable Plot), consumindo apenas a API v1 somente leitura, com home de 3 perguntas, perfil do vereador, "para onde vai o dinheiro", sessões/pauta, páginas de método e limitações e canal de correção.

## Entregas
- Rotas e componentes descritos no plano, com dados reais
- Fonte, data da coleta e "Como calculamos" em todo número; ausência nunca exibida como zero
- Testes `playwright test` (fluxos + acessibilidade), checagem automática de CPF e de vocabulário proibido no HTML gerado
- Capturas de tela de cada etapa para revisão humana
- ADR-006 com as decisões do frontend; roadmap e relatório da fase atualizados

## Regras específicas
- Implementar por etapas e apresentar capturas ao fim de cada uma.
- Nenhuma coleta nova, hospedagem com custo ou publicação aberta sem autorização explícita.
- Ordem alfabética e mesmo tratamento visual para todos os vereadores; nenhum ranking.
