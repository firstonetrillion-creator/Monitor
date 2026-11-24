# Briefing Técnico para Agentes de IA e Revisores Externos — Cerrado Aberto

> **Para que serve este documento:** dar a qualquer agente de IA (Claude, Codex, Gemini, Cursor etc.) ou revisor técnico o **mapa mental completo do projeto em uma leitura** — o que já foi construído (Fases 0 a 5), por que cada escolha foi feita (`ADR-001` a `ADR-008`), onde estão as lacunas reais e quais perguntas estratégicas merecem ideias novas e críticas profundas.

---

## 1. Resumo Executivo e Guardrails Inegociáveis

O **Cerrado Aberto** (`cerradoaberto.org.br`) é uma plataforma cidadã independente de transparência legislativa focada inicialmente na Câmara Municipal de Inhumas (GO), **sem qualquer vínculo institucional, contratual ou político-partidário com a Câmara Municipal ou com agentes públicos**.

As **Fases 0 a 5** foram implementadas e validadas ponta a ponta em homologação local em **24/11/2026**. A **Fase 6 (Replicação / Publicação em Produção)** ainda não foi aberta.

### 7 restrições inegociáveis (leia [`AGENTS.md`](../AGENTS.md) e [`docs/05-etica-legal-editorial.md`](05-etica-legal-editorial.md))
1. **Proveniência obrigatória:** todo registro persistido carrega `municipio_id`, `fonte_id`, `fonte_url`, `coletado_em`, `hash_conteudo` (SHA-256) e `versao_coletor`. Todo número na UI exibe fonte e data.
2. **Bruto imutável:** payloads JSON/HTML/PDF originais ficam em `data/raw/` (gitignored) com hash SHA-256 antes de qualquer normalização.
3. **Fatos, não veredictos:** a plataforma apresenta fatos, séries e indícios com contexto. Nunca acusa, conclui irregularidade ou usa palavras de juízo de valor (`fraude`, `desvio`, `esquema`, `irregular`, `suspeito`, `escândalo`, `absurdo`, `farra`, `mamata`). Preserva estritamente `NULL != 0`.
4. **Multi-município desde o dia 1:** nenhuma tabela ou regra de banco assume apenas Inhumas (`municipio_id` em todo o esquema).
5. **Coleta educada e legal:** respeita `robots.txt`, `Crawl-Delay >= 3,0s` (Nexlegis) e `>= 5,0s` (Transparência/Legislação), `User-Agent` identificável, concorrência 1, e **jamais contorna CAPTCHA ou autenticação** (ex.: `acao=new_captcha` no CENTI).
6. **Privacidade (LGPD):** minimização estrita; zero CPF completo em disco, banco, logs ou API (sanitização para `***.***.***-**`).
7. **Sem custos externos ou troca de stack sem aprovação:** não sugerir APIs pagas (ex.: LLM comercial por requisição, Google Maps pago, Meta WhatsApp Business API) como requisito obrigatório sem justificar claramente custo/benefício para aprovação humana.

---

## 2. Mapa Completo do Código (Arquivo → Responsabilidade)

### Banco de Dados (`db/migrations/`)
| Arquivo | Conteúdo |
|---|---|
| [`db/migrations/0001_init_core_and_nexlegis.sql`](../db/migrations/0001_init_core_and_nexlegis.sql) | Núcleo multi-município (`municipio`, `casa_legislativa`, `legislatura`, `partido`, `fonte`, `coleta_execucao`, `documento_bruto`, `lacuna_historica`), pessoas (`vereador`, `vereador_alias`, `mandato`), classificação (`de_para_tipo_proposicao`) e processo legislativo (`sessao`, `presenca`, `proposicao`, `autoria`, `tramitacao`, `pauta_item`, `votacao`, `voto`). |
| [`db/migrations/0002_init_transparencia_and_custo_mandato.sql`](../db/migrations/0002_init_transparencia_and_custo_mandato.sql) | Finanças públicas e transparência (`fornecedor`, `folha_pagamento`, `despesa_empenho`, `diaria`, `receita_duodecimo`, `declaracao_oficial_transparencia`, `custo_estrutura_mandato_mensal`). |
| [`db/migrations/0003_fase5_aprofundamento.sql`](../db/migrations/0003_fase5_aprofundamento.sql) | Função `IMMUTABLE` `normalizar_texto_busca(TEXT)`, 5 índices GIN de Full-Text Search `portuguese` (`proposicao`, `norma`, `sessao`, `vereador`, `despesa_empenho`), tabelas `norma`, `bairro`, `proposicao_bairro` e `comparativo_legislativo_siconfi`. |

