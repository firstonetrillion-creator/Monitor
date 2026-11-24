# AGENTS.md — Cerrado Aberto: Plataforma Independente de Transparência Legislativa (Inhumas/GO)

> Nome oficial: **Cerrado Aberto** (`cerradoaberto.org.br`; ver `docs/01-produto.md` e `docs/decisoes/ADR-005-decisoes-produto-e-regras-negocio.md`). Iniciativa cidadã independente de monitoramento e interpretação de dados públicos, **sem vínculo institucional, contratual ou político com a Câmara Municipal**. Este arquivo é o ponto de entrada para qualquer agente de IA (Claude Code, Codex, Cursor etc.). Leia-o inteiro antes de qualquer ação.

## 1. Missão

Transformar os dados públicos do Legislativo municipal de Inhumas (GO) — hoje espalhados em portais burocráticos — em uma plataforma cidadã moderna, **confiável, neutra e fácil de entender**, útil para o cidadão comum, jornalistas e pesquisadores.

Não somos um espelho do portal da transparência. Somos **tradução + contexto + cruzamento + alerta**, sempre com fonte verificável.

## 2. Fontes oficiais (verificadas na Fase 0)

| Fonte | URL oficial verificada | Conteúdo verificado |
|---|---|---|
| Portal da Transparência / Dados Abertos | `https://acessoainformacao.inhumas.go.leg.br/` (e hub `https://inhumas.go.leg.br/transparencia/`) | Receitas/duodécimo (`POST /api`), despesas, folha sem CPF com lotação por gabinete, diárias, licitações e contratos (`POST /api/centi`), declaração oficial de inexistência de cota parlamentar (2020–2026) |
| Nexlegis | `https://inhumas.nexlegis.com.br/` (`GET /api/*`) | Vereadores, sessões (desde 2021), presenças, pautas, votações nominais, matérias/proposições (desde out/2020) |
| Legislação municipal | `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis` | Leis, decretos, resoluções e portarias (`POST /api` + PDFs digitalizados no S3, exigindo download imediato e OCR) |

Ver fichas detalhadas em `docs/fontes/` e decisões em `docs/decisoes/ADR-001` a `ADR-005`.

## 3. Ordem de leitura

0. `docs/BRIEFING-PARA-AGENTES.md` — atalho técnico completo (mapa de código, síntese das ADRs 001–008, lacunas atuais e trilhas de revisão/brainstorm)
1. `docs/01-produto.md` — visão, público, cruzamentos, UX, identidade
2. `docs/02-arquitetura.md` — stack, camadas, modelo de dados conceitual
3. `docs/03-fontes-de-dados.md` — estado de cada fonte e ficha de reconhecimento
4. `docs/04-roadmap.md` — fases e critérios de aceite (**trabalhe somente na fase ativa**)
5. `docs/05-etica-legal-editorial.md` — regras inegociáveis
6. `docs/06-glossario.md` — termos legislativos e contábeis
7. `docs/decisoes/` — ADRs (decisões já tomadas; não reverta sem novo ADR)

## 4. Princípios inegociáveis

1. **Proveniência em tudo.** Todo registro guarda `fonte_url`, `coletado_em`, `hash_conteudo`, `versao_coletor`. Todo número exibido ao cidadão mostra fonte e data.
2. **Bruto imutável.** Guarde o HTML/JSON/PDF original antes de qualquer transformação. Nunca sobrescreva; versione.
3. **Fatos, não veredictos.** A plataforma exibe fatos e indícios com contexto. Nunca acusa, nunca conclui irregularidade, nunca ranqueia de forma sensacionalista. Ver `docs/05`.
4. **Multi-município desde o dia 1.** Nenhuma regra, tabela ou constante pode assumir que só existe Inhumas. Use `municipio_id`/configuração por município.
5. **Coleta educada.** Respeite `robots.txt`, limite de taxa, User-Agent identificável, cache agressivo, sem paralelismo abusivo. Em dúvida, pare e pergunte.
6. **Idempotência.** Reexecutar uma coleta não duplica nem corrompe dados.
7. **Privacidade (LGPD).** Não armazene nem exiba CPF completo, endereço residencial, dados de dependentes ou qualquer dado pessoal desnecessário. Mascare por padrão.
8. **Não invente.** Se não sabe um endpoint, formato, regra legal ou valor: pesquise, registre a dúvida em `docs/03` ou pergunte ao responsável. Suposições devem ser marcadas `[SUPOSIÇÃO]` e listadas.
9. **Português claro para o cidadão.** Interface sem juridiquês; siglas explicadas.

