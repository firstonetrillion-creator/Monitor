# Relatório de Cobertura Histórica e Qualidade de Dados — Fase 1 (Nexlegis)

> **Plataforma:** **Cerrado Aberto** (`cerradoaberto.org.br`) — Iniciativa cidadã independente de monitoramento e interpretação de dados públicos, sem vínculo institucional ou político com a Câmara Municipal de Inhumas.
> **Data do relatório:** 12/11/2026
> **Fonte avaliada:** `nexlegis` (`https://inhumas.nexlegis.com.br/api/*`)
> **Versão do coletor:** `cerrado-aberto-coleta/0.1.0`

---

## 1. Cobertura Histórica Verificada na Fonte `nexlegis`

| Entidade | Endpoint de Origem | Início da Série Histórica | Registro Mais Antigo Verificado | Fim da Série (Data da Coleta) | Volume Total na API |
|---|---|---|---|---|---|
| **Vereadores** | `GET /api/vereadores` | Legislaturas `2021–2024` e `2025–2028` | `id: 2` (`ADRIANO MOREIRA`) | `10/11/2026` | **15** vereadores na legislatura atual (curados com aliases em `VEREADORES_MESTRE_INHUMAS`) |
| **Sessões Plenárias** | `GET /api/sessoes` | **`01/01/2021`** | `id: 630` — `Sessão Solene 001/2021` (Posse 2021) | **`10/11/2026`** (`id: 969` — `Sessão Ordinária 043/2026`) | **393** sessões |
| **Presenças e Votações Nominais** | `GET /api/sessoes/{id}` | **`01/01/2021`** | Aninhadas dentro de cada objeto de sessão (`presenca[]` e `pautas[].votacao.votos[]`) | **`10/11/2026`** | **393** detalhes de sessão |
| **Matérias e Proposições** | `GET /api/materias` | **`07/10/2020`** | `id: 927` — `Julgamento de Contas 004/2020` | **`10/11/2026`** (`id: 2770` — `Requerimento 312/2026`) | **2.716** matérias |

---

## 2. Regras de Qualidade e Classificação Aplicadas (ADR-005)

1. **Separação entre Proposições Parlamentares e Documentos Administrativos (`de_para_tipo_proposicao`):**
   - **100% das matérias** retornadas pela API são armazenadas na tabela `proposicao` (preservando os vínculos com `pauta_item` e `votacao`).
   - Na camada de classificação e na view analítica `vw_producao_legislativa_vereador` (e no método `contar_producao_legislativa_por_vereador`), são **excluídos da contagem de produção legislativa parlamentar**:
     - `tipo_id = 144` (**Ata da Sessão**, categoria `ATO_ADMINISTRATIVO_SESSAO`, `eh_proposicao_parlamentar = FALSE`, `contabilizar_producao_vereador = FALSE`).
     - `tipo_id = 211` (**Julgamento de Contas**, categoria `JULGAMENTO_EXTERNO`, `eh_proposicao_parlamentar = FALSE`, `contabilizar_producao_vereador = FALSE`).
     - Outros documentos administrativos não parlamentares (`OUTRO_ADMINISTRATIVO`).
2. **Deduplicação de Sessões por Chave Natural:**
   - Sessões cadastradas em duplicidade na API com a mesma chave natural `(municipio_id, tipo_id_origem, numero, ano, data_abertura)` são consolidadas em um único registro ativo, preservando os IDs secundários no campo `ids_origem_duplicados`.
3. **Resolução Curada de Vereadores (`vereador` + `vereador_alias`):**
   - Todos os 15 vereadores identificados nas sessões de 2026 possuem ID canônico (`inhumas-go-ver-{id}`) e aliases curados manualmente cobrindo tanto grafias do Nexlegis (`PROF°.KELVY FERNANDES` / `PROFESSOR KELVY FERNANDES`, `WEBER TIAGO PIRES` / `WEBER ENXOVAIS`) quanto strings de lotação da folha de pagamento do CENTI (`GAB. DO VEREADOR LEANDRO ESSADO`).
   - Nomes não reconhecidos nos aliases curados **nunca sofrem fusão automática silenciosa**: retornam confiança `BAIXA_REVISAO_HUMANA` para revisão manual.