### Coletores e Normalização (`apps/coleta/src/cerrado_aberto_coleta/`)
| Módulo | Responsabilidade |
|---|---|
| [`config.py`](../apps/coleta/src/cerrado_aberto_coleta/config.py) | `MunicipioConfig`, `FonteConfig` e `criar_config_municipio_padrao` (endpoints e `Crawl-Delay` por fonte). |
| [`storage.py`](../apps/coleta/src/cerrado_aberto_coleta/storage.py) | Protocolo `StorageBackend`, `LocalVersionedStorage` (SHA-256 em `data/raw/`), `MetadadosDocumentoBruto` e `ResultadoOCR`. |
| [`normalizacao.py`](../apps/coleta/src/cerrado_aberto_coleta/normalizacao.py) | Funções puras para texto PT-BR, valores em `R$`, datas ISO/BR, remoção de acentos e mascaramento LGPD. |
| [`entidades.py`](../apps/coleta/src/cerrado_aberto_coleta/entidades.py) | Tabela mestre `VEREADORES_MESTRE_INHUMAS` (`ResolvedorVereadores`) e classificação oficial de tipos (`MAPA_TIPOS_PROPOSICAO_PADRAO` — separa proposições parlamentares de atas e julgamentos de contas). |
| [`custo_mandato.py`](../apps/coleta/src/cerrado_aberto_coleta/custo_mandato.py) | Cálculo auditável de `Custo da Estrutura do Mandato = Subsídio Bruto + Folha Bruta do Gabinete + Diárias Atribuíveis`, preservando `NULL` em lacunas como `PRESIDENCIA` e competências em aberto. |
| [`qualidade.py`](../apps/coleta/src/cerrado_aberto_coleta/qualidade.py) | Bateria de qualidade e consistência cruzada (`avaliar_qualidade_repositorio`). |
| [`bairros.py`](../apps/coleta/src/cerrado_aberto_coleta/bairros.py) | Catálogo curado de `52` bairros/distritos de Inhumas com aliases normalizados, extração determinística de temas e bloqueio explícito de falsos positivos. |
| `nexlegis/` (`fetcher.py`, `parser.py`, `loader.py`, `schemas.py`, `lote1.py`, `lote2.py`, `incremental.py`, `postgres_loader.py`) | Pipeline 3 etapas (`fetch → parse → load`), `LayoutQuebradoError`, sanitização de CPF, Lotes 1 (`2026`) e 2 (`2025`), coleta incremental semanal e carga PostgreSQL 16 idempotente. |
| `transparencia/` (`parser.py`, `schemas.py`, `lote_2026.py`, `postgres_loader.py`) | Parser/reconciliação do Lote 2026 CENTI/NúcleoGov (folha sem CPF, 360 empenhos, 14 diárias Elemento 14, duodécimo, declarações oficiais). |
| `legislacao/` (`parser.py`, `ocr.py`, `loader.py`) | Parser das 407 leis NúcleoGov com URL canônica permanente (`/legislacao/lei/id={id}`) e pipeline híbrido `pdfplumber` + Tesseract OCR (`por`) com fallback seguro `PENDENTE_OCR`. |
| [`siconfi/collector.py`](../apps/coleta/src/cerrado_aberto_coleta/siconfi/collector.py) | Coletor oficial SICONFI/Tesouro Nacional (`DCA-Anexo I-E`, Função `01 - Legislativa`) para Inhumas + 7 cidades pares de Goiás (`2024` e `2025`). |

### API Pública Somente Leitura (`apps/api/src/cerrado_aberto_api/`)
| Módulo | Responsabilidade |
|---|---|
| [`main.py`](../apps/api/src/cerrado_aberto_api/main.py) | Aplicação FastAPI v1, `/api/v1/health` e endpoints legislativos + transparência (14 rotas `GET`). |
| [`boletins_router.py`](../apps/api/src/cerrado_aberto_api/boletins_router.py) | Endpoint `GET /api/v1/boletins/resumo-semanal`. |
| [`fase5_router.py`](../apps/api/src/cerrado_aberto_api/fase5_router.py) | 6 endpoints `GET` da Fase 5: `/busca`, `/bairros`, `/bairros/{slug}`, `/legislacao`, `/legislacao/{id}`, `/comparativo`. |
| [`resumos.py`](../apps/api/src/cerrado_aberto_api/resumos.py) | Motor determinístico (custo `R$ 0`) de tradução cidadã para proposições, sessões, legislação, alertas WhatsApp (`<= 400` chars) e carrosséis Instagram, validado contra `PALAVRAS_PROIBIDAS_TEXTO_CIDADAO`. |
| [`db.py`](../apps/api/src/cerrado_aberto_api/db.py) | Conexão `psycopg` somente leitura (`conn.read_only = True`) via `DATABASE_URL` ou cluster portátil `pgserver` (`data/pgdata`). |
| [`security.py`](../apps/api/src/cerrado_aberto_api/security.py) | `LGPDAndReadOnlyMiddleware`, `FiltroLogLGPD` e `sanitizar_estrutura_lgpd`. |
| [`rate_limit.py`](../apps/api/src/cerrado_aberto_api/rate_limit.py) | `RateLimitMiddleware` por IP em janela deslizante configurável (`CERRADO_RATE_LIMIT_RPM`, padrão `240` req/min). |
| [`schemas.py`](../apps/api/src/cerrado_aberto_api/schemas.py) & [`schemas_fase5.py`](../apps/api/src/cerrado_aberto_api/schemas_fase5.py) | Contratos Pydantic v2 de saída com metadados de proveniência. |