## 5. Convenções

- **Idioma:** documentação e textos de UI em PT-BR. Código, commits e nomes de infraestrutura em inglês. **Entidades de domínio em português sem acento** (`vereador`, `proposicao`, `sessao`, `empenho`), `snake_case`.
- **Stack padrão (ADR-001, provisória):** Python 3.12 + `uv`; `httpx` + `selectolax` (coleta estática), Playwright **só como fallback**; `pdfplumber` + Tesseract (PDF/OCR); PostgreSQL 16; migrações SQL versionadas; FastAPI; Next.js (App Router) + Tailwind + Observable Plot; testes com `pytest` e `playwright test`.
- **Estrutura do repositório:**
  ```
  apps/coleta/      # coletores (Python)
  apps/api/         # FastAPI
  apps/web/         # Next.js
  db/migrations/    # SQL versionado
  data/             # bruto e banco local (gitignored)
  docs/             # documentação, relatórios e ADRs
  scripts/          # rotinas operacionais, validação de docs e launcher
  prompts/          # prompts de tarefa para agentes
  skills/           # skills reutilizáveis de domínio
  .agents/          # agentes revisores, regras e workflows
  .github/          # workflows de CI
  ```
- **Git:** commits pequenos e descritivos (Conventional Commits). Uma tarefa = um branch/PR.
- **Segredos:** apenas em variáveis de ambiente; nunca no repositório.

## 6. Como trabalhar (ciclo obrigatório)

1. **Entender:** leia os docs relevantes e a fase ativa.
2. **Planejar:** escreva um plano curto (o que, por quê, arquivos, riscos) e **espere aprovação** em tarefas que alterem arquitetura, esquema de banco ou comportamento de coleta.
3. **Implementar** em passos pequenos, com testes.
4. **Verificar:** rode testes, linters e, para coletores, valide contra fixtures reais.
5. **Documentar:** atualize `docs/` e crie ADR para decisões relevantes.
6. **Reportar:** resumo do que foi feito, o que ficou pendente, suposições e riscos.

## 7. Definição de pronto (DoD)

- [ ] Funciona e tem testes (fixtures reais para coletores)
- [ ] Proveniência registrada em todos os registros novos
- [ ] Idempotente e com tratamento de erro/retentativa
- [ ] Sem dado pessoal desnecessário
- [ ] Documentação atualizada; ADR criado se houve decisão
- [ ] Linguagem neutra em qualquer texto voltado ao cidadão

## 8. Proibido sem aprovação explícita do responsável

- Coleta em volume (além de amostras de reconhecimento), paralelismo agressivo, burlar CAPTCHA ou autenticação
- Publicar qualquer conteúdo que nomeie pessoas com juízo de valor
- Trocar a stack, o banco ou o modelo de dados central
- Adicionar dependência paga ou serviço externo com custo

## 9. Skills disponíveis (`skills/`)

| Skill | Use quando |
|---|---|
| `reconhecimento-de-fonte` | Antes de qualquer coletor novo |
| `scraper-resiliente` | Implementar/alterar um coletor |
| `normalizacao-e-entidades` | Limpar dados e unificar vereadores/fornecedores |
| `qualidade-de-dados` | Criar testes, métricas e alertas de dados |
| `texto-cidadao` | Escrever resumos, rótulos, alertas e qualquer texto público |
| `frontend-cidadao` | Construir telas e componentes (em conjunto com `modern-web-guidance`) |

## 10. Fase ativa

**Fase 5 — Aprofundamento (implementada e validada em homologação em 24/11/2026).** Ver `docs/04-roadmap.md`, `docs/fase-5/plano-aprofundamento.md`, `docs/fase-5/relatorio-fase-5.md` e `docs/decisoes/ADR-008-aprofundamento-busca-bairros-legislacao-comparativo.md`. Próxima fase (Fase 6 — Replicação / Publicação em Produção) só pode ser aberta após aprovação explícita do responsável.

Histórico: Fase 0 concluída e aprovada em 12/11/2026 · Fase 1 concluída para 2025–2026 em 12/11/2026 (Lote 3 — 2020–2024 — pendente de autorização) · Fase 2 concluída para o exercício de 2026 em 12/11/2026 · Fase 3 implementada e homologada em 18/11/2026 (teste presencial com usuários pendente pelo responsável) · Fase 4 implementada e validada em homologação em 18/11/2026 · Fase 5 implementada e validada em homologação em 24/11/2026.
