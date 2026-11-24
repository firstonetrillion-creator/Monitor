# Ficha — `transparencia` (Portal da Transparência / Dados Abertos — NúcleoGov + CENTI)

- **Data do reconhecimento inicial (Fase 0):** 2026-11-12 (`v0.1.0`)
- **Data do reconhecimento aprofundado (Fase 2 — Etapa 1):** 2026-11-12 (`v0.2.0`)
- **Quem (agente):** Antigravity (Co-fundador Técnico) + Subagente `browser` (`37152313` e `320e385b`)
- **Versão:** `v0.2.0`

---

## 1. Acesso e Proteção de Borda (Cloudflare WAF)

- **URL informada inicialmente:** `http://go.leg.br` (incompleta — é o domínio de topo do Legislativo em Goiás).
- **URLs reais descobertas e verificadas:**
  - **Portal Institucional:** `https://inhumas.go.leg.br/` (WordPress)
  - **Hub Indexador de Transparência (78 links):** `https://inhumas.go.leg.br/transparencia/`
  - **Portal da Transparência / Acesso à Informação (base):** `https://acessoainformacao.inhumas.go.leg.br/` (plataforma **NúcleoGov** `v5.4.169` integrada ao ERP **CENTI**, tenant `go/camarainhumas`, após migração do sistema legado SIGEP comunicada em `02/09/2026` em `https://inhumas.go.leg.br/comunicado-migracao/`).
  - **Módulos principais em escopo na Fase 2 (2026):**
    - Folha de Pagamento / Subsídios / Lotação: `https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/servidores_cnt`
    - Despesas (Empenhos / Liquidações / Pagamentos): `https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/cntdespesas`
    - Diárias: `https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/cntdiarias`
    - Declaração Oficial de Não Concessão de Diárias: `https://acessoainformacao.inhumas.go.leg.br/cidadao/p/declaracao/16` (linkada via `/informacao/mp/id=23`)
    - Tabela de Valores de Diárias: `https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/tabeladiarias`
    - Receitas / Duodécimo: `https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/sgduodecimo`
    - Cotas e Gastos Parlamentares (Declaração CEAP): `https://acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/sggastosparlamentares`
    - Licitações: `https://acessoainformacao.inhumas.go.leg.br/cidadao/informacao/licitacoes_cnt`
    - Contratos: `https://acessoainformacao.inhumas.go.leg.br/cidadao/informacao/contratos_cnt`
- **Comportamento de borda (Cloudflare / Nginx WAF) e CAPTCHA:**
  - Requisições `GET` diretas com cliente HTTP genérico sem contexto de sessão/cabeçalhos XHR para `acessoainformacao.inhumas.go.leg.br` ou `static.nucleogov.com.br` recebem `HTTP 403 Forbidden` na borda (`server: cloudflare`).
  - No contexto de navegador padrão (ou Playwright em sessão legítima da página com `X-Requested-With: XMLHttpRequest` e `Origin`/`Referer` da própria página), todas as chamadas `POST /api` e `POST /api/centi` de listagem e detalhes respondem `HTTP 200 OK` em `400ms–1.500ms`, **sem exigir login nem CAPTCHA**.
  - **Único ponto com CAPTCHA (`acao=new_captcha`):** o botão **"Arquivos"** dentro do modal de um empenho dispara `POST /api/centi` (`acao=new_captcha`) exigindo resolução humana de CAPTCHA de imagem para download de anexos/comprovantes. **Regra inegociável:** o coletor jamais chamará `acao=new_captcha` nem tentará contornar esse CAPTCHA; coletará exclusivamente os metadados estruturados públicos de `acao=empenhos`.
- **`robots.txt` e taxa de coleta:**
  - `https://acessoainformacao.inhumas.go.leg.br/robots.txt` retorna `HTTP 200` vazio (`0 bytes`).
  - `https://inhumas.go.leg.br/robots.txt` define `Crawl-Delay: 5`.
  - **Regra operacional:** `Crawl-Delay >= 5.0s` obrigatório entre requisições, sem paralelismo (`concorrência = 1`).

---

## 2. Mecânica e Contratos Exatos de Requisição (`POST /api` e `POST /api/centi`)