### Frontend Cidadão (`apps/web/src/`)
- **Proxy seguro (`GET`-only):** [`apps/web/src/app/api/v1/[...path]/route.ts`](../apps/web/src/app/api/v1/%5B...path%5D/route.ts)
- **Páginas (`apps/web/src/app/`):** `/`, `/vereadores`, `/vereadores/[id]`, `/custo-mandato`, `/despesas` (`/dinheiro` redireciona para `/despesas`), `/diarias`, `/sessoes`, `/sessoes/[id]`, `/materias/[id]`, `/boletins`, `/busca`, `/bairros` (inclui `MapaBairrosSvg.tsx`), `/legislacao`, `/legislacao/[id]`, `/comparativo`, `/dados-abertos`, `/como-calculamos`, `/cobertura-e-limitacoes`, `/sobre`, `/correcoes`.
- **Componentes e utilitários (`components/` e `lib/`):** `AvatarVereador`, `BotaoCopiar` (WCAG `aria-live`), `DadoComFonte`, `EstadoAusente`, `GlossarioTooltip`, `PlotChart` (Observable Plot + tabela acessível + CSV), `ProvenienciaBox`, `ResumoCidadaoBox`, `SiteHeader`, `SiteFooter`, `api.ts`, `cardCanvas.ts` (Canvas 2D PNG `1080×1350` e `1080×1920`), `csv.ts`, `format.ts`, `types.ts`.

### Scripts, Skills e Automação
- **Operação e utilitários (`scripts/`):** `atualizar-semana.ps1` (coleta incremental + validação), `coletar-legislacao-leis.mjs` (coleta Playwright educada `Crawl-Delay = 5,2s`), `validate-docs.mjs` (checa links Markdown, caminhos de código e JSONs) e `launcher/CerradoAbertoLauncher.cs` (inicia PostgreSQL portátil + FastAPI + Next.js em Windows).
- **Skills de domínio (`skills/`):** `reconhecimento-de-fonte`, `scraper-resiliente`, `normalizacao-e-entidades`, `qualidade-de-dados`, `texto-cidadao`, `frontend-cidadao`.
- **Agentes revisores e regras (`.agents/`):** 8 perfis revisores (`python-reviewer`, `fastapi-reviewer`, `react-reviewer`, `typescript-reviewer`, `database-reviewer`, `security-reviewer`, `a11y-architect`, `silent-failure-hunter`), regras de estilo/segurança e workflows.

---

## 3. Síntese das 8 Decisões Arquiteturais (ADRs)

Antes de sugerir mudanças que contradigam escolhas já tomadas, entenda o contexto das ADRs existentes em [`docs/decisoes/`](decisoes/):

