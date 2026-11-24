# Cerrado Aberto — Plataforma Cidadã Independente de Transparência Legislativa (Inhumas/GO)

> **Declaração de independência:** O **Cerrado Aberto** (`cerradoaberto.org.br`) é uma iniciativa cidadã independente de monitoramento, tradução e interpretação de dados públicos do Poder Legislativo municipal de Inhumas (GO), **sem qualquer vínculo institucional, contratual ou político-partidário com a Câmara Municipal ou com agentes públicos**.

> **Para Agentes de IA e Revisores Técnicos (leia em 2 passos):**
> 1. Leia [`AGENTS.md`](AGENTS.md) para entender a missão, os princípios inegociáveis (proveniência, neutralidade editorial, LGPD, multi-município) e a regra de fase ativa.
> 2. Leia [`docs/BRIEFING-PARA-AGENTES.md`](docs/BRIEFING-PARA-AGENTES.md) — um mapa completo do código, resumo das 8 ADRs, lacunas técnicas atuais, trilhas de brainstorm e um **prompt pronto** para gerar críticas técnicas e ideias novas com profundidade.

---

## Estado Atual do Projeto

As **Fases 0 a 5** foram implementadas e validadas ponta a ponta em homologação local em **24/11/2026**. A **Fase 6 (Replicação e Publicação em Produção)** aguarda aprovação explícita do responsável.

| Fase | Escopo | Estado | Evidência / Documento |
|---|---|---|---|
| **Fase 0** | Descoberta e validação das fontes | Concluída e aprovada (`12/11/2026`) | [`docs/03-fontes-de-dados.md`](docs/03-fontes-de-dados.md) |
| **Fase 1** | Fundação de dados — Nexlegis (`2025–2026`) + PostgreSQL 16 + API v1 | Concluída para 2025–2026 (`Lote 3 2020–2024` pendente) | [`docs/fase-1/relatorio-cobertura-e-qualidade-nexlegis.md`](docs/fase-1/relatorio-cobertura-e-qualidade-nexlegis.md) |
| **Fase 2** | Portal da Transparência CENTI/NúcleoGov (`2026`) + Custo do Mandato | Concluída para 2026 (`12/11/2026`) | [`docs/fase-2/relatorio-transparencia-e-custo-mandato-2026.md`](docs/fase-2/relatorio-transparencia-e-custo-mandato-2026.md) |
| **Fase 3** | MVP Público (Next.js + Tailwind + Observable Plot + WCAG AA) | Homologada (`18/11/2026`; teste presencial pendente) | [`docs/fase-3/relatorio-mvp-homologacao.md`](docs/fase-3/relatorio-mvp-homologacao.md) |
| **Fase 4** | Coleta semanal incremental, resumos automáticos e central `/boletins` | Validada em homologação (`18/11/2026`) | [`docs/fase-4/relatorio-fase-4.md`](docs/fase-4/relatorio-fase-4.md) |
| **Fase 5** | Busca FTS, Mapa por Bairros, Legislação, Comparativo SICONFI e `/dados-abertos` | Validada em homologação (`24/11/2026`) | [`docs/fase-5/relatorio-fase-5.md`](docs/fase-5/relatorio-fase-5.md) |
| **Fase 6** | Replicação multi-município e publicação em produção | Aguardando aprovação | [`docs/04-roadmap.md`](docs/04-roadmap.md) |