4. **Proveniência e Idempotência:**
   - 100% dos registros exigem `municipio_id`, `fonte_id`, `fonte_url`, `coletado_em`, `hash_conteudo` (SHA-256 de 64 caracteres) e `versao_coletor` validados via Pydantic (`ProvenienciaMixin`).
   - A reexecução do pipeline sobre os mesmos arquivos brutos resulta em `novos = 0` e `alterados = 0`.

---

## 3. Plano de Lotes para Backfill Histórico (Aguardando Autorização por Lote)

Conforme regra do `prompts/fase-1-nexlegis.md` (*"Backfill histórico em lotes pequenos e com taxa baixa, mediante minha autorização por lote"*), o coletor foi validado 100% offline contra as fixtures reais e aguarda sua autorização para executar os lotes de rede abaixo (com `crawl_delay = 3.0s`):

| Lote | Escopo da Coleta em Rede | Requisições Estimadas | Status |
|---|---|---|---|
| **Lote 1 (Inicial — 2026)** | `/robots.txt` + `/api/vereadores` + 8 páginas de índice de `/api/sessoes` (`per_page=50`) + detalhes das 60 sessões de 2026 (`/api/sessoes/{id}`) + 12 páginas de `/api/materias` de 2026 + 48 PDFs das sessões de 2026 | **130 requisições executadas** (`>= 3,05s/req`) | **Concluído e validado em 12/11/2026** |
| **Lote 2 (Histórico 2025)** | `/robots.txt` + detalhes das 73 sessões de 2025 (`/api/sessoes/{id}`) + 15 páginas de `/api/materias` de 2025 (`page=13..27`) + 52 PDFs das sessões de 2025 | **141 requisições executadas** (`>= 3,046s/req`) | **Concluído e validado em 12/11/2026** |
| **Lote 3 (Histórico 2020–2024)** | Detalhes das 260 sessões de 2021–2024 + páginas de `/api/materias` de 2020–2024 | ~110 requisições | Aguardando autorização |

---

## 4. Resultados Empíricos do Lote 1 Executado (`12/11/2026`)

- **Manifesto de auditoria:** `data/raw/inhumas-go/nexlegis/manifesto_lote1.json` (`execucao_id: 2b6902e5-9bbc-4682-abca-478a590ddd41`)
- **Snapshot tratado reproduzível:** `data/raw/inhumas-go/nexlegis/snapshot_tratado_lote1.json`
- **Requisições realizadas:** **130** (`HTTP 200` em 100% das chamadas; intervalo mínimo observado de **3,050s** e médio de **3,052s**; nenhum bloqueio HTTP 403/429 ou CAPTCHA).
- **Volume encontrado vs. armazenado:**
  - **Vereadores (`/api/vereadores`):** **32** encontrados e **32** armazenados (`16` atuantes em 2026 — `15` titulares + `1` suplente `WEBER ENXOVAIS` — e `16` de legislaturas anteriores/suplentes).
  - **Sessões no índice (8 páginas de `/api/sessoes?per_page=50`):** **393** encontradas (`2021: 36`, `2022: 79`, `2023: 74`, `2024: 71`, `2025: 73`, `2026: 60`) e **387** sessões únicas armazenadas após deduplicação de **6** pares duplicados exatos no histórico 2023–2024 (e identificação de **11** pares com mesma numeração `(tipo_id, numero, ano)` em 2023–2024).
  - **Sessões de 2026 detalhadas (`/api/sessoes/{id}`):** **60** coletadas e **60** armazenadas, contendo **900** registros de presença (`15 × 60`), **738** itens de pauta, **726** votações e **2.445** votos nominais.
  - **Matérias de 2026 (`/api/materias`, páginas 1 a 12):** **571** matérias de 2026 encontradas e armazenadas (**509** proposições parlamentares/legislativas e **62** documentos administrativos/atos externos separados da produção parlamentar conforme ADR-005), com **878** vínculos de autoria e **569** tramitações. As **29** matérias de 2025 presentes na página de fronteira (`page=12`) foram preservadas no JSON bruto, mas não carregadas no escopo 2026 do Lote 1.
  - **PDFs das sessões de 2026:** **48** PDFs identificados, **48** baixados com sucesso (`0` falhas), todos validados pelo cabeçalho `%PDF` e hash SHA-256.