O reconhecimento técnico do código-fonte cliente (`request.js`, `centi.js`, `servidores_cnt.js` e `despesas_centi.js`) revelou que o portal divide as consultas em **dois canais POST distintos** (`Content-Type: application/x-www-form-urlencoded; charset=UTF-8`):

### Canal A — API Multiplexada NúcleoGov (`POST https://acessoainformacao.inhumas.go.leg.br/api`)
Gerenciada por `res/js/nucleo/request/request.js`. Recebe `multi_request=true&params=<JSON>` onde cada chave é um identificador de chamada (`"<indice>-<id>"`) contendo `"acao": "<controlador>/<metodo>"`.

#### A.1. Folha de Pagamento, Subsídios e Lotação (`servidores_cnt/listar`)
> **Achado crítico da Fase 2:** Ao contrário do que o sufixo `_cnt` na URL sugere, a folha de pagamento **não** usa `/api/centi`; ela consulta `POST /api` com o controlador `servidores_cnt/listar` e **já retorna na própria listagem todos os 28 atributos de cada vínculo** (incluindo `matricula`, `lotacao`, `cargo`, `tipo_admissao`, `data_admissao`, `data_exoneracao`, `decreto`, `carga_horaria`, `salario_base`, `total_proventos`, `total_descontos` e `total_liquido`).

- **Payload de requisição (`postData` verbatim):**
  ```http
  multi_request=true&params={"0-listar":{"acao":"servidores_cnt/listar","ano":"2026","mes":"10","orgao":"2","limit":"0, 50"}}
  ```
  - Filtros suportados em `filtro`: `ano` (`2011`–`2026`), `mes` (`"01"`–`"12"`), `orgao` (`"2"` = Câmara Municipal de Inhumas), `txtbusca` (matrícula ou nome), `cargo`, `situacao`, `tipo_folha`, e paginação SQL `limit: "<offset>, <size>"` (ex.: `"0, 50"`, `"50, 50"`).
- **Estrutura JSON de resposta (`result["0-listar"]`):**
  - `total`: inteiro com o total de vínculos na competência (ex.: `88` em `Outubro/2026`).
  - `ultimoMes`: `{"ano": "2026", "mes": "10"}` (indica a última competência fechada publicada).
  - `orgao_filtrado`: `"2"`.
  - `dados`: array de objetos de vínculo/contracheque com **28 campos** (ver Seção 3.1).
- **Chamada secundária de modal (`servidores_cnt/selecionarFolha`):**
  - Disparada ao clicar em uma linha: `params={"0-det":{"acao":"servidores_cnt/selecionarFolha","folha":{...}}}`.
  - Retorna o mesmo objeto acrescido de `eventos: []`, `lista_proventos: []`, `lista_descontos: []` (vazios porque a configuração do portal `sgservidores/getConfigs` define `hide_all_descontos: true` e não popula rubricas analíticas).
  - **Economia de tráfego:** Como `servidores_cnt/listar` já entrega 100% dos campos necessários para o **Custo da Estrutura do Mandato** (`matricula`, `nome`, `cargo`, `lotacao`, `tipo_admissao`, `data_admissao`, `data_exoneracao`, `salario_base`, `total_proventos`, `total_descontos`, `total_liquido`), não é necessário disparar 88 requisições de modal por mês — bastam **2 requisições paginadas (`limit: "0, 50"` e `"50, 50"`) por competência mensal**!

#### A.2. Receitas e Devoluções de Duodécimo (`sgduodecimo/listar`)
- **Payload de requisição (`postData` verbatim):**
  ```http
  multi_request=true&params={"0-sgduodecimo":{"acao":"sgduodecimo/listar","ano":"2026","id_orgao":"2","limit":"0, 50"}}
  ```
- **Estrutura JSON de resposta:**
  - `total`: `22` registros em 2026 (`09/01/2026` a `28/10/2026`).
  - `dados`: array com `chave` (MD5 único), `orgao` (`"2"`), `tipo` (`"1"` = Receita/Repasse Duodécimo; `"2"` = Despesa/Devolução Duodécimo), `tipo_text`, `descricao`, `data` (`YYYY-MM-DD`), `previsao_mensal` (`"911179.79"` para receitas, `null` para devoluções), `valor` (`"911179.79"`, `"10000.00"`, etc.), `beneficiario` (`null`).