### Números verificados na base de homologação (`24/11/2026`)
- **Nexlegis (`2025–2026` + incremental semanal):** `32` vereadores cadastrados (`16` na legislatura `2025–2028`), `134` sessões plenárias, `1.311` proposições (`1.692` itens de pauta), `1.613` votações e `7.990+` votos nominais.
- **Portal da Transparência CENTI/NúcleoGov (`2026`):** `939` registros na folha de pagamento (`01/2026` a `10/2026`, zero CPF completo), `360` empenhos de despesa (`R$ 8.873.608,80` pagos), `102` fornecedores, `14` diárias no Elemento 14 (`R$ 6.600,00`), `22` lançamentos de duodécimo (`R$ 9.111.797,89` recebidos e `R$ 99.000,00` devolvidos) e Declaração Oficial de inexistência de cota parlamentar/CEAP (`2020–2026`).
- **Legislação Municipal (`1990–2026`):** `407` leis municipais catalogadas com URL canônica permanente e pipeline híbrido `pdfplumber` + Tesseract OCR (`por`).
- **Mapa Territorial por Bairros:** `52` bairros, setores e distritos de Inhumas mapeados (`231` proposições com menção verificável na ementa / `291` vínculos + `943` proposições gerais sem localidade na ementa exibidas de forma transparente).
- **Comparativo SICONFI / Secretaria do Tesouro Nacional (`2024` e `2025`):** Função `01 - Legislativa` (`DCA-Anexo I-E`) comparando Inhumas com `7` municípios pares de Goiás (`Morrinhos`, `Quirinópolis`, `Itaberaí`, `Jaraguá`, `Porangatu`, `Uruaçu` e `Cristalina`).

---

## Arquitetura em Camadas

```mermaid
flowchart LR
  subgraph Fontes["Fontes Oficiais Públicas"]
    F1["Nexlegis REST API"]
    F2["Transparência CENTI / NúcleoGov"]
    F3["Legislação Municipal (NúcleoGov + PDFs)"]
    F4["SICONFI / Tesouro Nacional"]
  end

  subgraph Coleta["apps/coleta (Python 3.12 + httpx + pdfplumber/OCR)"]
    C1["Fetch educado + Sanitização LGPD"]
    C2["Parse + Resolução de Entidades"]
    C3["Load idempotente + Qualidade"]
  end

  Raw[("data/raw/ imutável\nSHA-256 + Manifestos\n(gitignored)")]
  DB[("PostgreSQL 16\nMigrações 0001..0003\nFTS portuguese + GIN")]
  API["apps/api\nFastAPI v1 (21 endpoints GET)\nSomente leitura + Rate Limit + LGPD"]
  Web["apps/web\nNext.js 16 + Tailwind CSS 4\nObservable Plot + Canvas 2D (23 rotas)"]

  Fontes --> C1
  C1 --> Raw
  Raw --> C2
  C2 --> C3
  C3 --> DB
  DB --> API
  API --> Web
```

Para os detalhes do modelo de dados, escolhas técnicas e desafios conhecidos, veja [`docs/02-arquitetura.md`](docs/02-arquitetura.md) e [`docs/decisoes/`](docs/decisoes/).

---

## Capturas do MVP (Homologação — Fase 5)

| Página Inicial (3 perguntas + busca) | Perfil do Vereador + Custo do Mandato |
|---|---|
| ![Home do Cerrado Aberto](docs/fase-5/capturas/01-home-desktop.png) | ![Perfil do Vereador](docs/fase-5/capturas/03-vereador-perfil-desktop.png) |

| Despesas Públicas e Duodécimo | Mapa de Indicações por Bairro |
|---|---|
| ![Despesas Públicas](docs/fase-5/capturas/05-despesas-desktop.png) | ![Mapa por Bairros](docs/fase-5/capturas/15-bairros-desktop.png) |

| Comparativo SICONFI (8 cidades GO) | Cartão Instagram (`1080×1350`) em `/boletins` |
|---|---|
| ![Comparativo SICONFI](docs/fase-5/capturas/18-comparativo-desktop.png) | ![Cartão Instagram Slide 1](docs/fase-5/capturas/card-instagram-slide-1-1080x1350.png) |

---

## Rotas Web e Endpoints da API Pública

### Aplicação Web (`apps/web` — 23 rotas no build Next.js)
- **Cidadão e Busca:** `/` (Home com 3 perguntas + busca rápida), `/busca` (Full-Text Search unificado), `/bairros` (mapa vetorial SVG local + tabela + CSV), `/boletins` (alertas WhatsApp `<= 400` chars + gerador Canvas 2D de cards PNG para `@cerradoaberto`).
- **Legislativo:** `/vereadores`, `/vereadores/[id]` (presenças, proposições, votos e custo da estrutura do mandato), `/sessoes`, `/sessoes/[id]`, `/materias/[id]`, `/legislacao`, `/legislacao/[id]`.
- **Finanças Públicas e Contexto:** `/custo-mandato`, `/despesas` (`/dinheiro` redireciona para `/despesas`), `/diarias`, `/comparativo`.
- **Transparência, Metodologia e Dados Abertos:** `/dados-abertos`, `/como-calculamos`, `/cobertura-e-limitacoes`, `/sobre`, `/correcoes`, além do proxy somente leitura `/api/v1/[...path]`.

