# Relatório da Fase 3 — MVP Público do Cerrado Aberto (Ambiente de Homologação)

> **Projeto:** Cerrado Aberto (`cerradoaberto.org.br`) — Plataforma Cidadã Independente de Transparência Legislativa  
> **Escopo:** MVP público em ambiente de homologação local (`apps/web` + `apps/api` + PostgreSQL 16)  
> **Data:** 18/11/2026 (atualizado com Etapas 1–7 concluídas, favorecidos PJ, CSV, capturas e roteiro de usuários)

---

## 1. Estrutura do Frontend (`apps/web`)

- **Framework e bibliotecas:** Next.js `16.4.6` (App Router), React `19.3.0`, TypeScript, Tailwind CSS `4.3.3`, `@observablehq/plot`, `lucide-react`.
- **Testes automatizados:** `@playwright/test` + `@axe-core/playwright`.
- **Organização de arquivos:**
  - `apps/web/src/app/layout.tsx` e `globals.css`: identidade visual própria inspirada no cerrado goiano (off-white quente `#FAF7F2`, verde-cerrado `#1F4E3D`, laterita `#B44B2A`, ipê `#D99B16`, modo escuro automático, tipografia `Fraunces` + `Inter` + `JetBrains Mono`, numerais tabulares e link de salto para acessibilidade).
  - `apps/web/src/app/api/v1/[...path]/route.ts`: proxy **somente leitura (`GET`)** para a API FastAPI v1, evitando CORS no navegador e bloqueando qualquer operação de escrita.
  - `apps/web/src/lib/`: `types.ts` (contratos tipados alinhados ao OpenAPI), `api.ts` (cliente com tratamento de erro e `safeFetchApi`), `format.ts` (formatação PT-BR sem converter `null` em `0` e mascaramento LGPD), `csv.ts` (exportação CSV UTF-8 com BOM preservando `"NULL"` para valores ausentes).
  - `apps/web/src/components/`: `SiteHeader.tsx`, `SiteFooter.tsx`, `DadoComFonte.tsx`, `EstadoAusente.tsx`, `GlossarioTooltip.tsx`, `AvatarVereador.tsx`, `PlotChart.tsx` (gráficos Observable Plot com botões "Ver dados em tabela" e "Baixar CSV", `role="region"` e `tabIndex={0}` para rolagem por teclado), `ProvenienciaBox.tsx`.

---

## 2. Telas Implementadas e Integração com a API v1

| Tela / Rota | Endpoints FastAPI v1 consumidos | Regras atendidas |
|---|---|---|
| **Página inicial** (`/`) | `/api/v1/health`, `/api/v1/vereadores`, `/api/v1/transparencia/despesas/resumo`, `/api/v1/transparencia/duodecimo`, `/api/v1/sessoes` | Apresentação independente, indicadores gerais (16 vereadores atuais, 133 sessões, 1.295 proposições, despesas 2026 por estágio, duodécimo), data da última coleta por fonte e lacunas históricas. |
| **Vereadores** (`/vereadores` e `/vereadores/[id]`) | `/api/v1/vereadores`, `/api/v1/vereadores/{id}` | Ordem alfabética, tratamento uniforme, presenças/ausências separando justificadas e licenças, proposições com exclusão de atas/atos, votos nominais e Custo da Estrutura do Mandato (preservando `NULL` em `PRESIDENCIA` e meses `11–12/2026`). |
| **Custo da Estrutura do Mandato** (`/custo-mandato`) | `/api/v1/transparencia/custo-mandato`, `/api/v1/transparencia/declaracoes` | Subsídio bruto, folha do gabinete, diárias atribuíveis e total apenas quando calculável; gráfico empilhado + tabela; nota oficial de inexistência da CEAP (2020–2026). |
| **Despesas públicas** (`/despesas` e `/dinheiro`) | `/api/v1/transparencia/despesas/resumo`, `/api/v1/transparencia/despesas`, `/api/v1/transparencia/duodecimo` | Empenho bruto (`R$ 11.122.741,47`), anulações (`R$ 1.244.416,61`), empenho líquido (`R$ 9.878.324,86`), liquidado (`R$ 8.873.608,80`) e pago (`R$ 8.873.608,80`); duodécimo (`R$ 9.111.797,89` recebidos e `R$ 99.000,00` devolvidos, com detalhamento dos 22 lançamentos em `<details>` e CSV); gráficos e tabelas por elemento de despesa e por **favorecido Pessoa Jurídica (78 fornecedores PJ)**; exportação CSV a um clique; filtros por período, fornecedor, elemento, diárias e busca textual. |
| **Diárias** (`/diarias`) | `/api/v1/transparencia/diarias`, `/api/v1/transparencia/declaracoes` | 14 registros do Elemento 14 (`R$ 6.600,00`, sendo `R$ 1.600,00` a 3 vereadores em jan–fev/2026), beneficiário, valor, data, referência ao empenho e explicação objetiva da diferença com `cntdiarias`. |
| **Sessões, Votações e Matérias** (`/sessoes`, `/sessoes/[id]`, `/materias/[id]`) | `/api/v1/sessoes`, `/api/v1/sessoes/{id}`, `/api/v1/materias/{id}` | Filtros por ano/data/texto, pautas, lista de presença, placares e votos nominais, tramitações e links para documentos oficiais. |
| **Metodologia** (`/como-calculamos`) | `/api/v1/health`, `/api/v1/transparencia/declaracoes` | Fórmulas, indicador per capita com população oficial IBGE 2026 (`54.133` hab.), critérios de exclusão de atas, proteção LGPD e declarações oficiais. |
| **Cobertura e Limitações** (`/cobertura-e-limitacoes`) | `/api/v1/health`, `/api/v1/transparencia/declaracoes` | Escopo temporal coberto por fonte, lacunas históricas documentadas (`SIGEP 2017–2025`, `Lote 3 2020–2024`, `PRESIDENCIA`, `11–12/2026`) e declarações oficiais. |
| **Canal de Correção** (`/correcoes`) | — | Canal público de retificação e direito de esclarecimento (`firstonetrillion@gmail.com` no beta fechado) e tabela pública datada de correções realizadas. |
| **Sobre** (`/sobre`) | — | Declaração obrigatória de independência, missão, fontes monitoradas e princípios inegociáveis. |