#### A.3. Declaração de Cotas / Gastos Parlamentares (`sggastosparlamentares/listar`)
- **Payload de requisição (`postData` verbatim):**
  ```http
  multi_request=true&params={"0-sggastosparlamentares":{"acao":"sggastosparlamentares/listar","ano":"2026","mes":"11"}}
  ```
- **Estrutura JSON de resposta:**
  - Retorna `tabela: "declaracoes"`, `data: "01/01/2020"`, `descricao: "2026-10-22 11:37:04"`, e no campo `fornecedor` o texto oficial da declaração de inexistência de CEAP/verba indenizatória de `01/01/2020` a `22/10/2026`.

---

### Canal B — Proxy WCF CENTI (`POST https://acessoainformacao.inhumas.go.leg.br/api/centi`)
Gerenciado por `res/js/cidadao/requisicoes/centi.js`. Envia parâmetros `application/x-www-form-urlencoded` diretamente ao serviço WCF (`ServerAppWCF.Service.Portal.Controllers.*, Wcf`, tenant `go/camarainhumas`).

#### B.1. Despesas: Empenhos, Liquidações e Pagamentos (`acao=empenhos`)
- **Payload de requisição (`postData` verbatim):**
  ```http
  acao=empenhos&numero=0&processo=0&credor=&cpf_cnpj=&ano=0&valor_inicial=0&valor_final=0&id_orgao=2&id_funcao=0&licitacao=0&elemento=&sub_funcao=&dp_acao=&covid=&data_inicio=01/01/2026&data_fim=31/12/2026
  ```
  - **Nota sobre paginação e detalhe (`despesas_centi.js`):** A chamada `acao=empenhos` retorna **todos os objetos `EmpenhoItem` do intervalo `data_inicio`..`data_fim` de uma só vez** em um array JSON; a paginação (`15/20/30/40/50` linhas) e a abertura do modal `"Exibir Informações"` (`getEmpenhoById(empenhos, empenhoId)`) ocorrem 100% em memória no navegador! Para evitar payloads muito grandes ou timeouts (timeout configurado em `60_000ms` no `centi.js`), consultaremos `acao=empenhos` particionado por mês ou trimestre de 2026.

#### B.2. Diárias (`acao=diarias`)
- **Payload de requisição (`postData` verbatim):**
  ```http
  acao=diarias&id_orgao=1&data_inicio=01/01/2026&data_fim=12/11/2026
  ```
- **Retorno em 2026:** Array JSON vazio `[]` (`0` registros).
- **Cruzamento documental obrigatório:** A página `/cidadao/transparencia/cntdiarias` aponta para a **Declaração Oficial de "Não Concessão de Diárias"** (`/cidadao/p/declaracao/16`), que atesta oficialmente ausência de concessão de diárias nos períodos:
  - `01/03/2026` a `14/04/2026`
  - `01/05/2026` a `22/10/2026`
  - Para os intervalos de 2026 não cobertos explícita e formalmente pela declaração (`01/01/2026–28/02/2026`, `15/04/2026–30/04/2026` e após `22/10/2026`), verificaremos também nos empenhos (`acao=empenhos`) a existência de despesas no elemento `14 - Diárias – Pessoal Civil` (`3.3.90.14`). Caso não haja nem registro em `cntdiarias`, nem empenho em `3.3.90.14`, nem cobertura pela declaração oficial no mês específico, o componente `diarias_brutas` daquele mês deve respeitar a semântica estrita de `NULL` vs. `0,00` (ver Seção 3.3).

---

## 3. Mapeamento Detalhado de Campos e Semântica de `NULL`

### 3.1. Folha de Pagamento (`servidores_cnt/listar` — 28 campos)

