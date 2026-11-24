# 04 — Roadmap (MVP)

Regra: **trabalhe somente na fase ativa.** Avançar de fase exige aprovação do responsável humano e todos os critérios de aceite cumpridos.

## Fase 0 — Descoberta e validação *(CONCLUÍDA E APROVADA EM 12/11/2026)*
**Entregas**
- [x] Fichas de reconhecimento das 3 fontes principais (`docs/fontes/transparencia.md`, `docs/fontes/nexlegis.md`, `docs/fontes/legislacao.md`)
- [x] Fixtures reais (amostras pequenas) de cada tipo de página/resposta (`apps/coleta/tests/fixtures/`)
- [x] Confirmação das URLs corretas (inclui a de legislação: `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis`)
- [x] Rascunho e versão final do pedido formal via LAI (`docs/fase-0/pedido-lai-final.md` e `docs/fase-0/pedido-lai-rascunho.md`)
- [x] Roteiro de entrevistas com 8–10 pessoas de Inhumas (`docs/fase-0/roteiro-entrevistas.md`)
- [x] Shortlist de nomes com checagem de domínio/handles (`docs/fase-0/shortlist-nomes.md` — nome escolhido: **Cerrado Aberto**, `cerradoaberto.org.br`)
- [x] ADRs: estratégia de coleta por fonte (`ADR-002`, `ADR-003`, `ADR-004`), stack confirmada (`ADR-001`) e decisões de produto e regras de negócio (`ADR-005`)
**Aceite:** para cada fonte, sabemos *como* coletar, *o que* há, *desde quando* e *quais riscos*.

## Fase 1 — Fundação de dados (Nexlegis primeiro) *(CONCLUÍDA PARA O BIÊNIO 2025–2026 EM 12/11/2026)*
**Entregas**
- [x] Migrações SQL versionadas das tabelas de domínio (`db/migrations/0001_init_core_and_nexlegis.sql`)
- [x] Coletor em 3 etapas (`fetch` → `parse` → `load`), parametrizado por `municipio_id` (`apps/coleta/src/cerrado_aberto_coleta/nexlegis/`)
- [x] Tabela mestre de vereadores + aliases curados e classificação de proposições (`apps/coleta/src/cerrado_aberto_coleta/entidades.py`)
- [x] Armazenamento bruto local versionado em `data/raw/` com SHA-256 e governança de OCR (`apps/coleta/src/cerrado_aberto_coleta/storage.py`)
- [x] Regra de negócio codificada e testada do indicador **Custo da Estrutura do Mandato** (`apps/coleta/src/cerrado_aberto_coleta/custo_mandato.py`)
- [x] Testes automatizados (`pytest`) com fixtures reais, idempotência e layout quebrado (`apps/coleta/tests/`)
- [x] Relatório de cobertura histórica e de qualidade (`docs/fase-1/relatorio-cobertura-e-qualidade-nexlegis.md`)
- [x] Execução do **Lote 1 de Backfill do Nexlegis (2026)** (concluído e validado em 12/11/2026: 130 requisições, 262 arquivos e manifestos gerados em `data/raw/inhumas-go/nexlegis/`)
- [x] Execução do **Lote 2 de Backfill do Nexlegis (2025)** (concluído e validado em 12/11/2026: 141 requisições, 284 arquivos e manifestos gerados em `data/raw/inhumas-go/nexlegis/2025/`)
- [x] Persistência idempotente em **PostgreSQL 16** do biênio 2025–2026 (`apps/coleta/src/cerrado_aberto_coleta/nexlegis/postgres_loader.py` + `apps/coleta/tests/test_postgres_persistence.py`)
- [x] API pública somente leitura em **FastAPI v1** com paginação, filtros, OpenAPI e proteção LGPD (`apps/api/src/cerrado_aberto_api/` + `apps/api/tests/test_api_v1.py`)
- [ ] Execução do lote histórico **Lote 3 (2020–2024)** — aguardando autorização explícita por lote
**Aceite:** reexecução idempotente; 100% dos registros com proveniência; relatório de cobertura histórica; fixtures cobrindo as variações de layout encontradas.

