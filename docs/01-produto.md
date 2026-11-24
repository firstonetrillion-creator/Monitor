# 01 — Produto

## Problema
Os dados do Legislativo de Inhumas existem, mas em portais burocráticos, fragmentados e escritos para quem já entende de política e contabilidade pública. Um portal que apenas replica essas tabelas não muda nada.

## Público
1. **Cidadão comum** (prioridade): quer saber quem o representa, o que foi votado, para onde vai o dinheiro. Não entende juridiquês.
2. **Jornalistas e comunicadores locais:** precisam de dado confiável, citável e baixável.
3. **Pesquisadores e organizações civis:** precisam de API e dados abertos limpos.

## Proposta de valor
**Traduzir** (linguagem simples) · **Contextualizar** (comparações e séries históricas) · **Cruzar** (ligar fontes que o portal não liga) · **Alertar** (WhatsApp/Telegram) · **Provar** (fonte e data em todo número).

## Unidade central: a pessoa
O **perfil do vereador** é o coração do produto: presença, proposições parlamentares (excluindo atas e atos administrativos da contagem de autoria), votos nominais e **Custo da Estrutura do Mandato** (`Subsídio Bruto + Folha Bruta do Gabinete + Diárias Atribuíveis`, acompanhado da nota oficial: *"Cota parlamentar (CEAP): inexistente, conforme declaração oficial da Câmara Municipal de Inhumas."*). Cidadão entende gente, não classificação de despesa.

## Cruzamentos prioritários
| Cruzamento | Observação ética |
|---|---|
| Presença e votações por vereador | Distinguir falta justificada de ausência |
| Custo por sessão presente | Subsídio costuma ser fixo; apresentar como custo unitário, sem acusação |
| Diárias × agenda de sessões | Sinalizar inconsistência factual, sem concluir irregularidade |
| Fornecedores recorrentes / concentração | Cruzar CNPJ com dados abertos da Receita |
| Dispensas e fracionamento de licitações | Indício, não prova; redação neutra |
| Ordem cronológica × pagamentos efetivos | Exige dados limpos |
| Tema do projeto × tema do gasto do gabinete | Documentar o método de classificação |
| Voto × posição do Executivo | Fatos agregados, sem rótulo político |
| Taxa de conversão de proposições em lei | Separar moções honoríficas de projetos substantivos |
| Gasto da Câmara × limites constitucionais (art. 29-A CF) | Confirmar percentuais vigentes para a faixa populacional |
| Externos: TCM-GO, TSE, PNCP, Querido Diário | Documentar qualidade/cobertura de cada um |

## Funcionalidades por camada
- **Essencial (MVP):** home com 3 perguntas, perfil do vereador, "para onde vai o dinheiro", pauta da semana, fonte/data em tudo, canal de correção.
- **Depois:** alertas WhatsApp/Telegram, resumos em linguagem simples (IA, marcados como automáticos), busca em linguagem natural, mapa de indicações por bairro, comparativo com cidades de porte semelhante, API pública.
- **Visão:** replicar para outras câmaras (Nexlegis é usado por muitas).

## Identidade
**Nome oficial (decidido em 12/11/2026 — ADR-005):** **Cerrado Aberto** (domínio prioritário: `cerradoaberto.org.br`, a confirmar disponibilidade no ato do registro).
**Declaração de independência:** Iniciativa cidadã independente de monitoramento e interpretação de dados públicos, sem vínculo institucional, contratual ou político com a Câmara Municipal.

**Paleta (inspirada no cerrado goiano):** off-white quente (fundo), verde-cerrado profundo (primária), terra vermelha/laterita (acento), amarelo-ipê (destaque). Evitar azul-institucional e verde-amarelo literal.

**Tipografia:** títulos com personalidade (Fraunces ou Space Grotesk); texto em Inter; **numerais tabulares** nos dados.

**Tom de voz:** direto, humano, sem juridiquês, sem ironia, sem indignação. Firme nos fatos, neutro nos adjetivos.

## UX da home (3 perguntas)
1. **"Quem me representa e o que fez?"** — grade de vereadores (presença, projetos, votos).
2. **"Para onde vai o dinheiro?"** — número âncora ("R$ X por habitante por mês"), gráfico simples, "ver detalhes".
3. **"O que vai ser votado agora?"** — pauta da semana em 3 linhas por item + "me avise no WhatsApp".

Complementos: busca em linguagem natural, filtro por bairro, glossário em tooltip, "Resumo da semana". Detalhes pesados (tabelas, CSV, documentos) ficam um clique abaixo.

## Métrica de norte
Pessoas que **voltam a cada semana** (não visitas totais).
