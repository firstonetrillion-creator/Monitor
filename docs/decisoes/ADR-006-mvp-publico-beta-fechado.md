# ADR-006 — Decisões de Produto, UX e Arquitetura do MVP Público (Fase 3 — Beta Fechado)

- **Status:** Aceito (aprovado pelo responsável em 18/11/2026)
- **Data:** 2026-11-18
- **Contexto:** Definição e aprovação das decisões `D1` a `D7` do plano da Fase 3 (`docs/fase-3/plano-mvp-publico.md`) para homologação e validação do MVP público do **Cerrado Aberto** (`apps/web` + `apps/api`).

---

## Decisões Aprovadas (D1–D7)

### D1 — Pauta da Semana e Recorte Temporal das Sessões
- **Decisão:** No beta fechado, exibir **"Sessões e pautas mais recentes disponíveis"** (cobertura de 2025 e 2026 até a última coleta verificada em `12/11/2026`), sempre com a data e hora exatas da coleta visíveis ao cidadão.
- **Justificativa:** Evita alterar o comportamento de coleta em produção antes da validação de usabilidade com cidadãos reais. A coleta incremental semanal do Nexlegis será tratada em autorização específica posterior.

### D2 — Indicador Per Capita ("R$ por habitante") com Base Oficial do IBGE
- **Decisão:** Adotar a população oficial do **IBGE** para **Inhumas (GO)** (código IBGE `5210000`), parametrizada por município (`municipio_id = 'inhumas-go'`):
  - **População estimada 2026 (IBGE):** `54.133` habitantes (referência principal para indicadores do exercício de 2026).
  - **Censo Demográfico 2022 (IBGE):** `52.204` habitantes (referência censitária exibida em nota complementar).
  - **Fonte oficial verificada:** IBGE Cidades — Panorama de Inhumas/GO (`https://cidades.ibge.gov.br/brasil/go/inhumas/panorama`).
- **Regra de exibição:** Todo cálculo per capita deve informar explicitamente a população utilizada (`54.133 hab. — Estimativa IBGE 2026`), o numerador contábil (ex.: despesa paga ou repasse de duodécimo acumulado nos 10 meses com dados publicados em 2026) e o link para `/como-calculamos`.

### D3 — Canal de Correção e Direito de Resposta (`/correcoes`)
- **Decisão:** Ativar a página pública `/correcoes` sem escrita no banco/API, utilizando inicialmente o endereço de e-mail provisório **`firstonetrillion@gmail.com`** (`mailto:firstonetrillion@gmail.com`) durante o beta fechado, a ser substituído por endereço institucional do domínio `cerradoaberto.org.br` antes da abertura ao público geral.
- **Regras da página `/correcoes`:**
  1. Orientar cidadãos, jornalistas, servidores e agentes públicos sobre como reportar divergências materiais indicando a URL da página e o documento oficial de referência.
  2. Manter tabela pública e datada de **Registro de Correções e Atualizações**, preservando histórico transparente de qualquer retificação realizada.

### D4 — Ambiente de Homologação e Fechamento do Beta
- **Decisão:** Conduzir as Etapas 1 a 7 integralmente em ambiente local (`127.0.0.1:8000` para a API FastAPI v1 e `127.0.0.1:3000` para o Next.js), validado por testes automatizados (`pytest`, `playwright test`, `@axe-core/playwright`) e capturas de tela desktop/mobile. O roteiro de entrevistas com usuários reais (`docs/fase-0/roteiro-entrevistas.md`) será aplicado pelo responsável antes de qualquer publicação aberta.

### D5 — Identificação Visual Uniforme dos Vereadores
- **Decisão:** Utilizar na v1 o componente `AvatarVereador` com iniciais em tipografia e paleta uniformes para todos os 16 vereadores da legislatura 2025–2028 (e registros históricos), listados sempre em **ordem alfabética**.
- **Justificativa:** Garante simetria visual estrita (`docs/05-etica-legal-editorial.md`), evita coleta adicional de imagens externas no beta e previne assimetrias de resolução ou direito de imagem.

### D6 — Apresentação Neutra da Divergência Técnica de Diárias (`cntdiarias` × Elemento 14)
- **Decisão:**
  1. Contabilizar as diárias atribuíveis normalmente como componente do **Custo da Estrutura do Mandato** (`Subsídio Bruto + Folha Bruta do Gabinete + Diárias Atribuíveis`), aplicando a mesma regra documental para todos os parlamentares.
  2. Documentar a diferença entre o módulo específico `cntdiarias` (`0` registros em 2026 e declarações de não concessão nos períodos `01/03/2026–14/04/2026` e `01/05/2026–22/10/2026`) e os 14 empenhos contábeis do **Elemento 14 (`Diárias – Civil`)** em `/como-calculamos` e na rota de consulta `/diarias`, de forma estritamente descritiva, sem destaque nominal acusatório e sem presumir irregularidade.

### D7 — Tipografia Editorial e Adoção do Modern Web Guidance
- **Decisão:**
  1. Definir **Fraunces** para títulos (`--font-fraunces`), **Inter** para corpo de texto e tabelas numéricas com `font-variant-numeric: tabular-nums` (`--font-inter`) e **JetBrains Mono** para códigos e números de empenho (`--font-mono`), auto-hospedadas via `next/font/google`.
  2. Adotar oficialmente a skill **`modern-web-guidance`** (`GoogleChrome/modern-web-guidance-src`) em conjunto com `frontend-cidadao` para assegurar padrões modernos de HTML semântico, CSS nativo (`color-scheme`, variáveis de tema, `popover`/diálogos acessíveis), responsividade e Core Web Vitals.