## Fase 2 — Segunda fonte e primeiro cruzamento (Portal da Transparência CENTI/NúcleoGov — 2026) *(CONCLUÍDA PARA 2026 EM 12/11/2026)*
**Entregas**
- [x] Etapa 1: Reconhecimento técnico aprofundado do CENTI/NúcleoGov (contratos `POST /api` e `POST /api/centi`, campos, paginação, filtros e limitações documentados em `docs/fontes/transparencia.md` `v0.2.0`)
- [x] Etapa 2: Arquitetura e documentação da proteção LGPD e base legal (`docs/fontes/transparencia.md` Seção 4)
- [x] Etapa 3: Coleta de 2026 do Portal da Transparência (Folha/Subsídios/Lotação de jan–out/2026, 360 empenhos de despesas, 14 diárias identificadas no Elemento 14, 22 lançamentos de duodécimo e Declarações Oficiais) em `data/raw/inhumas-go/transparencia_centi/2026/`
- [x] Etapa 4: Cruzamento dos dados e cálculo de **Custo da Estrutura do Mandato** em 2026 no PostgreSQL 16 (`db/migrations/0002_init_transparencia_and_custo_mandato.sql`) com reconciliação integral de totais
- [x] Etapa 5: Integração com o Nexlegis no perfil completo do vereador (`GET /api/v1/vereadores/{id}`) e 6 endpoints dedicados de transparência em `/api/v1/transparencia/*`
**Aceite:** reconciliação de totais com o que o portal exibe; método do indicador, limitações e relatório documentados em `docs/fase-2/relatorio-transparencia-e-custo-mandato-2026.md`.

## Fase 3 — MVP público (beta fechado / homologação) *(ETAPAS 1–7 CONCLUÍDAS EM HOMOLOGAÇÃO EM 18/11/2026 — pronto para Etapa 8: teste com usuários)*
**Entregas**
- [x] Aplicação web `apps/web` (Next.js 16 + TypeScript + Tailwind CSS + Observable Plot) consumindo a API FastAPI v1 (somente leitura)
- [x] Telas obrigatórias implementadas e validadas com dados reais do PostgreSQL 16: Página inicial (`/`), Vereadores (`/vereadores` e `/vereadores/[id]`), Custo da Estrutura do Mandato (`/custo-mandato`), Despesas públicas (`/despesas` e `/dinheiro`, com duodécimo × devoluções, despesas por estágio, por elemento, por favorecido PJ e exportação CSV a um clique), Diárias (`/diarias`), Sessões e votações (`/sessoes`, `/sessoes/[id]` e `/materias/[id]`), Metodologia (`/como-calculamos`), Cobertura (`/cobertura-e-limitacoes`), Sobre (`/sobre`) e Canal de correção (`/correcoes`)
- [x] Fonte, data de coleta e link "Como calculamos" nos indicadores; preservação estrita de `NULL` (nunca convertido em zero); zero CPF completo em HTML; acessibilidade WCAG 2.1 A/AA verificada via `axe-core` e `playwright test` (14/14 testes desktop e mobile)
- [x] Capturas de tela desktop e mobile geradas em `docs/fase-3/capturas/` (19 imagens), relatório técnico (`docs/fase-3/relatorio-mvp-homologacao.md`), decisões registradas em `ADR-006` e roteiro prático de teste com usuários no MVP (`docs/fase-3/roteiro-teste-usuarios-mvp.md`)
- [ ] Aplicação presencial do roteiro de teste com usuários reais de Inhumas (`docs/fase-3/roteiro-teste-usuarios-mvp.md` e `docs/fase-0/roteiro-entrevistas.md`) pelo responsável
**Aceite:** teste com usuários reais de Inhumas; nenhum texto com juízo de valor (revisão com a skill `texto-cidadao`).

