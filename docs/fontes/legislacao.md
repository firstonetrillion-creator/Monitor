# Ficha — `legislacao` (Leis, Decretos Legislativos, Resoluções e Portarias — NúcleoGov)

- **Data do reconhecimento:** 2026-11-12
- **Quem (agente):** Antigravity (Co-fundador Técnico) + Subagente `browser`
- **Versão:** `v0.1.0`

---

## 1. Acesso

- **URL informada inicialmente:** `go.leg.br/cidadao/legislacao/leis` (malformada por falta de protocolo e subdomínio).
- **URL correta confirmada:**
  - **Leis Ordinárias, Complementares e Lei Orgânica:** `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis`
  - **Leis Consolidadas:** `https://acessoainformacao.inhumas.go.leg.br/informacao/mp/id=27`
  - **Decretos Legislativos:** `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/decretos`
  - **Resoluções:** `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/resolucoes`
  - **Portarias:** `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/portarias`
  - **Detalhe de Lei:** `https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id={id}` (ex.: `id=407` para a Lei 3.577/2026).
- **Exige JS? Sessão? CAPTCHA? Login?**
  - A página HTML usa JS para buscar os dados em `POST https://acessoainformacao.inhumas.go.leg.br/api` e `POST https://acessoainformacao.inhumas.go.leg.br/api/leis`. Não exige login nem CAPTCHA.
- **`robots.txt`:**
  - Mesmo domínio da Fonte 1 (`acessoainformacao.inhumas.go.leg.br/robots.txt` vazio; adotaremos `Crawl-Delay >= 5s` em respeito ao domínio pai `inhumas.go.leg.br`).
- **Exportação / Anexos:**
  - Os metadados vêm em JSON via `POST /api`.
  - Os textos integrais das leis são arquivos **PDF** hospedados no Amazon S3 (`nucleogov.s3.us-east-2.amazonaws.com/cm_inhumas/...`), entregues via URL pré-assinada (`X-Amz-Signature`, expiração de `2400s` / 40 minutos) gerada ao acionar o endpoint de download.

---

## 2. Mecânica

- **Listagem e Paginação:**
  - Requisição `POST https://acessoainformacao.inhumas.go.leg.br/api` com `multi_request=true&params={"0-leis":{"acao":"leis/buscaAvancada","limit":"0, 50","search":""}}` (contrato exato verificado e executado na Fase 5 em `24/11/2026`, retornando `407` registros únicos em `9` páginas de `50` itens com `Crawl-Delay = 5,2s`, salvos em `data/raw/inhumas-go/legislacao/leis/pagina_001.json` a `pagina_009.json`).
  - Também envia a lista de 14 categorias normativas via `leis/listarCategoria` (`Lei Ordinária`, `Lei Orgânica`, `Lei de Diretrizes Orçamentárias`, `Lei Orçamentária Anual`, `Plano Plurianual`, `Código Tributário`, `Código de Postura`, `Estatuto do Servidor`, `Regimento Interno`, `Plano Diretor`, `LAI`, `Lei Complementar`, `Emenda`, `Lei de Crédito Adicional`).
- **Detalhe e Download de PDF:**
  - Navegar para `/legislacao/lei/id={id}` ou chamar `POST https://acessoainformacao.inhumas.go.leg.br/api/leis` retorna os metadados do anexo e redireciona/fornece URL assinada AWS S3 (`https://nucleogov.s3.us-east-2.amazonaws.com/cm_inhumas/outros/{hash}.pdf?...`).
  - Como a URL S3 tem `X-Amz-Expires=2400`, **nunca devemos salvar a URL assinada do S3 como link permanente para o cidadão**, e sim o link canônico da página da lei (`https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id={id}`) + o binário PDF na nossa camada bruta com `hash_conteudo` SHA-256.

---

## 3. Conteúdo

