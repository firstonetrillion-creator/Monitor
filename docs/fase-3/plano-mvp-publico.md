# Plano — Fase 3: MVP público (beta fechado)

> **Status:** aprovado pelo responsável em 18/11/2026 (ver `docs/decisoes/ADR-006-mvp-publico-beta-fechado.md`).
> **Base:** `docs/01-produto.md` (UX e identidade), `docs/02-arquitetura.md`, `docs/05-etica-legal-editorial.md`, skills `frontend-cidadao`, `modern-web-guidance` e `texto-cidadao`, API FastAPI v1 (13 rotas `GET`, somente leitura).

## 1. Objetivo e aceite (do roadmap)

**Entregas:** home com 3 perguntas, perfil do vereador, "para onde vai o dinheiro", pauta da semana, fonte/data em todo número, canal de correção funcionando, acessibilidade básica (contraste, teclado, leitor de tela), desempenho no celular.
**Aceite:** teste com usuários reais de Inhumas; nenhum texto com juízo de valor (revisão com a skill `texto-cidadao`).

## 2. Escopo de telas

| Rota | Conteúdo | Dados (API v1) |
|---|---|---|
| `/` | Home com as 3 perguntas: "Quem me representa e o que fez?", "Para onde vai o dinheiro?", "O que foi/vai ser votado?" | `vereadores`, `transparencia/duodecimo`, `transparencia/despesas`, `sessoes` |
| `/vereadores` | Grade em **ordem alfabética**, mesmo tratamento visual para todos | `GET /api/v1/vereadores` |
| `/vereadores/[id]` | Presença, proposições parlamentares, votos nominais, **Custo da Estrutura do Mandato 2026** (série mensal, nota da CEAP, estados `NULL` explicados) | `GET /api/v1/vereadores/{id}` |
| `/dinheiro` | Repasses do duodécimo × devoluções, despesas 2026 por etapa (empenhado → liquidado → pago), por elemento de despesa e por favorecido PJ; detalhe/CSV a um clique | `transparencia/*` |
| `/sessoes` e `/sessoes/[id]` | Sessões 2025–2026, presença, pauta e votações | `sessoes`, `materias` |
| `/como-calculamos` | Método de cada indicador, fontes, datas de coleta | — |
| `/cobertura-e-limitacoes` | Lacunas: histórico financeiro 2017–2025 (pedido LAI), Nexlegis 2020–2024 (Lote 3), lotação da Presidência, competências abertas | `health` + docs |
| `/sobre` | Declaração de independência, quem faz, contato | — |
| `/correcoes` | Canal de correção e registro público das correções feitas | — |

**Regras transversais:** todo número exibe fonte, data da coleta e link "Como calculamos" (componente obrigatório `<Numero>`); dado ausente aparece como "dado não publicado pela fonte" ou "em verificação", **nunca como zero**; glossário em tooltip (duodécimo, empenho, CEAP etc.).

## 3. Arquitetura proposta

- `apps/web/`: Next.js (App Router) + TypeScript + Tailwind + Observable Plot (ADR-001). Gerenciador: **npm** (Node 22 já instalado; `pnpm` não está instalado).
- **Site estático gerado no build** (`output: 'export'`): o build lê a API v1 local e gera HTML pronto. Não há servidor nem banco expostos na internet; os dados só mudam quando reconstruímos o site após nova coleta. Isso combina com "estático sempre que possível" e reduz custo e superfície de ataque.
- Cliente tipado gerado a partir do OpenAPI da API v1 (`openapi-typescript`), para que mudanças de contrato quebrem o build e não a tela.
- Fontes servidas pelo próprio site (`next/font`), **sem chamadas a terceiros** no navegador; **sem analytics** no beta.
- Possível acréscimo na API (somente leitura): endpoint de agregados para a home/página de dinheiro (`GET /api/v1/transparencia/resumo`), caso a agregação no build fique pesada. Sem escrita, sem mudança de esquema de banco.

## 4. Decisões que preciso de você (com recomendação)