## Fase 4 — Distribuição e retenção *(ETAPAS 1–4 IMPLEMENTADAS E VALIDADAS EM HOMOLOGAÇÃO EM 18/11/2026)*
**Entregas**
- [x] Etapa 1: Coletor incremental semanal educado do Nexlegis (`apps/coleta/src/cerrado_aberto_coleta/nexlegis/incremental.py`), script operacional Windows (`scripts/atualizar-semana.ps1`) e 1ª coleta semanal executada (`execucao_id=6d9b5d8d-3bb1-4899-8639-90555fba9beb`, 12 requisições, intervalo `>= 3,0s`), incorporando a **Sessão Ordinária 044/2026 (17/11/2026)** e atualizando a base para `134` sessões e `1.311` proposições
- [x] Etapa 2: Motor determinístico de resumos em linguagem simples (`apps/api/src/cerrado_aberto_api/resumos.py`) com selo obrigatório *"Resumo automático"* + link para o documento original, integrado em `GET /api/v1/sessoes/{id}`, `GET /api/v1/materias/{id}` e no novo endpoint `GET /api/v1/boletins/resumo-semanal` (`apps/api/src/cerrado_aberto_api/boletins_router.py`)
- [x] Etapa 3: Central `/boletins` (`apps/web/src/app/boletins/`) com alertas prontos para **WhatsApp** (`<= 400` caracteres, link verificável, opção de descadastro e botão copiar acessível), legenda neutra e gerador local em Canvas 2D de cartões PNG em alta resolução (**Carrossel 3 slides `1080×1350`** e **Story/Status `1080×1920`**) para o **Instagram Oficial do Cerrado Aberto (`@cerradoaberto`)**, além do bloco `<ResumoCidadaoBox>` nas páginas `/sessoes/[id]` e `/materias/[id]`
- [x] Etapa 4: Verificação ponta a ponta (`ruff`, `pytest`, `eslint`, `next build`, `16/16` testes `playwright test` + `axe-core` desktop/mobile), capturas e cartões PNG salvos em `docs/fase-4/capturas/`, registro da decisão em `ADR-007` e relatório técnico em `docs/fase-4/relatorio-fase-4.md`
- [ ] Operação recorrente: agendamento semanal pelo responsável (`scripts/atualizar-semana.ps1` / Agendador de Tarefas), publicação dos primeiros cards no `@cerradoaberto` e coleta de métricas de retorno semanal com parcerias locais (rádio, imprensa, associações, escolas)
**Métrica:** retorno semanal. **Decisões:** `docs/decisoes/ADR-007-distribuicao-resumos-e-atualizacao-semanal.md`.

## Fase 5 — Aprofundamento *(ETAPAS 1–4 IMPLEMENTADAS E VALIDADAS EM HOMOLOGAÇÃO EM 24/11/2026)*
**Entregas**
- [x] Etapa 1: Migração SQL `0003_fase5_aprofundamento.sql` (`normalizar_texto_busca`, 5 índices GIN FTS `portuguese`, tabelas `norma`, `bairro`, `proposicao_bairro`, `comparativo_legislativo_siconfi`), extrator determinístico de `52` bairros de Inhumas (`231` proposições mapeadas / `291` vínculos), coleta oficial **SICONFI / Tesouro Nacional** (`DCA-Anexo I-E` `2024` e `2025`, Inhumas + 7 pares GO) e coleta educada dos metadados das **`407` leis municipais** (`leis/buscaAvancada`, `Crawl-Delay = 5,2s`) + pipeline híbrido `pdfplumber`/Tesseract OCR (`ADR-004`)
- [x] Etapa 2: 6 novos endpoints somente leitura na API FastAPI v1 (`GET /api/v1/busca`, `/bairros`, `/bairros/{slug}`, `/legislacao`, `/legislacao/{id}`, `/comparativo`) + middleware de **rate limiting configurável por IP** (`429` / `X-RateLimit-*`) + `16/16` testes `pytest`
- [x] Etapa 3: Novas telas em `apps/web`: `/busca` (+ busca rápida na Home `/`), `/bairros` (mapa cartográfico vetorial local + tabela WCAG + CSV), `/legislacao` e `/legislacao/[id]` (catálogo + resumo automático + transparência OCR + CSV), `/comparativo` (Inhumas × 7 cidades GO via SICONFI, linguagem neutra + gráfico Observable Plot + CSV) e `/dados-abertos` (portal da API Pública com exemplos `cURL`/`Python`/`JavaScript` copiáveis)
- [x] Etapa 4: Verificação ponta a ponta (`ruff`, `26/26 pytest` coleta, `16/16 pytest` API, `eslint`, `next build` 23 rotas, `24/24 playwright test` + `axe-core` WCAG 2.1 A/AA desktop/mobile), capturas em `docs/fase-5/capturas/`, `ADR-008` e `docs/fase-5/relatorio-fase-5.md`
- [ ] Opcional local: instalar Tesseract OCR (`por`) no servidor/máquina para processamento em lote dos PDFs escaneados de legislação (`ocr.py` já pronto)
**Decisões:** `docs/decisoes/ADR-008-aprofundamento-busca-bairros-legislacao-comparativo.md`.

## Fase 6 — Replicação
Abrir código, documentar o processo, adaptar a outras câmaras que usam o mesmo sistema.
