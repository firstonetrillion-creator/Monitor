# Ficha — `nexlegis` (Sistema de Processo Legislativo — Nexlegis)

- **Data do reconhecimento:** 2026-11-12
- **Quem (agente):** Antigravity (Co-fundador Técnico) + Subagente `browser`
- **Versão:** `v0.1.0`

---

## 1. Acesso

- **URL informada inicialmente:** `https://nexlegis.com.br` (site institucional da fornecedora Nexlegis — CNPJ `44.626.127/0001-96`, Goiânia/GO).
- **URL oficial da instância de Inhumas descoberta e confirmada:**
  - **Base Web (SPA):** `https://inhumas.nexlegis.com.br/`
  - **Base REST API (JSON):** `https://inhumas.nexlegis.com.br/api/`
  - **Rotas de interface web:**
    - Sessões Plenárias: `https://inhumas.nexlegis.com.br/sessoes` (detalhe: `/sessoes/{id}/{slug}`)
    - Matérias / Proposições: `https://inhumas.nexlegis.com.br/materias`
    - Vereadores: `https://inhumas.nexlegis.com.br/vereadores`
    - Comissões: `https://inhumas.nexlegis.com.br/comissoes`
    - Lista de Presenças: `https://inhumas.nexlegis.com.br/presencas`
- **Exige JS? Sessão? CAPTCHA? Login?**
  - A interface web é uma SPA, mas **a REST API em `https://inhumas.nexlegis.com.br/api/*` responde diretamente a requisições `GET` HTTP puras em JSON**, sem necessidade de JavaScript, cookies de sessão, login ou CAPTCHA.
- **`robots.txt` e termos de uso:**
  - `https://inhumas.nexlegis.com.br/robots.txt` retorna `HTTP 200` apenas com comentários padrão da Cloudflare sobre *content signals* (nenhuma diretiva `Disallow` para `User-agent: *`).
  - `https://nexlegis.com.br/robots.txt` (domínio institucional) define `Crawl-Delay: 5`.
  - **Decisão ética:** Respeitar intervalo mínimo de `2s–5s` entre requisições (`httpx`), sem paralelismo e com `User-Agent` identificável do projeto.
- **Existe API, exportação CSV/XML/JSON, "dados abertos"? Onde?**
  - **Sim — REST API JSON pública nativa:**
    - `GET https://inhumas.nexlegis.com.br/api/sessoes?page={p}&per_page={n}`
    - `GET https://inhumas.nexlegis.com.br/api/sessoes/{id}`
    - `GET https://inhumas.nexlegis.com.br/api/materias?page={p}&per_page={n}`
    - `GET https://inhumas.nexlegis.com.br/api/materias/{id}`
    - `GET https://inhumas.nexlegis.com.br/api/vereadores`
  - Os anexos (PDFs de projetos, requerimentos, pautas e atas) ficam em bucket público S3: `https://nexlegis.s3.us-east-2.amazonaws.com/cliente/cm_inhumas/{midia_id}/{file_name}`.

---

## 2. Mecânica

- **Paginação (padrão Laravel Resource):**
  - Parâmetros query string: `page` (1-indexed) e `per_page` (testado com `1`, `2`, `15`, `100`).
  - O envelope JSON traz `data` (array de registros), `total`, `links` (`first`, `last`, `prev`, `next`) e `meta` (`current_page`, `from`, `last_page`, `per_page`, `to`, `total`).
- **Requisição mínima reproduzível:**
  ```bash
  curl -s "https://inhumas.nexlegis.com.br/api/sessoes?page=1&per_page=15" \
    -H "Accept: application/json" \
    -H "User-Agent: MonitorCamaraInhumas/0.1 (+contato)"
  ```