| Campo no JSON (`POST /api`) | Tipo bruto | Exemplo real (2026) | Obrigatório / Preenchimento | Tratamento / Destino no PostgreSQL (`folha_pagamento`) |
|---|---|---|---|---|
| `id` | `int` | `768`, `701` | 100% | `id_origem` (identificador do registro na competência) |
| `orgao_id` | `str` | `"2"` | 100% | Código do órgão (`"2"` = Câmara Municipal) |
| `orgao` | `str` | `"CAMARA MUNICIPAL DE INHUMAS"` | 100% | Nome da unidade gestora |
| `ano` | `int` | `2026` | 100% | `ano` (`SMALLINT`) |
| `mes` | `int` | `10` | 100% | `mes` (`SMALLINT`, `1..12`) |
| `referencia` | `str` | `"Outubro/2026"` | 100% | Referência textual |
| `matricula` | `str` | `"768"`, `"701"` | 100% | `matricula` — chave de deduplicação por `(municipio_id, ano, mes, matricula, tipo_folha, id_origem)` |
| `nome` | `str` | `"ADRIANO MOREIRA DE SOUSA"` | 100% | `nome_servidor` (conciliado com `vereador_alias` quando `cargo = 'VEREADOR'`) |
| `cargo` | `str` | `"VEREADOR"`, `"CHEFE DE GABINETE DE VEREADOR CM II"`, `"ASSESSOR PARLAMENTAR CM I"` | 100% | `cargo` |
| `lotacao` | `str` | `"GAB. DO VEREADOR ADRIANO MOREIRA"`, `"GAB. VEREADOR RUBENS CARDOSO DA SILVA"`, `"PRESIDENCIA"` | 100% | `lotacao` (normalizado e vinculado a `vereador_id` quando gabinete parlamentar) |
| `tipo_admissao` | `str` | `"VEREADOR"`, `"COMISSÃO"`, `"EFETIVO"` | 100% | `vinculo` / `tipo_admissao` |
| `situacao` | `str` | `"ATIVO"` | 100% | `situacao` |
| `data_admissao` | `str` | `"01/05/2025"`, `"01/01/2025"` | ~100% (`""` → `NULL`) | `data_admissao` (`DATE`, formato origem `DD/MM/YYYY`) |
| `data_exoneracao` | `str \| null` | `null` | `null` quando ativo | `data_exoneracao` (`DATE NULL` — **nunca converter para data fictícia**) |
| `decreto` | `str` | `"085"`, `""` | Vazio para agentes políticos (`""` → `NULL`) | `decreto_nomeacao` (`TEXT NULL`) |
| `carga_horaria` | `str` | `"40,0"` | ~100% (`""` → `NULL`) | `carga_horaria` (`NUMERIC(5,1) NULL`) |
| `tipo_folha` | `str` | `"MENSAL"` | 100% | `tipo_folha` (ex.: `"MENSAL"`, `"COMPLEMENTAR"`, `"13º"`) |
| `tipo_movimentacao` | `str` | `"NORMAL"` | 100% | `tipo_movimentacao` |
| `salario_base` | `str` | `"12.796,93"`, `"4.300,00"` | ~100% (`""`/`null` → `NULL`) | `salario_base` (`NUMERIC(14,2) NULL`) |
| `total_proventos` | `str` | `"12.796,93"`, `"4.300,00"` | 100% | `remuneracao_bruta` (`NUMERIC(14,2) NULL`) — **base oficial do Subsídio Bruto e da Folha Bruta do Gabinete** |
| `total_descontos` | `str` | `"3.326,78"`, `"404,58"` | 100% | `descontos` (`NUMERIC(14,2) NULL`) |
| `total_liquido` | `str` | `"5.691,49"`, `"3.895,42"` | 100% | `remuneracao_liquida` (`NUMERIC(14,2) NULL`) |
| `outros_proventos` | `str` | `"0,00"` | 100% | `outros_proventos` (`NUMERIC(14,2) NULL`) |
| `outros_descontos_obrigatorios` | `str` | `"0,00"` | 100% | `outros_descontos_obrigatorios` (`NUMERIC(14,2) NULL`) |
| `cpf` | `str` | `"xxx.xxx.xxx-xx"` | Já mascarado na fonte | Sanitizado como `"***.***.***-**"` no arquivo bruto/tratado; **não persistido em coluna de CPF no banco** |