| ADR | Decisão central | Motivação principal |
|---|---|---|
| [`ADR-001`](decisoes/ADR-001-stack.md) | Python 3.12 (`httpx`, `pdfplumber`, Tesseract) + PostgreSQL 16 + FastAPI + Next.js | Fontes expõem APIs JSON diretas; evita custo de scraping pesado em navegador quando desnecessário. |
| [`ADR-002`](decisoes/ADR-002-estrategia-nexlegis.md) | Coletar Nexlegis via `GET /api/*` (`Crawl-Delay >= 3s`); separar Atas (`tipo_id=144`) e Julgamentos (`211`); calcular placar via `votos[]` | `/api/presencas` retorna 404 (dados ficam em `/api/sessoes/{id}`) e flag `unanime` nem sempre é confiável. |
| [`ADR-003`](decisoes/ADR-003-estrategia-transparencia.md) | Coletar CENTI/NúcleoGov via `POST /api` e `POST /api/centi` (`Crawl-Delay >= 5s`); mascarar CPFs na ingestão; pedir histórico pré-2026 via LAI | Portal migrou do SIGEP para CENTI em set/2026; anexos têm CAPTCHA (`acao=new_captcha`, proibido contornar). |
| [`ADR-004`](decisoes/ADR-004-estrategia-legislacao.md) | Usar URL canônica `/legislacao/lei/id={id}` (nunca URL S3 que expira em 40 min); pipeline híbrido `pdfplumber` + Tesseract OCR (`por`) | Leis recentes (ex.: Lei 3.577/2026) são PDFs escaneados sem texto nativo e têm erros de digitação na ementa oficial. |
| [`ADR-005`](decisoes/ADR-005-decisoes-produto-e-regras-negocio.md) | Nome **Cerrado Aberto**; fórmula do **Custo da Estrutura do Mandato**; nota obrigatória de CEAP inexistente; `StorageBackend` abstraído | Garante transparência contábil, independência editorial, preservação de `NULL` e futuro suporte S3. |
| [`ADR-006`](decisoes/ADR-006-mvp-publico-beta-fechado.md) | População IBGE `54.133` hab. (2026) para per capita; página `/correcoes` sem escrita em banco; avatares uniformes; tipografia `Fraunces` + `Inter` + `JetBrains Mono` | Evita assimetria visual entre vereadores, garante simetria editorial e segue `modern-web-guidance`. |
| [`ADR-007`](decisoes/ADR-007-distribuicao-resumos-e-atualizacao-semanal.md) | Coleta semanal incremental; motor determinístico de resumos (custo `R$ 0`); cards PNG em Canvas 2D (`@cerradoaberto`) e alerta WhatsApp `<= 400` chars | Evita custo de APIs LLM/Meta e elimina risco de alucinação factual em textos sobre pessoas públicas. |
| [`ADR-008`](decisoes/ADR-008-aprofundamento-busca-bairros-legislacao-comparativo.md) | FTS nativo `portuguese` com `normalizar_texto_busca` (sem `pg_trgm`/`unaccent` no `pgserver`); 407 leis; 52 bairros locais com mapa SVG; SICONFI (`DCA-Anexo I-E`, Função 01) + rate limit | `pgserver` no Windows não traz extensões contrib; mapa SVG local e SICONFI evitam APIs pagas e mantêm neutralidade. |

---

## 4. Lacunas Reais, Dívidas Técnicas e Pendências Conhecidas

Aqui estão os problemas reais onde análises críticas e sugestões de engenharia têm maior valor:

1. **Testes de integração da API dependem de `data/` local (gitignored):**
   - `apps/api/tests/test_api_v1.py`, `apps/api/tests/test_fase5_api.py`, `test_endpoint_boletim_semanal` e `apps/coleta/tests/test_postgres_persistence.py` carregam ou consultam dados de `data/raw/` / `data/pgdata/`.
   - Por isso, o CI em `.github/workflows/ci.yml` hoje roda apenas os testes unitários/offline e um smoke test de importação da API. Criar uma **fixture/seed PostgreSQL sintética completa** para rodar todos os endpoints da API (e o Playwright E2E) dentro do GitHub Actions é uma melhoria técnica imediata de alto impacto.
2. **Passivo histórico pré-2026 (SIGEP → CENTI) e Lote 3 do Nexlegis (`2020–2024`):**
   - O pedido formal via LAI ([`docs/fase-0/pedido-lai-final.md`](fase-0/pedido-lai-final.md)) ainda precisa ser protocolado pelo responsável humano.
   - O Lote 3 do Nexlegis (`2020–2024`) aguarda autorização explícita por lote.
3. **OCR em lote das `407` leis municipais:**
   - Metadados e URLs canônicas das `407` leis já estão persistidos, e `ocr.py` já está pronto e testado, mas a extração real dos PDFs escaneados depende da instalação do binário Tesseract (`por`) e da execução em lote respeitando a expiração de 40 min dos links S3 e `Crawl-Delay >= 5s`.
4. **Acoplamento residual de configurações de Inhumas em Python (para a Fase 6):**
   - O esquema SQL já é multi-município (`municipio_id`), mas `VEREADORES_MESTRE_INHUMAS` (`entidades.py`), `_BAIRROS_INHUMAS_GO` (`bairros.py`) e `MUNICIPIOS_PARES_POR_MUNICIPIO` (`siconfi/collector.py`) ainda vivem em estruturas Python em vez de pacotes declarativos (YAML/JSON) por município.