- **Onde estão as Presenças e Votações Nominais?**
  - A rota `/api/presencas` retorna `404` ("O caminho solicitado não pôde ser encontrado!").
  - **Descoberta técnica central:** Ao consultar o detalhe de uma sessão (`GET /api/sessoes/{id}`, ex.: `/api/sessoes/969`), o JSON retorna aninhados:
    1. `presenca`: array com todos os vereadores da sessão e seu `situacao` (ex.: `{"id": 3, "descricao": "Presente"}`).
    2. `pautas`: array com todas as matérias da Ordem do Dia / Expediente, e dentro de cada item de pauta, o objeto `votacao` contendo o array `votos` com o voto nominal de cada vereador (`{"votacao_id": 2469, "vereador_id": 2, "voto": {"id": 1, "descricao": "Favorável"}}`)!
- **Atenção ao tamanho do payload de `/api/sessoes/{id}`:**
  - Como a API serializa o objeto completo de `vereador` (incluindo o HTML da `biografia`) dentro de cada item de `presenca`, de `pautas[].materia.vereadores` e de `pautas[].votacao.votos`, uma única resposta de `/api/sessoes/969` tem **~699 KB**. Com 393 sessões, a carga histórica completa representa ~200–270 MB brutos (mas com `gzip`/`br` HTTP reduz drasticamente na rede).

---

## 3. Conteúdo

| Endpoint | Entidade(s) no modelo | Campos principais observados | Cobertura histórica (evidência) | Total de registros |
|---|---|---|---|---|
| `/api/sessoes` | `sessao` | `id`, `numero`, `ano`, `data` (`YYYY-MM-DD`), `tipo_id`, `tipo.descricao` (`Sessão Ordinária`, `Sessão Extraordinária`, `Sessão Solene`), `horario_abertura`, `data_encerramento`, `horario_encerramento`, `inicio_sessao`, `presidente_id`, `sessao_legislativa_id`, `nome_sessao`, `slug`, `midias` (PDF de pauta/ata) | **01/01/2021** (`id: 630`, `Sessão Solene 001/2021` — ata de posse) até **10/11/2026** (`id: 969` e `1002`) | **393 sessões** |
| `/api/sessoes/{id}` | `presenca`, `pauta`, `votacao`, `voto` | `presenca[].{vereador_id, situacao_id, situacao.descricao}`, `pautas[].{materia_id, ordem, turno, votacao_id, unanime, has_votos, tipo_pauta, votacao.{id, started_at, closed_at, tempo_decorrido, unanime, votos[].{vereador_id, voto.{id, descricao}}}}` | 2021 a 2026 (vinculado às 393 sessões) | 393 detalhes de sessão |
| `/api/materias` | `proposicao`, `autoria`, `tramitacao`, `documento` | `id`, `numero`, `ano`, `protocolo`, `autoria`, `ementa`, `data_publicacao`, `tipo_id`, `tipo.descricao` (`Requerimento`, `Projeto de Lei`, `Indicação`, `Moção`, `ATA DA SESSÃO`, `Julgamento de Contas`...), `situacao`, `ultima_movimentacao`, `nome_materia`, `vereadores` (autores), `midias` (PDF no S3), `tramitacao`, `sessoes`, `votacoes` | **07/10/2020** (`id: 927`, `Julgamento de Contas 004/2020`) até **10/11/2026** (`id: 2770`, `Requerimento 312/2026`) | **2.716 matérias** |
| `/api/vereadores` | `vereador` | `id`, `nome`, `nome_politico`, `nome_exibicao`, `slug`, `biografia` (HTML rico), `email_publico`, `avatar`, `foto` | Legislaturas 2021–2024 e 2025–2028 | 13 vereadores em exercício (+ suplentes/ex-vereadores referenciados nas sessões/matérias) |

---

## 4. Qualidade

- **Formatos:**
  - Datas na API: ISO `YYYY-MM-DD` (`"2026-11-10"`) e timestamps `YYYY-MM-DD HH:MM:SS` (`"2026-11-10 16:32:14"`).
  - Encoding: `UTF-8` nativo em JSON.