### Ajustes realizados na API v1 (`apps/api`)
- Adicionado `ultima_coleta_por_fonte` em `GET /api/v1/health`.
- Adicionados filtros `data_inicio`, `data_fim`, `fornecedor_id` e `elemento_despesa` em `GET /api/v1/transparencia/despesas`.
- Criado `GET /api/v1/transparencia/despesas/resumo` para calcular somatórios de estágios, totais por elemento e somatórios completos por favorecido (`FavorecidoDespesaOut`, incluindo `documento_favorecido` e os 6 estágios/saldos contábeis) diretamente no PostgreSQL (sem duplicar regras no frontend).
- Adicionado `threading.Lock()` e preparação resiliente do cluster local PostgreSQL 16 no Windows (`_preparar_pgdata_windows` + recuperação de `TimeoutExpired`) em `obter_uri_banco()` (`apps/api/src/cerrado_aberto_api/db.py`).

---

## 3. Segurança, Privacidade (LGPD) e Acessibilidade

- **Zero CPF completo:** auditado automaticamente por regex (`\b\d{3}\.\d{3}\.\d{3}-\d{2}\b`) em todas as páginas renderizadas no Playwright e em `apps/api/tests/test_api_v1.py`.
- **Somente leitura:** o proxy `/api/v1/[...path]` expõe apenas `GET` e a API FastAPI bloqueia `POST`/`PUT`/`PATCH`/`DELETE` (`405`).
- **Sem rastreamento de terceiros:** fontes carregadas localmente via `next/font/google` no build; zero cookies de rastreamento ou analytics externos.
- **Acessibilidade (WCAG 2.0/2.1 A e AA):** 0 violações graves ou críticas no `@axe-core/playwright` em todas as rotas testadas (desktop `1280×800` e mobile `390×844`), tabelas com `tabIndex={0}` para rolagem por teclado e alternativa em tabela HTML para todos os gráficos.
- **Neutralidade editorial:** checagem automatizada de vocabulário proibido (`fraude`, `desvio`, `esquema`, `irregular`, `suspeito`, `escândalo`, `absurdo`, `farra`, `mamata`) em todas as telas.

---

## 4. Como executar localmente e configurar o ambiente de homologação

### Pré-requisitos
- Python 3.12 + `uv`
- Node.js 22+ + `npm`
- Banco PostgreSQL 16 local já populado em `data/pgdata` (ou variável `DATABASE_URL` apontando para PostgreSQL 16 em homologação).

### Passo 1 — Subir a API FastAPI v1 (porta `8000`)
```powershell
# Opcional em homologação: definir DATABASE_URL=postgresql://usuario:senha@host:5432/cerrado_aberto
uv run --directory apps/api uvicorn cerrado_aberto_api.main:app --host 127.0.0.1 --port 8000
```

### Passo 2 — Configurar e subir o frontend Next.js (porta `3000`)
```powershell
# Opcional: configurar CERRADO_API_URL no .env de apps/web (padrão: http://127.0.0.1:8000)
npm --prefix apps/web install
npm --prefix apps/web run build
npm --prefix apps/web run start -- -H 127.0.0.1 -p 3000
```
Acessar no navegador: `http://127.0.0.1:3000` (e OpenAPI da API em `http://127.0.0.1:8000/docs`).

### Passo 3 — Executar testes e linters
```powershell
uv run --directory apps/api ruff check src tests
uv run --directory apps/api pytest -q
npm --prefix apps/web run lint
npm --prefix apps/web run test:e2e
```

---

## 5. Capturas de Tela e Roteiro para Teste com Usuários (Etapas 7 e 8)

- **Capturas de tela geradas (`docs/fase-3/capturas/`):** 19 capturas de página inteira (desktop `1280×800` e mobile `390×844`) cobrindo `/`, `/vereadores`, `/vereadores/[id]`, `/custo-mandato`, `/despesas`, `/diarias`, `/sessoes`, `/sessoes/[id]`, `/como-calculamos`, `/correcoes`, `/cobertura-e-limitacoes` e `/sobre`.
- **Roteiro prático de teste com usuários reais de Inhumas:** documentado em `docs/fase-3/roteiro-teste-usuarios-mvp.md` (5 tarefas práticas guiadas conectadas às rotas e números reais do MVP, em conjunto com `docs/fase-0/roteiro-entrevistas.md`).

---

## 6. Pendências identificadas para conclusão do aceite da Fase 3

1. ~~**Canal de correção (`/correcoes`):**~~ **Concluído em 18/11/2026 (ADR-006 / D3)** com ativação da rota `/correcoes` e e-mail provisório `firstonetrillion@gmail.com` para o beta fechado.
2. **Teste presencial com usuários reais de Inhumas (Etapa 8):** conduzir validação com os roteiros em `docs/fase-3/roteiro-teste-usuarios-mvp.md` e `docs/fase-0/roteiro-entrevistas.md` antes de qualquer publicação aberta.
3. **Expansão histórica (fora desta autorização):** protocolo do pedido LAI (SIGEP 2017–2025) e autorização do Lote 3 do Nexlegis (2020–2024).