5. **Ausência de infraestrutura de produção e monitoramento externo:**
   - Ainda não há `Dockerfile` / `docker-compose.yml`, estratégia de deploy (VPS / Fly.io + Postgres gerenciado), rotina automatizada de backup, nem alerta proativo de quebra de layout (`LayoutQuebradoError` / alteração de contagem) em execução agendada Linux/cloud.
6. **Validação humana pendente antes do lançamento público amplo:**
   - Teste presencial com 8–10 moradores de Inhumas ([`docs/fase-3/roteiro-teste-usuarios-mvp.md`](fase-3/roteiro-teste-usuarios-mvp.md)), revisão jurídica sobre exibição nominal de pessoas e aquisição/configuração de `cerradoaberto.org.br`.
7. **Série temporal e cruzamentos ainda não explorados:**
   - Licitações (`licitacoes_cnt`) e Contratos (`contratos_cnt`) já foram mapeados na Fase 0 (`ADR-003`), mas ainda não possuem coletor/tela completos; fontes candidatas (`TCM-GO`, `TSE`, `PNCP`, `Querido Diário`, `Receita/CNPJ`) ainda não foram integradas.

---

## 5. Trilhas de Brainstorm (Onde Queremos Novas Ideias)

Se você é um agente analisando este repositório para dar dicas e novas ideias, priorize sugestões concretas e acionáveis nas 5 trilhas abaixo:

- **Trilha A — Produto, Utilidade Real e Retenção Semanal:** como fazer um morador comum de Inhumas voltar toda semana (melhorias nos boletins WhatsApp/Instagram, alertas por bairro/tema, leitura em celular, comparativos fáceis de entender sem perder neutralidade)?
- **Trilha B — Novos Cruzamentos Cívicos:** quais cruzamentos com fontes abertas (`TCM-GO`, `TSE` filiações/doações, `PNCP`, `Receita/CNPJ`, `Querido Diário`, `Licitações × Contratos × Empenhos`, `Diárias × Presença em Sessão`, `Art. 29-A CF`) entregam mais valor com baixo risco jurídico e 100% de rigor metodológico?
- **Trilha C — Produção Barata, Resiliente e Observável:** qual a melhor arquitetura para colocar API + PostgreSQL + Web + coleta semanal + OCR no ar custando o mínimo possível (ou grátis/baixo custo em VPS única), com backups e alertas de falha silenciosa?
- **Trilha D — Replicação Multi-Município (Fase 6):** como refatorar `apps/coleta`, `apps/api` e `apps/web` para suportar uma segunda cidade goiana que também usa **Nexlegis + CENTI/NúcleoGov** em menos de 1 dia de configuração (manifestos por município, roteamento por subdomínio/slug, tema e mapa por cidade)?
- **Trilha E — Qualidade de Engenharia, Testes e OCR:** como fechar o ciclo de testes da API/E2E no GitHub Actions sem precisar versionar `data/raw/`, melhorar a taxa de acerto do OCR em PDFs digitalizados ruins e evitar regressões silenciosas nos parsers?

---

## 6. Prompt Pronto para Outro Agente (Copie e Cole)

```markdown
Leia `AGENTS.md` e `docs/BRIEFING-PARA-AGENTES.md` por inteiro antes de responder.
Trabalhe apenas em modo de análise/planejamento (não edite código ainda) e respeite integralmente os 7 princípios inegociáveis (proveniência, bruto imutável, neutralidade editorial sem veredictos, LGPD, multi-município, coleta educada e zero serviço pago sem justificativa).

Depois de inspecionar os arquivos relevantes do repositório, entregue uma análise objetiva organizada em 4 blocos:
1. **Top 5 Quick Wins Técnicos (baixo esforço, alto ganho):** melhorias imediatas em testes/CI, segurança, performance, acessibilidade ou manutenção de código.
2. **Pontos Cegos e Riscos Ocultos:** falhas potenciais em parsers, PostgreSQL/FTS, LGPD, semântica de `NULL`, rate limiting, proxy Next.js ou operação semanal que ainda não estão cobertas.
3. **5 Ideias Novas de Produto e Cruzamento de Dados:** ideias úteis para cidadãos comuns e jornalistas locais de Inhumas (explicando fonte oficial, método neutro, riscos e esforço).
4. **Desenho Sugerido para a Fase 6 (Produção + 2º Município):** arquitetura mínima para publicar em produção com baixo custo e tornar o sistema configurável para outras câmaras que usam Nexlegis e CENTI/NúcleoGov.

Para cada recomendação, cite os arquivos exatos envolvidos e seja honesto sobre limitações ou suposições.
```