- **Novos tipos de proposição descobertos e catalogados no Lote 1:**
  - `12`: *Projeto de Resolução* (`PROPOSICAO_PARLAMENTAR`, contabiliza = `True`)
  - `112`: *Emenda* (`PROPOSICAO_PARLAMENTAR`, contabiliza = `True`)
  - `113`: *PROJETO DE LEI DO LEGISLATIVO* (`PROPOSICAO_PARLAMENTAR`, contabiliza = `True`)
  - `145`: *ATA DA SESSAO EXTRAORDINARIA* (`ATO_ADMINISTRATIVO_SESSAO`, contabiliza = `False`)
  - `210`: *Veto ao Autógrafo de Lei* (`ATO_EXECUTIVO_SUBMETIDO`, contabiliza = `False`)
  - `213`: *BALANÇO GERAL* (`PRESTACAO_DE_CONTAS`, contabiliza = `False`)
  - `375`: *MENSAGEM DO PREFEITO* (`EXPEDIENTE_EXECUTIVO`, contabiliza = `False`)

---

## 5. Resultados Empíricos do Lote 2 Executado — Ano 2025 (`12/11/2026`)

- **Manifesto de auditoria:** `data/raw/inhumas-go/nexlegis/2025/manifesto_lote2.json` (`execucao_id: 78bcab7b-d829-40b6-8990-29177a7a9140`)
- **Snapshot tratado reproduzível:** `data/raw/inhumas-go/nexlegis/2025/snapshot_tratado_lote2.json`
- **Requisições realizadas:** **141** (`HTTP 200` em 100% das chamadas; intervalo mínimo observado de **3,046s** e médio de **3,055s**; nenhum bloqueio HTTP 403/429 ou CAPTCHA).
- **Volume encontrado vs. armazenado (escopo 2025):**
  - **Sessões de 2025 detalhadas (`/api/sessoes/{id}`):** **73** coletadas e **73** armazenadas (`48` Ordinárias, `24` Extraordinárias, `1` Especial), contendo **1.095** registros de presença (`15 × 73`), **942** itens de pauta, **874** votações e **5.545** votos nominais.
  - **Matérias de 2025 (`/api/materias`, páginas 8, 10, 11 e 12 do Lote 1 + páginas 13 a 27 novas):** **717** matérias de 2025 encontradas e armazenadas (**643** proposições parlamentares/legislativas e **74** documentos administrativos/atos externos separados da produção parlamentar conforme ADR-005), com **1.013** vínculos de autoria e **717** tramitações. As **61** matérias anteriores a 2025 presentes na fronteira foram preservadas no JSON bruto, mas não carregadas no escopo 2025 (exceto **6** matérias pautadas nas sessões de 2025 para 100% de integridade referencial).
  - **PDFs das sessões de 2025:** **52** PDFs identificados, **52** baixados com sucesso (`0` falhas), todos validados pelo cabeçalho `%PDF` e hash SHA-256.
- **Novos tipos de proposição descobertos e catalogados no Lote 2 (`2025`):**
  - `10`: *Projeto de Lei Complementar* (`PROPOSICAO_PARLAMENTAR`, contabiliza = `True`)
  - `14`: *Veto* (`ATO_EXECUTIVO_SUBMETIDO`, contabiliza = `False`)
  - `214`: *Moção de Apoio* (`PROPOSICAO_PARLAMENTAR`, contabiliza = `True`)
  - `243`: *PROJETO DE LEI COMPLEMENTAR DO LEGISLATIVO* (`PROPOSICAO_PARLAMENTAR`, contabiliza = `True`)
- **Duplicidade de numeração identificada em 2025:**
  - `(tipo_id=5, numero="036", ano=2025)` aparece em dois registros distintos: `id: 504` (*Requerimento 036/2025* sobre atendimentos na área da saúde) e `id: 1859` (*Requerimento 036/2025*, cuja ementa e autoria indicam tratar-se de Projeto de Lei do Executivo cadastrado sob tipo_id `5` na origem). Ambos foram preservados sem perda de dados e sinalizados para revisão humana.

---

## 6. Persistência Consolidada do Biênio 2025–2026 em PostgreSQL 16 e API FastAPI v1 (`12/11/2026`)

Os dados validados de **2025 (Lote 2)** e **2026 (Lote 1)** — cobrindo 100% do biênio `2025–2026` da **20ª Legislatura (`2025–2028`)** — foram persistidos no banco **PostgreSQL 16.2** (`data/pgdata/`, migração `db/migrations/0001_init_core_and_nexlegis.sql`) por meio de `carregar_bienio_2025_2026_no_postgres` (`apps/coleta/src/cerrado_aberto_coleta/nexlegis/postgres_loader.py`) e expostos pela API de leitura `cerrado-aberto-api` (`apps/api/src/cerrado_aberto_api/`).