> **Atenção sobre múltiplos lançamentos na mesma competência:** Na inspeção de `Outubro/2026`, observou-se que uma mesma servidora (`ANA PAULA LOURENCO`, `ASSESSOR PARLAMENTAR CM I`, `GAB. VEREADOR RUBENS CARDOSO DA SILVA`) possui **duas linhas distintas** na mesma referência (`Proventos: 3.800,00` e `Proventos: 2.660,00`, ex.: mudança de faixa/portaria ou folha complementar com `id` distinto). A deduplicação deve distinguir **reexecução da coleta** (mesmo `id_origem` / mesmo contracheque) de **lançamentos financeiros distintos na mesma competência** (verificando `id`, `matricula`, `tipo_folha`, `tipo_movimentacao` e `total_proventos`).

### 3.2. Despesas / Empenhos (`POST /api/centi` — `acao=empenhos` — 30 campos)

| Campo no JSON (`EmpenhoItem`) | Tipo bruto | Exemplo real (2026) | Tratamento / Destino no PostgreSQL (`despesa_empenho`) |
|---|---|---|---|
| `Id` | `int` | `224943` | `id_origem` (chave única do empenho no CENTI) |
| `Numero` | `str` | `"224943"` | `numero_empenho` |
| `Sequencial` | `int` | `0` | `sequencial` |
| `Data` | `str` | `"10/11/2026"` | `data_empenho` (`DATE`, formato `DD/MM/YYYY`) |
| `Fornecedor` | `str` | `"GLOBAL SUPREMENTOS E SERVIÇOS LTDA"` | `nome_favorecido` (normalizado em `fornecedor`) |
| `CpfCnpjCredor` | `str` | `"050.xxx.xxx-63"` ou CNPJ | Se PF (11 dígitos / máscara `.xxx.`), converte para `"***.***.***-**"`; se PJ (CNPJ 14 dígitos), preserva CNPJ público |
| `ValorEmpenhado` | `str` | `"5.975,94"` | `valor_empenhado` (`NUMERIC(14,2) NULL`) |
| `ValorAnulacao` | `str` | `"0,00"` | `valor_anulacao` (`NUMERIC(14,2) NULL`) |
| `ValorLiquidado` | `str` | `"1.990,00"` | `valor_liquidado` (`NUMERIC(14,2) NULL`) — **separado de empenhado e pago** |
| `ValorPago` | `str` | `"1.990,00"` | `valor_pago` (`NUMERIC(14,2) NULL`) — **separado de empenhado e liquidado** |
| `SaldoPagar` | `str` | `"0,00"` | `saldo_pagar` (`NUMERIC(14,2) NULL`) |
| `Historico` | `str` | `"DESPESA PROVENIENTE DE..."` | `historico` (`TEXT NULL`) |
| `Elemento` / `elemento_codigo` | `str` | `"3.3.90.36.00..."` / `"36"` | `elemento_despesa` / `elemento_codigo` |
| `SubElemento` | `str` | `"99 - OUTROS SERVICOS..."` | `subelemento_despesa` |
| `Categoria` / `Grupo` / `Modalidade` | `str` | `"3 - Despesas Correntes"`, `"33..."`, `"90..."` | Classificação orçamentária completa |
| `FonteRecurso` / `DestinacaoRecurso` | `str` | `"1.00 - Recursos Ordinários"` | Fonte e destinação de recursos |
| `LicitacaoModalidade` / `IdLicitacaoDispensaAdesao` | `str` | `"Não se Aplica..."` / `""` (`NULL` se vazio) | Modalidade licitatória e vínculo (`NULL` quando `""`) |
| `TotalRegistros` | `int` | `25` | Total reportado pelo WCF para reconciliação |

### 3.3. Regras de Preservação de `NULL` (Nunca Converter Ausência em Zero)
1. **Competências futuras ou ainda não fechadas (ex.: `Novembro/2026` e `Dezembro/2026` na folha):** permanecem `NULL` (não coletadas / não publicadas), jamais `R$ 0,00`.
2. **Diárias (`cntdiarias` vs. Declaração Oficial `/cidadao/p/declaracao/16`):**
   - Nos períodos de 2026 **explicitamente cobertos pela Declaração Oficial de Não Concessão de Diárias** (`01/03/2026 a 14/04/2026` e `01/05/2026 a 22/10/2026`, ou seja, competências integrais de **Maio/2026 a Setembro/2026** e **Março/2026**), o valor de diárias possui lastro documental oficial de `R$ 0,00` (com proveniência vinculada à Declaração `/cidadao/p/declaracao/16`).
   - Nas competências de 2026 **não cobertas integralmente pela declaração oficial** (`Janeiro/2026`, `Fevereiro/2026`, `Abril/2026`, `Outubro/2026`) em que `cntdiarias` retorna `[]` e não houver empenho nominal no elemento `3.3.90.14`, o campo `diarias_brutas` será registrado como `NULL` (dados não publicados/parcialmente cobertos na fonte), e o agregador `calcular_custo_estrutura_mandato` exibirá a composição parcial transparente com aviso explícito da lacuna documental daquele subperíodo.
