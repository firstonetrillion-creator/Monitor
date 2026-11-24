# ADR-004 — Estratégia de coleta da fonte `legislacao`

- **Status:** Aceito (aprovado em 12/11/2026 — ver regras de armazenamento e OCR em ADR-005)
- **Data:** 2026-11-12
- **Contexto:**
  O reconhecimento técnico da fonte `legislacao` ([docs/fontes/legislacao.md](../fontes/legislacao.md)) confirmou a URL `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis` (além de `/decretos`, `/resolucoes` e `/portarias`).
  Foram identificadas três características críticas:
  1. Os metadados das 406 leis são retornados em JSON estruturado via `POST https://acessoainformacao.inhumas.go.leg.br/api`, porém o campo `texto` vem sempre `null`.
  2. O texto integral das normas existe apenas nos anexos PDF, cujos links de download no Amazon S3 (`nucleogov.s3.us-east-2.amazonaws.com`) são pré-assinados e **expiram em 40 minutos (`X-Amz-Expires=2400`)**.
  3. A inspeção real do PDF da Lei nº 3.577/2026 comprovou que **mesmo leis recentes de 2026 são PDFs escaneados em imagem (sem camada de texto selecionável)** e que há erros de digitação na ementa cadastrada no portal (`"PAROQUIA SANTADA"` no portal vs. `"Paroquia Santana"` no texto escaneado da lei).
- **Decisão:**
  1. **Coleta de metadados via `POST /api` (`httpx`)** com paginação de 50 registros e `Crawl-Delay >= 5s`.
  2. **URL de proveniência canônica:** Registrar sempre `https://acessoainformacao.inhumas.go.leg.br/legislacao/lei/id={id}` como `fonte_url` pública, e nunca a URL temporária pré-assinada do S3.
  3. **Download e pipeline híbrido de extração de PDF (`pdfplumber` + Tesseract OCR):**
     - Baixar imediatamente o binário PDF original (antes da expiração de 40 min da URL pré-assinada) para a camada bruta versionada (`data/raw/legislacao/`) através da abstração `StorageBackend`, registrando `hash_conteudo` (SHA-256).
     - Executar `pdfplumber`; se a página retornar menos de 50 caracteres úteis, acionar automaticamente OCR com **Tesseract (`lang='por'`)** sobre a imagem renderizada da página.
     - Preservar sempre o PDF original, armazenar o `texto_extraido` separadamente, marcar `extraido_por_ocr = TRUE` e sinalizar `requer_revisao_humana = TRUE` quando o texto extraído apresentar baixa confiança ou divergência com a ementa oficial.
- **Consequências:**
  - **Positivas:** Viabiliza pesquisa textual em leis que hoje são "imagens cegas" para o cidadão no portal oficial e corrige limitações de busca por erro de digitação na ementa (como o caso `"SANTADA"` vs. `"Santana"`).
  - **Negativas / Atenção:** Maior tempo de processamento inicial para OCR das ~406 leis (mitigado pelo fato de ser uma carga histórica única, processada em lote apenas para PDFs novos cujo `hash_conteudo` ainda não conste no banco).
