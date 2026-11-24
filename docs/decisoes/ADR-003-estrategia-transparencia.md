# ADR-003 — Estratégia de coleta da fonte `transparencia`

- **Status:** Aceito (aprovado em 12/11/2026 — ver regras complementares em ADR-005)
- **Data:** 2026-11-12
- **Contexto:**
  O reconhecimento técnico ([docs/fontes/transparencia.md](../fontes/transparencia.md)) identificou que a Câmara Municipal de Inhumas migrou em setembro de 2026 do sistema SIGEP para o portal **NúcleoGov** integrado ao ERP **CENTI** (`https://acessoainformacao.inhumas.go.leg.br/`, tenant `go/camarainhumas`).
  O portal opera com dois endpoints XHR:
  1. `POST https://acessoainformacao.inhumas.go.leg.br/api/centi` — retorna arrays JSON tipados do WCF (`ServerAppWCF.Service.Portal.Controllers.*, Wcf`) para módulos `cntdespesas`, `servidores_cnt`, `cntdiarias`, `licitacoes_cnt`, `contratos_cnt`.
  2. `POST https://acessoainformacao.inhumas.go.leg.br/api` — retorna JSON multiplexado para módulos nativos NúcleoGov como Receitas/Duodécimo (`sgduodecimo`) e Cotas Parlamentares (`sggastosparlamentares`).
  Adicionalmente, o endpoint `GET /api/centi?acao=exportarDespesas&...` apresentou alta latência/timeout durante o reconhecimento, enquanto as chamadas `POST` paginadas respondem em `< 1,5s`.
- **Decisão:**
  1. **Coletar via requisições HTTP `POST` diretas (`httpx`) para `/api/centi` e `/api`**, paginando de 50 em 50 registros e respeitando `Crawl-Delay >= 5s` (definido no `robots.txt` do domínio principal `inhumas.go.leg.br`).
  2. **Mascaramento estrito na ingestão (LGPD):** Embora a Folha (`servidores_cnt`) já não exponha CPF e o módulo de Despesas entregue CPFs parcialmente mascarados (`050.xxx.xxx-63`), o coletor aplicará sanitização imediata para o padrão `***.***.***-**` em qualquer pessoa física antes de persistir na camada tratada.
  3. **Composição do "Custo da Estrutura do Mandato" (ADR-005):** Como a Câmara publicou declaração oficial de inexistência de Cotas Parlamentares / Verba Indenizatória (`2020–2026`), o indicador oficial será denominado **Custo da Estrutura do Mandato** e calculado pela fórmula:
     $$\text{Custo da Estrutura do Mandato} = \text{Subsídio Bruto} + \text{Folha Bruta do Gabinete} + \text{Diárias Atribuíveis}$$
     - Exibir sempre o texto oficial: *"Cota parlamentar (CEAP): inexistente, conforme declaração oficial da Câmara Municipal de Inhumas."* (referenciando o período declarado 2020–2026).
     - Respeitar a vigência histórica de lotação, evitar duplicidade, exigir identificação verificável para diárias, não confundir folha bruta com custo patronal total e jamais transformar dados ausentes em zero.
  4. **Pedido formal via LAI para o passivo histórico pré-2026:** Protocolar pedido via LAI ([docs/fase-0/pedido-lai-rascunho.md](../fase-0/pedido-lai-rascunho.md)) para obter as bases de 2021–2025 do sistema legado SIGEP que não tiverem sido migradas integralmente para o CENTI.
- **Consequências:**
  - **Positivas:** Sem dependência de navegador headless para a coleta rotineira; conciliação direta entre vereadores e assessores pela coluna `Lotação`.
  - **Negativas / Atenção:** Necessidade de monitorar mudanças nas chaves dinâmicas do endpoint `POST /api` através de testes de contrato sobre as fixtures.