### 6.1. Registros Persistidos no PostgreSQL 16 por Tabela (Consolidado 2025–2026)

| Categoria / Tabela | Lote 1 (`2026`) | Lote 2 (`2025`) | Total Consolidado no PostgreSQL 16 | Observação / Regra Aplicada |
|---|---:|---:|---:|---|
| `municipio` / `casa_legislativa` / `legislatura` / `partido` / `fonte` | `1`/`1`/`3`/`10`/`4` | — | `1` / `1` / `3` / `10` / `4` | Sementes estruturais multi-município (`inhumas-go`) |
| `de_para_tipo_proposicao` | `17` | `+4` | **21** | Classificação ADR-005 (10 originais + 7 Lote 1 + 4 Lote 2) |
| `lacuna_historica` | `2` | — | **2** | SIGEP `2017–2025` (Pedido LAI) e Legislação `1991–2004` |
| `coleta_execucao` | `1` | `+1` | **2** | Auditoria das execuções do Lote 1 (`2026`) e Lote 2 (`2025`) |
| `documento_bruto` | `130` | `+139` | **269** | Catálogo SHA-256 dos arquivos brutos de 2026 e 2025 |
| `vereador` | `32` | `0` novos | **32** | 16 atuantes em 2025–2026 + 16 históricos/suplentes; ausentes mantidos como `NULL` |
| `vereador_alias` | `66` | `0` novos | **66** | Aliases curados (`VEREADORES_MESTRE_INHUMAS`) + nomes políticos/civis da API |
| `mandato` | `16` | `0` novos | **16** | 15 `TITULAR` + 1 `SUPLENTE` (`WEBER ENXOVAIS`) na 20ª Legislatura (`2025–2028`) |
| `sessao` | `60` | `+73` | **133** | 100% das sessões plenárias de 2025 (`73`) e 2026 (`60`) |
| `presenca` | `900` | `+1.095` | **1.995** | 15 vereadores × 133 sessões de 2025–2026 |
| `proposicao` | `571` (`+6` pauta) | `717` (`+6` pauta) | **1.295** | **717** de `2025` (`643` parl. + `74` adm.) + **571** de `2026` (`509` parl. + `62` adm.) + **7** de anos anteriores deliberadas nas pautas de 2025–2026 |
| `autoria` | `878` | `+1.013` | **1.891** | Vínculos N:N entre proposições e vereadores autores |
| `tramitacao` | `569` | `+717` | **1.286** | Movimentações regimentais das matérias de 2025 e 2026 |
| `pauta_item` | `738` | `+942` | **1.680** | Itens da Ordem do Dia nas 133 sessões de 2025–2026 (`0` órfãos) |
| `votacao` | `726` | `+874` | **1.600** | Votações plenárias vinculadas aos itens de pauta de 2025–2026 |
| `voto` | `2.445` | `+5.545` | **7.990** | Votos nominais individuais dos vereadores nas sessões de 2025–2026 |

### 6.2. Resultados da Verificação Automatizada (`pytest` e `ruff`)

- **Suíte `apps/coleta/`:** **15 testes aprovados (`15 passed`)** e `ruff check .` com `0` erros, cobrindo idempotência no PostgreSQL (`novos=0, alterados=0` na 2ª execução tanto para Lote 1 quanto para Lote 2), integridade referencial e proveniência em 100% das tabelas de 2025–2026, preservação estrita de `NULL` e bloqueio LGPD (`ViolacaoLGPDError`).
- **Suíte `apps/api/`:** **6 testes end-to-end aprovados (`6 passed`)** e `ruff check .` com `0` erros, cobrindo consultas de `2025` e `2026` em todos os 7 endpoints somente leitura (`/api/v1/health`, `/api/v1/vereadores`, `/api/v1/vereadores/{id}`, `/api/v1/sessoes`, `/api/v1/sessoes/{id}`, `/api/v1/materias`, `/api/v1/materias/{id}`), paginação, filtros, validação `422`, bloqueio `405` para métodos de escrita, documentação OpenAPI (`/openapi.json`) e sanitização LGPD em respostas, erros e logs.