### API Pública Somente Leitura (`apps/api` — 21 endpoints `GET`)
Documentação interativa disponível em `/docs` (Swagger/OpenAPI) quando a API estiver rodando:
- **Saúde e Metadados:** `GET /api/v1/health`
- **Legislativo:** `GET /api/v1/vereadores`, `GET /api/v1/vereadores/{id}`, `GET /api/v1/sessoes`, `GET /api/v1/sessoes/{id}`, `GET /api/v1/materias`, `GET /api/v1/materias/{id}`
- **Transparência:** `GET /api/v1/transparencia/custo-mandato`, `GET /api/v1/transparencia/folha`, `GET /api/v1/transparencia/despesas`, `GET /api/v1/transparencia/despesas/resumo`, `GET /api/v1/transparencia/diarias`, `GET /api/v1/transparencia/duodecimo`, `GET /api/v1/transparencia/declaracoes`
- **Boletins, Busca e Aprofundamento:** `GET /api/v1/boletins/resumo-semanal`, `GET /api/v1/busca`, `GET /api/v1/bairros`, `GET /api/v1/bairros/{slug}`, `GET /api/v1/legislacao`, `GET /api/v1/legislacao/{id}`, `GET /api/v1/comparativo`

---

## Estrutura do Repositório

```text
AGENTS.md / CLAUDE.md          # Regras mestras para agentes e contribuidores
README.md                      # Visão geral, rotas e guia de execução local
CONTRIBUTING.md / SECURITY.md  # Guia de contribuição, LGPD e reporte de segurança
apps/
  coleta/                      # Coletores Python (Nexlegis, Transparência, Legislação, SICONFI) + fixtures reais + pytest
  api/                         # FastAPI v1 somente leitura (routers, rate limit, resumos, segurança LGPD) + pytest
  web/                         # Frontend Next.js 16 + Tailwind 4 + Observable Plot + testes E2E Playwright/axe-core
db/migrations/                 # Migrações SQL idempotentes (0001, 0002, 0003) para PostgreSQL 16
docs/                          # Produto, arquitetura, fontes, roadmap, ética, glossário, ADRs 001–008, relatórios e BRIEFING-PARA-AGENTES.md
scripts/                       # Atualização semanal (.ps1), coletor de legislação (.mjs), validador de docs (.mjs) e launcher Windows (.cs)
skills/                        # 6 skills de domínio (fontes, scrapers, normalização, qualidade, texto-cidadao, frontend-cidadao)
.agents/                       # Agentes revisores, regras de estilo/segurança e workflows reutilizáveis
prompts/                       # Prompts históricos usados nas fases anteriores
.github/workflows/             # Pipeline de CI (docs, coleta, api, web)
data/                          # Brutos SHA-256 e banco local pgserver (gitignored; não versionado)
```

---

## Como Rodar Localmente e Testar

