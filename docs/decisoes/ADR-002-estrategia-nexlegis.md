# ADR-002 — Estratégia de coleta da fonte `nexlegis`

- **Status:** Aceito (aprovado em 12/11/2026)
- **Data:** 2026-11-12
- **Contexto:**
  O reconhecimento técnico da Fase 0 ([docs/fontes/nexlegis.md](../fontes/nexlegis.md)) revelou que o portal legislativo da Câmara Municipal de Inhumas (`https://inhumas.nexlegis.com.br/`) é uma SPA que consome uma **REST API JSON pública e sem autenticação** em `https://inhumas.nexlegis.com.br/api/*`:
  - `GET /api/vereadores` (vereadores, biografia HTML, fotos)
  - `GET /api/sessoes?page={p}&per_page={n}` (393 sessões desde `01/01/2021`)
  - `GET /api/sessoes/{id}` (detalhe da sessão contendo o array `presenca` e o array `pautas` com `votacao` e `votos` nominais de cada vereador)
  - `GET /api/materias?page={p}&per_page={n}` (2.716 matérias desde `07/10/2020`, incluindo autorias, tramitação atual e links de PDFs no S3)
- **Decisão:**
  1. **Coletar exclusivamente via requisições HTTP `GET` (`httpx`) na REST API JSON**, descartando o uso de Playwright ou scraping de HTML para esta fonte.
  2. **Obter presenças e votações nominais a partir de `GET /api/sessoes/{id}`**, já que `/api/presencas` retorna `HTTP 404` e toda a estrutura de presença e votos está aninhada no detalhe da sessão.
  3. **Compressão e imutabilidade do bruto:** Enviar `Accept-Encoding: gzip, br` e salvar o JSON bruto versionado (comprimido ou deduplicando o campo `biografia` apenas na camada tratada, mantendo o bruto intacto), pois cada resposta de `/api/sessoes/{id}` pesa ~699 KB devido à repetição do objeto `vereador` completo.
  4. **Política de taxa e cache:** Intervalo mínimo de `3s` entre requisições (`<= 20 req/min`), `User-Agent` identificável e coleta incremental (sessões com status encerrado e matérias já baixadas só são reconsultadas em janela móvel de atualização para detectar edições retroativas).
  5. **Filtragem de tipos em `materias`:** Separar na camada tratada/analítica as proposições parlamentares substantivas (`Projeto de Lei`, `Requerimento`, `Indicação`, `Moção`) de documentos administrativos que usam a mesma tabela (`ATA DA SESSÃO` `tipo_id=144`, `Julgamento de Contas` `tipo_id=211`).
- **Consequências:**
  - **Positivas:** Coleta 100% determinística, rápida (~55 requisições para listar todas as matérias; ~8 requisições para listar todas as sessões) e resistente a mudanças visuais de CSS/HTML.
  - **Negativas / Atenção:** Como `vereador` não traz o campo `partido` estruturado na API do Nexlegis (apenas mencionado na `biografia`), a filiação partidária por legislatura deverá ser curada na tabela `mandato` e enriquecida com dados do TSE.