3. **Campos opcionais vazios (`""` ou `"-"`)**: `decreto = ""`, `IdLicitacaoDispensaAdesao = ""`, `possui_estabilidade = "-"`, `previsao_mensal = null` nas devoluções de duodécimo são convertidos para `NULL` no banco.

---

## 4. Proteção LGPD e Hipótese Legal (Etapa 2)

### 4.1. Base Legal Aplicável
- **Lei de Acesso à Informação (Lei Federal nº 12.527/2011, art. 3º, art. 7º, VI e art. 8º, § 1º, II e III):** publicidade ativa e transparência da execução orçamentária, financeira, subsídios e remuneração de cargos e funções públicas.
- **Lei Geral de Proteção de Dados Pessoais (Lei Federal nº 13.709/2018 — LGPD):**
  - **Art. 7º, II e III:** tratamento para cumprimento de obrigação legal/regulatória e pela administração pública para execução de políticas públicas.
  - **Art. 7º, § 3º e Art. 23, I:** o tratamento de dados pessoais cujo acesso é público deve considerar a **finalidade, a boa-fé e o interesse público** que justificaram sua disponibilização, observando o **princípio da necessidade/minimização (Art. 6º, III)**.

### 4.2. Controles Técnicos Implementados em Todas as Camadas
1. **Minimização na Coleta:**
   - Não coletamos nem persistimos dados bancários (banco, agência, conta), endereço residencial, telefone, e-mail particular, filiação/dependentes ou descontos facultativos individualizados (consignados/pensão alimentícia).
2. **Mascaramento Antes da Persistência (`sanitizar_lgpd`):**
   - Qualquer CPF completo ou parcialmente mascarado (`050.xxx.xxx-63`, `xxx.xxx.xxx-xx`) é normalizado para `"***.***.***-**"` **antes** de gravar o arquivo JSON tratado e o banco PostgreSQL.
   - CNPJs (14 dígitos) de pessoas jurídicas contratadas pela Câmara permanecem públicos, conforme a LAI.
3. **Banco, Logs e API FastAPI:**
   - Nenhuma tabela do PostgreSQL possui coluna para CPF completo de pessoa física.
   - Exceções e logs de coleta passam por filtro de regex de CPF.
   - Testes automatizados (`pytest`) varrem todos os snapshots, tabelas e respostas da API (`GET /api/v1/*`) garantindo `0` ocorrências de CPF completo.

---

## 5. Amostras (Fixtures Reais Verificadas)

Salvas em `apps/coleta/tests/fixtures/transparencia/`:
- [folha_pagamento_sample.json](../../apps/coleta/tests/fixtures/transparencia/folha_pagamento_sample.json) — inclui o JSON bruto verbatim de `servidores_cnt/listar` e `servidores_cnt/selecionarFolha`
- [despesas_centi_list.json](../../apps/coleta/tests/fixtures/transparencia/despesas_centi_list.json) — JSON bruto verbatim de `POST /api/centi` (`acao=empenhos`)
- [duodecimo_api_response.json](../../apps/coleta/tests/fixtures/transparencia/duodecimo_api_response.json) — JSON bruto verbatim de `sgduodecimo/listar`
- [cotas_parlamentares_declaracao.json](../../apps/coleta/tests/fixtures/transparencia/cotas_parlamentares_declaracao.json) — JSON bruto verbatim de `sggastosparlamentares/listar`
- [diarias_declaracao_sample.json](../../apps/coleta/tests/fixtures/transparencia/diarias_declaracao_sample.json) — resposta de `acao=diarias` + Declaração Oficial de Não Concessão de Diárias (`/cidadao/p/declaracao/16`)