| # | Decisão | Recomendação |
|---|---|---|
| D1 | **Pauta da semana:** os dados param em 12/11/2026. Mostrar pauta atual exige coleta incremental recorrente do Nexlegis (poucas requisições por semana) — é mudança de comportamento de coleta. | No beta, mostrar **"última sessão e pauta mais recente disponível"** com data explícita; autorizar a coleta semanal em etapa separada. |
| D2 | **"R$ por habitante por mês"** exige população oficial (IBGE), fonte nova. | Usar a estimativa oficial do IBGE, registrada em configuração do município com fonte e ano; buscarei o número e mostrarei a evidência antes de usar. |
| D3 | **Canal de correção:** a API não aceita escrita. | E-mail dedicado (`mailto:`) + página pública `/correcoes` com registro datado. **Preciso que você indique o e-mail.** |
| D4 | **Como fechar o beta:** hospedagem com custo exige sua aprovação. | Etapas 1–6 rodando **localmente** (revisão por capturas de tela). Para o teste com usuários: site estático em hospedagem gratuita com controle de acesso por e-mail convidado (ex.: Cloudflare Pages + Access) — `[SUPOSIÇÃO]` de gratuidade a confirmar antes de usar. |
| D5 | **Fotos dos vereadores:** baixar fotos do Nexlegis é coleta nova e envolve direito de imagem. | v1 com **iniciais em avatar uniforme** para todos; fotos oficiais em etapa futura. |
| D6 | **Divergência de diárias** (`cntdiarias` vazio × 14 empenhos no Elemento 14, 4 em nome de vereadores): cruzamento sensível que nomeia pessoas; `docs/05` exige revisão humana e jurídica. | No beta: diárias aparecem só como **componente do Custo da Estrutura do Mandato** (mesma régua para todos); a explicação da divergência fica em `/como-calculamos`, **sem destaque nominal**, até revisão. |
| D7 | **Tipografia de títulos:** Fraunces ou Space Grotesk. | **Fraunces** (títulos) + Inter (texto) com numerais tabulares. |

## 5. Etapas (cada uma termina com capturas de tela e testes)

1. **Fundação web:** scaffold `apps/web`, tokens de cor (claro/escuro), tipografia, layout com declaração de independência, componentes `<Numero>`, `<Fonte>`, `<EstadoAusente>`, `<Glossario>`, cliente tipado da API.
2. **Vereadores:** lista alfabética e perfil completo, incluindo os estados `ABERTA_SEM_PUBLICACAO` e `LACUNA_PARCIAL_LOTACAO` explicados em linguagem simples.
3. **Para onde vai o dinheiro:** duodécimo, despesas por etapa, por elemento e por favorecido PJ; gráficos de barras/linhas com tabela alternativa e CSV.
4. **Sessões e pauta:** lista e detalhe (presença, pauta, votações), conforme D1.
5. **Home:** as 3 perguntas, ligando às telas acima.
6. **Páginas institucionais:** como calculamos, cobertura e limitações, sobre, correções.
7. **Qualidade:** testes `playwright test` (fluxos principais + varredura de acessibilidade com axe), contraste AA, navegação por teclado, medição de desempenho em celular simulado, revisão de todos os textos com `texto-cidadao`, relatório final.
8. **Beta fechado:** publicação conforme D4 e roteiro de teste com usuários (`docs/fase-0/roteiro-entrevistas.md`), conduzido por você.

## 6. Critérios de pronto propostos

- 0 violações graves/críticas de acessibilidade (axe) nas rotas principais; contraste AA; tudo navegável por teclado.
- Todas as rotas funcionando com dados reais (nada de mock não sinalizado).
- 100% dos números com fonte e data; 0 valores ausentes exibidos como zero; 0 CPF em HTML gerado (teste automatizado).
- Revisão `texto-cidadao` sem nenhum termo da lista proibida (teste automatizado de vocabulário + revisão humana).
- `pytest`/`ruff` da API continuam passando; ADR-006 registrando as decisões D1–D7.

## 7. Riscos

- **Leitura enviesada de números isolados** (ex.: custo por vereador): mitigado com mesma ordem, mesma apresentação, contexto e método visível.
- **Dados envelhecem** sem coleta recorrente: data da coleta sempre visível; D1 trata a pauta.
- **Exposição jurídica ao nomear pessoas:** D6 + checklist de `docs/05` antes de abrir o beta.
- **Escopo do beta crescer:** busca, alertas e mapa por bairro ficam para a Fase 4/5.

## 8. Fora do escopo desta fase

Alertas WhatsApp/Telegram, resumos por IA, busca em linguagem natural, Lote 3 do Nexlegis, histórico financeiro 2017–2025, publicação aberta ao público geral.
