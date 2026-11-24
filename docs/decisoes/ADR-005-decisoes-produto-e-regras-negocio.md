# ADR-005 — Decisões de Produto, Identidade e Regras de Negócio (Fechamento da Fase 0)

- **Status:** Aceito (aprovado pelo responsável em 12/11/2026)
- **Data:** 2026-11-12
- **Contexto:** Conclusão da Fase 0 de reconhecimento técnico e definição das diretrizes estratégicas, editoriais, contábeis e arquiteturais para início da Fase 1.

---

## Decisões Aprovadas

### 1. Nome Oficial, Domínio e Posicionamento de Independência
- **Nome oficial da plataforma:** **Cerrado Aberto**
- **Domínio prioritário:** `cerradoaberto.org.br` (com verificação de disponibilidade imediatamente antes do registro definitivo; alternativa `.com.br` também disponível em 12/11/2026).
- **Aplicação:** Utilizar **Cerrado Aberto** (`cerrado_aberto` em pacotes Python e identificadores técnicos; `CerradoAbertoBot/0.1 (+https://cerradoaberto.org.br; contato@cerradoaberto.org.br)` no `User-Agent`) em toda a documentação, código, repositórios e futura identidade visual.
- **Declaração obrigatória de independência:** A plataforma deve deixar explícito em todas as suas páginas, rodapés, documentação e metadados que **Cerrado Aberto é uma iniciativa cidadã independente de monitoramento, tradução e interpretação de dados públicos, sem qualquer vínculo institucional, contratual ou político-partidário com a Câmara Municipal de Inhumas ou com qualquer agente público**.

---

### 2. Pedido via LAI (Histórico SIGEP 2017–2025) e Política de Lacunas Históricas
- **Protocolo humano:** O documento final em `docs/fase-0/pedido-lai-final.md` (derivado de `pedido-lai-rascunho.md`) fica pronto com instruções passo a passo e endereço do e-SIC (`https://acessoainformacao.inhumas.go.leg.br/cidadao/informacao/sic`) para protocolo pessoal pelo responsável do projeto. Nenhum agente deve protocolar pedidos em nome do responsável automaticamente.
- **Tratamento de lacunas históricas:** Enquanto os dados históricos pré-migração (2017–2025, sistema legado SIGEP) não forem fornecidos oficialmente:
  1. Documentar explicitamente a lacuna histórica no banco e na interface pública.
  2. **Jamais estimar, interpolar ou transformar dados ausentes em zero (`0` ≠ `NULL`).**

---

### 3. Regra de Negócio: Indicador "Custo da Estrutura do Mandato" (Fase 2)
- **Nome oficial do indicador:** **Custo da Estrutura do Mandato**
- **Fórmula:**
  $$\text{Custo da Estrutura do Mandato} = \text{Subsídio Bruto do Vereador} + \text{Folha Bruta do Gabinete} + \text{Diárias Atribuíveis}$$
- **Declaração sobre Cota Parlamentar (CEAP):**
  - Exibir obrigatoriamente a nota textual padronizada:
    > *"Cota parlamentar (CEAP): inexistente, conforme declaração oficial da Câmara Municipal de Inhumas."*
  - Referenciar o período formalmente declarado pela Câmara (`01/01/2020` a `22/10/2026`, conforme `apps/coleta/tests/fixtures/transparencia/cotas_parlamentares_declaracao.json`).
  - Não contabilizar verba inexistente como despesa efetiva.
- **Regras contábeis e metodológicas obrigatórias:**
  1. **Vigência de lotação:** Respeitar estritamente a `Lotação` informada na folha mensal (`servidores_cnt`) e sua vigência histórica mês a mês (`valido_de` / `valido_ate` ou competência `ano`/`mes`).
  2. **Sem duplicidade:** Garantir que um mesmo servidor/matrícula na mesma competência nunca seja somado em duplicidade.
  3. **Diárias atribuíveis:** Somente atribuir diárias ao indicador de um vereador quando houver identificação documental e verificável do beneficiário no registro oficial.
  4. **Precisão conceitual na folha:** Não confundir **folha bruta** (`Proventos` / remuneração bruta do servidor) com **custo total patronal** (que incluiria encargos patronais não detalhados individualmente no portal). Explicar a diferença em `"Como calculamos"`.
  5. **Estágios da despesa:** Diferenciar claramente valores **empenhados** (líquidos de anulações), **liquidados** e **pagos** sempre que disponíveis.
  6. **Ausência de dado vs. valor zero:** Nunca converter dados ausentes ou períodos não cobertos em `R$ 0,00` (`NULL` no banco e indicação `"Dado não disponível para o período"` na UI).
  7. **Transparência metodológica:** Apresentar sempre o período de competência, a fonte oficial com link e data de coleta, e a metodologia de cálculo ao lado do indicador.

---

### 4. Regra de Negócio: Classificação e Filtro de Proposições Legislativas (Fase 1)
- **Armazenamento integral:** Na Fase 1, armazenar no PostgreSQL **100% das matérias** retornadas por `GET https://inhumas.nexlegis.com.br/api/materias`, preservando a integridade referencial com as pautas e votações das sessões plenárias.
- **Separação na camada de classificação e apresentação (`de_para_tipo_proposicao`):**
  - Na contagem de **produção legislativa de autoria parlamentar** dos vereadores, **excluir**:
    - **Atas de sessão** (`tipo_id: 144`, `"ATA DA SESSÃO"`)
    - **Julgamentos de contas** (`tipo_id: 211`, `"Julgamento de Contas"`)
    - **Outros documentos administrativos ou procedimentais** que não representem proposições legislativas de autoria parlamentar (ex.: atos administrativos da Mesa/Secretaria, ofícios administrativos de expediente, pareceres internos de comissão quando classificados separadamente), mediante classificação explícita e documentada na tabela `de_para_tipo_proposicao` (`eh_proposicao_parlamentar = FALSE`).
  - Esses registros permanecem intactos no banco e visíveis na linha do tempo das sessões plenárias e pautas, sendo filtrados apenas nos indicadores de autoria/produção parlamentar.

---

### 5. Armazenamento de PDFs Brutos e Governança de OCR
- **Armazenamento local versionado (`data/raw/`):**
  - Iniciar na Fase 1 com armazenamento em disco local estruturado em `data/raw/<fonte>/<ano>/<hash_sha256>.<ext>` acompanhado de manifesto de metadados e registro na tabela `documento_bruto`.
  - Encapsular a escrita/leitura em uma interface `StorageBackend` (`LocalStorageBackend` hoje, pronta para `S3CompatibleStorageBackend` no futuro sem alterar os coletores e sem custo financeiro no MVP).
- **Download imediato de URLs temporárias:**
  - Como os links pré-assinados do S3 da NúcleoGov (`X-Amz-Expires=2400`) expiram em 40 minutos, o coletor deve baixar o binário do PDF imediatamente após obter o JSON de metadados e calcular seu hash SHA-256 na hora.
- **Regras para OCR (`pdfplumber` + Tesseract):**
  1. Preservar sempre o arquivo PDF original intacto e imutável.
  2. Armazenar o texto extraído em coluna/estrutura separada (`texto_extraido`), mantendo o campo original da API (`texto_oficial`) distinto.
  3. Marcar explicitamente os documentos processados via OCR (`extraido_por_ocr = TRUE`, `ocr_engine_versao`, `ocr_confianca_media`).
  4. Sinalizar (`requer_revisao_humana = TRUE`) textos com baixa nitidez, divergência com a ementa ou ruído de reconhecimento, exibindo aviso claro ao cidadão junto ao link para o PDF original.