- **Volume total em `leis`:** **406 registros** ativos (`total: "406"`, maior `id: "407"`).
- **Campos no JSON (`dados[]`):**
  - `id` (string numérica, ex.: `"407"`)
  - `tabela` (`"leis"`)
  - `numero` (ex.: `"3577"`)
  - `ementa` (texto em caixa alta)
  - `texto` (`null` em todos os registros amostrados — o texto integral está apenas no PDF anexo!)
  - `data_publicacao` (`YYYY-MM-DD`, ex.: `"2026-09-22"`)
  - `data_publicacao_portal` (`YYYY-MM-DD` ou `null`, ex.: `"2025-04-24"` na Lei 2032/1990, indicando data de cadastramento retroativo no portal)
  - `categoria` (ID `"1"` a `"14"`) e `categoria_descricao` (ex.: `"Lei Ordinária"`, `"Lei Orgânica"`)
  - `total_anexos` (ex.: `"1"`, `"3"`)
  - `covid` (`"0"` ou `"1"`), `desativado` (`"0"`), `oculto` (`"0"`)
  - `aplica` (`[]`), `recebe` (`[]`) — relacionamentos de revogação/alteração (vazios na amostra).
- **Cobertura histórica:**
  - **Mais antiga:** `Lei Orgânica 001/1990` (`05/04/1990`, `id: 1`, 3 anexos) e `Lei Ordinária 2032/1990` (`29/11/1990`, `id: 86`, Estatuto dos Servidores Públicos Municipais).
  - **Mais recente:** `Lei Ordinária 3577/2026` (`22/09/2026`, `id: 407`, publicada no placard oficial de `22/09/2026` a `22/10/2026`).
  - **Lacuna histórica evidente:** Se a numeração atual está em `3.577` e há `406` leis cadastradas no portal, cerca de ~3.100 leis históricas (especialmente pré-2005) não estão indexadas neste portal.

---

## 4. Qualidade

- **Evidência real de PDF escaneado sem camada de texto (OCR obrigatório):**
  - Baixamos e inspecionamos o PDF oficial da **Lei nº 3.577/2026** (`LEI.pdf`, `1.196.748 bytes`, 2 páginas).
  - O arquivo é uma **imagem digitalizada do papel impresso e assinado fisicamente** (com carimbo de publicação no placard, rubricas e furos de arquivo), **com camada de texto nativo 100% vazia**. Portanto, `pdfplumber` sozinho extrai string vazia; **Tesseract OCR é obrigatório** mesmo para leis de 2026!
- **Divergência entre Ementa cadastrada e texto real no PDF:**
  - Na listagem/API do portal (`id=407`), a ementa foi digitada com erro de grafia: `"PAROQUIA SANTADA"`.
  - Na imagem do PDF oficial sancionado da Lei 3.577/2026, consta corretamente `"Paroquia Santana"` (Praça Santana nº 110, CNPJ `01.569.466/0021-19`).
- **Ausência de vínculo estruturado com o Projeto de Lei de origem:**
  - O registro da Lei no portal (`legislacao`) não traz o número nem o ID do Projeto de Lei (`proposicao`) correspondente no Nexlegis. O cruzamento "Taxa de conversão de proposições em lei" precisará conciliar por número/data/ementa ou pelo despacho final de sanção dentro do Nexlegis.

---

## 5. Amostras (Fixtures)

Salvas em:
- [leis_api_page1.json](../../apps/coleta/tests/fixtures/legislacao/leis_api_page1.json)
- [leis_api_page28_oldest.json](../../apps/coleta/tests/fixtures/legislacao/leis_api_page28_oldest.json)
- [leis_table_row.html](../../apps/coleta/tests/fixtures/legislacao/leis_table_row.html)

---

## 6. Estratégia recomendada

- **Metadados:** Coletar via `POST https://acessoainformacao.inhumas.go.leg.br/api` (paginando com `50` itens por página = ~9 requisições para as 406 leis, mais Decretos Legislativos e Resoluções).
- **Anexos PDF e Texto Integral:** Baixar os PDFs com `Crawl-Delay >= 5s`, salvar no armazenamento bruto com hash SHA-256, tentar extração textual via `pdfplumber` e, quando o texto extraído for vazio/insuficiente (`< 50 chars/página`), executar **Tesseract OCR (`por`)**, gravando um indicador `qualidade_ocr` / `metodo_extracao` na tabela `documento`.

---

## 7. Riscos e perguntas em aberto

1. **Custo de armazenamento e OCR dos PDFs:** Cada PDF escaneado colorido/tons de cinza tem ~1,2 MB para 2 páginas (~500 MB–1 GB para todas as leis, decretos e resoluções).
2. **Expiração das URLs do S3:** Os links `nucleogov.s3.us-east-2.amazonaws.com` expiram em 40 minutos (`X-Amz-Expires=2400`). Na UI pública, devemos sempre apontar `fonte_url` para `https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id={id}`.
