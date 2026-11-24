# Tarefa — Fase 1: Coletor do Nexlegis (executar só após aprovação da Fase 0)

**Skills:** `scraper-resiliente`, `normalizacao-e-entidades`, `qualidade-de-dados`
**Pré-requisitos:** `docs/fontes/nexlegis.md` completa e ADR de estratégia aprovado.

## Objetivo
Coletar vereadores, sessões, presenças, proposições, autorias, tramitações e votações nominais, com bruto imutável, banco tratado e testes.

## Entregas
- Migrações SQL versionadas das tabelas de domínio (`docs/02-arquitetura.md`)
- Coletor em 3 etapas (fetch → parse → load), parametrizado por `municipio_id`
- Tabela mestre de vereadores + aliases
- Testes com fixtures reais, idempotência e layout quebrado
- Relatório de cobertura histórica e de qualidade

## Regras específicas
- Plano antes do código; aguardar aprovação.
- Backfill histórico em lotes pequenos e com taxa baixa, mediante minha autorização por lote.
- Atualizar roadmap e fichas ao final.