### Pré-requisitos
- **Python 3.12** + [`uv`](https://docs.astral.sh/uv/)
- **Node.js 20+** e `npm`
- **PostgreSQL 16** (opcional externamente via `DATABASE_URL`; se não informado, a API e os coletores sobem automaticamente um cluster portátil via `pgserver` em `data/pgdata`)
- *(Opcional para OCR em lote de PDFs escaneados)* **Tesseract OCR** com pacote de idioma `por`

> **Nota sobre dados locais (`data/`):** os arquivos brutos (`data/raw/`) e o cluster local (`data/pgdata/`) são ignorados no Git por tamanho e governança (`AGENTS.md`). Após clonar o repositório, todos os testes offline baseados em fixtures reais funcionam imediatamente. Para navegar no site com dados reais populados, execute primeiro o pipeline de carga/coleta respeitando os `Crawl-Delay` das fontes ou restaure um snapshot PostgreSQL 16 aplicando [`db/migrations/`](db/migrations/).

### 1. Instalar dependências
```bash
uv sync --directory apps/coleta --extra dev
uv sync --directory apps/api --extra dev
npm --prefix apps/web ci
```

### 2. Subir a API FastAPI e o Frontend Next.js
Em um terminal, inicie a API (porta `8000`):
```bash
# Opcional: export DATABASE_URL="postgresql://usuario:senha@localhost:5432/cerrado_aberto"
uv run --directory apps/api uvicorn cerrado_aberto_api.main:app --host 127.0.0.1 --port 8000
```

Em outro terminal, configure o arquivo `.env.local` dentro de `apps/web/` a partir de [`apps/web/.env.example`](apps/web/.env.example) (`CERRADO_API_URL=http://127.0.0.1:8000`) e inicie o frontend (porta `3000`):
```bash
npm --prefix apps/web run dev
```

Acesse:
- Site: `http://127.0.0.1:3000`
- Documentação OpenAPI: `http://127.0.0.1:8000/docs`

### 3. Atualização incremental semanal (Windows)
```powershell
.\scripts\atualizar-semana.ps1 -MunicipioId inhumas-go -Ano 2026
```

### 4. Executar linters, testes e validação de documentação
```bash
# Integridade da documentação e links
node scripts/validate-docs.mjs

# Coleta (lint + testes unitários/fixtures offline)
uv run --directory apps/coleta ruff check src tests
uv run --directory apps/coleta pytest -q tests/test_nexlegis_pipeline.py tests/test_regras_negocio_adr005.py tests/test_nexlegis_incremental.py tests/test_transparencia_2026.py tests/test_fase5_coleta.py -k "not persistencia_bairros_e_normas and not persistencia_postgres_transparencia_2026"

# API (lint + testes unitários que independem de data/raw local)
uv run --directory apps/api ruff check src tests
uv run --directory apps/api pytest -q tests/test_boletins_e_resumos.py -k "not endpoint_boletim_semanal"

# Frontend (lint + build de produção)
npm --prefix apps/web run lint
npm --prefix apps/web run build
```

> Com `data/raw/` e `data/pgdata/` populados localmente, rode a suíte completa sem filtros (`uv run --directory apps/coleta pytest -q`, `uv run --directory apps/api pytest -q` e `npm --prefix apps/web run test:e2e`).

---

## Ética, Privacidade (LGPD) e Pendências Humanas

- **Ética editorial:** fatos verificáveis com fonte e data em tudo; zero acusação ou adjetivo avaliativo; preservação estrita de `NULL` quando não há publicação oficial (`0 != NULL`). Ver [`docs/05-etica-legal-editorial.md`](docs/05-etica-legal-editorial.md).
- **Privacidade (LGPD):** nenhum CPF completo é armazenado ou exibido; qualquer CPF encontrado na origem é mascarado para `***.***.***-**` antes da persistência. Ver [`SECURITY.md`](SECURITY.md).
- **Canal de correção e direito de resposta:** página `/correcoes` e e-mail `firstonetrillion@gmail.com` (endereço provisório de homologação definido na `ADR-006`).
- **Pendências humanas fora do código:**
  - [ ] Protocolar pessoalmente o pedido via LAI ([`docs/fase-0/pedido-lai-final.md`](docs/fase-0/pedido-lai-final.md)) no e-SIC para o histórico pré-2026 (SIGEP)
  - [ ] Conduzir o teste presencial com moradores em Inhumas ([`docs/fase-3/roteiro-teste-usuarios-mvp.md`](docs/fase-3/roteiro-teste-usuarios-mvp.md))
  - [ ] Validação jurídica formal antes do lançamento público amplo
  - [ ] Avaliar abertura da **Fase 6** (definição de licença open-source, empacotamento multi-município e deploy em produção)

## Licença

**Sem licença open-source definida por enquanto** — a escolha e publicação da licença definitiva fazem parte da **Fase 6 (Replicação)**. Até definição formal pelo responsável do projeto, todos os direitos sobre o código-fonte permanecem reservados, sendo o repositório compartilhado para análise técnica, auditoria e sugestões de arquitetura.
