# Tarefa — Fase 4: Distribuição, Retenção e Atualização Semanal (executar só após aprovação do plano)

**Skills:** `scraper-resiliente`, `qualidade-de-dados`, `texto-cidadao`, `frontend-cidadao`, `modern-web-guidance`
**Pré-requisitos:** Fases 1, 2 e 3 concluídas em homologação e plano `docs/fase-4/plano-distribuicao-e-retencao.md` aprovado pelo responsável (incluindo decisões D1–D5).

## Objetivo
Integrar ao sistema:
1. Coleta incremental semanal do Nexlegis (`apps/coleta`), trazendo apenas sessões e proposições novas/atualizadas desde a última coleta verificada, com bruto imutável e idempotência no PostgreSQL 16;
2. Resumos em linguagem simples (`Resumo automático` + link para o documento original) para matérias legislativas e boletins de sessão;
3. Central `/boletins` e componentes de compartilhamento com alertas curtos para WhatsApp (`<= 400 caracteres`) e gerador de cartões PNG (`1080×1350` Feed/Carrossel e `1080×1920` Stories/Status) para o Instagram Oficial do Cerrado Aberto.

## Entregas
- Coletor incremental `apps/coleta/src/cerrado_aberto_coleta/nexlegis/incremental.py` + script `scripts/atualizar-semana.ps1`
- Motor de resumos `apps/api/src/cerrado_aberto_api/resumos.py` e endpoint `GET /api/v1/boletins/resumo-semanal` (somente leitura)
- Página `/boletins` em `apps/web`, exibição de resumos automáticos em `/sessoes/[id]` e `/materias/[id]`, cópia/envio para WhatsApp e download de cartões PNG para Instagram
- Testes `pytest` e `playwright test` (acessibilidade WCAG 2.1 A/AA, zero CPF e zero vocabulário proibido nos resumos e alertas)
- `ADR-007` documentando as decisões D1–D5 e relatório da Fase 4 com capturas de tela