- **Pontos de atenção na qualidade dos dados:**
  1. **Ausência de campo estruturado de `partido` no objeto `vereador`:** Na resposta de `/api/vereadores` e `/api/sessoes/{id}`, a filiação partidária (ex.: `PSD`, `PL`, `MDB`, `PP`, `UNIÃO`, `PSB`) está descrita em texto livre dentro do HTML de `biografia`, e não em uma chave JSON separada. Será necessário extrair/curar o partido na tabela mestre de `mandato` (e validar contra dados do TSE na Fase 1/2).
  2. **Nomes políticos vs. nomes civis:** O Nexlegis registra `nome: "PROF°.KELVY FERNANDES"` e `nome_politico: "PROFESSOR KELVY FERNANDES"`, ou `nome: "WEBER TIAGO PIRES"` e `nome_politico: "WEBER ENXOVAIS"`, ou `nome: "TCHULÃO"`. O ID numérico (`vereador.id`) é estável dentro do Nexlegis, facilitando a normalização interna e o de-para com a Folha (`vereador_alias`).
  3. **Atas e Julgamentos misturados em `materias`:** A entidade `/api/materias` inclui `ATA DA SESSÃO` (`tipo_id: 144`) e `Julgamento de Contas` (`tipo_id: 211`) junto com Projetos de Lei, Requerimentos e Indicações. Nas métricas de "produção legislativa por vereador", precisamos filtrar estritamente por `tipo_id` para não contar Atas da Mesa Diretora como proposições de vereador.
  4. **Campo `unanime: false` mesmo quando todos votam Favorável:** Na votação `id: 2469` (Sessão 969), o booleano `unanime` vem `false`, mas todos os votos registrados são `"Favorável"`. O coletor/analítico deve calcular o placar real a partir do array `votos[]` e nunca confiar cegamente na flag `unanime`.

---

## 5. Amostras (Fixtures)

Salvas em:
- [vereadores_list_page1.json](../../apps/coleta/tests/fixtures/nexlegis/vereadores_list_page1.json)
- [sessoes_list_page1.json](../../apps/coleta/tests/fixtures/nexlegis/sessoes_list_page1.json)
- [sessao_969_detail.json](../../apps/coleta/tests/fixtures/nexlegis/sessao_969_detail.json)
- [materias_list_page1.json](../../apps/coleta/tests/fixtures/nexlegis/materias_list_page1.json)
- [materias_oldest_page2716.json](../../apps/coleta/tests/fixtures/nexlegis/materias_oldest_page2716.json)

---

## 6. Estratégia recomendada

- **HTTP GET direto (`httpx`) na REST API JSON (`/api/sessoes`, `/api/sessoes/{id}`, `/api/materias`, `/api/vereadores`):**
  - Zero necessidade de Playwright ou parsing de HTML (`selectolax`) para os dados estruturados do Nexlegis.
  - Paginar `/api/materias` com `per_page=50` (~55 requisições para todo o estoque histórico de 2.716 matérias).
  - Paginar `/api/sessoes` com `per_page=50` (~8 requisições para listar as 393 sessões) e buscar `/api/sessoes/{id}` incrementalmente (com intervalo `>= 2s` e compressão `Accept-Encoding: gzip, br`).
  - Na camada bruta, armazenar o JSON original (ou comprimir com `zstd`/`gzip`) devido à repetição da chave `biografia` em `/api/sessoes/{id}`.

---

## 7. Riscos e perguntas em aberto

1. **Termos de uso de fornecedor privado:** Conforme alertado em `docs/05-etica-legal-editorial.md`, o Nexlegis é operado por empresa privada a serviço da Câmara. Embora a API seja aberta e o `robots.txt` não imponha `Disallow`, a coleta histórica das 393 sessões deve respeitar estritamente taxa baixa (`1 req / 3s`) e cache imutável para sessões encerradas.
2. **Histórico de sessões mais antigas (2021):** Nas sessões de 2021 (ex.: `id: 612`, `029/2021`), campos como `horario_abertura` estão `null`. É preciso verificar na Fase 1 a partir de qual data as listas de presença e votações eletrônicas nominais passaram a ser preenchidas em 100% das sessões, exibindo essa data de corte na UI.
