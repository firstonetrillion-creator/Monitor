# Roteiro de Teste de Usabilidade com Usuários Reais — Fase 3 (MVP em Beta Fechado)

> **Projeto:** Cerrado Aberto (`cerradoaberto.org.br`) — Plataforma Cidadã Independente de Transparência Legislativa (Inhumas/GO)  
> **Escopo:** Etapa 8 do Plano da Fase 3 (`docs/fase-3/plano-mvp-publico.md` e `ADR-006 / D4`)  
> **Base:** `docs/fase-0/roteiro-entrevistas.md`, `docs/01-produto.md` e `docs/05-etica-legal-editorial.md`

---

## 1. Objetivo do Teste Presencial / Guiado

Validar, com moradores reais de Inhumas (celular e computador), se o MVP em homologação (`apps/web` + `apps/api`) é **compreensível sem formação política ou contábil**, se os **estados de dado ausente (`NULL`)** evitam interpretações erradas como zero e se o **tratamento visual e editorial** é percebido como estritamente neutro e independente.

---

## 2. Perfis e Amostra Recomendada (5 a 8 participantes no beta fechado)

Seguindo a distribuição de `docs/fase-0/roteiro-entrevistas.md`:
1. **Cidadãs e cidadãos comuns (2 a 3 pessoas):** acesso preferencialmente em tela de celular (`390×844` ou aparelho próprio na mesma rede local).
2. **Comunicador local / jornalista (1 a 2 pessoas):** foco em verificação de fonte, data da coleta, detalhamento de empenhos e download de CSV.
3. **Docente ou estudante do IFG / UEG — Inhumas (1 a 2 pessoas):** foco em metodologia (`/como-calculamos`), cobertura (`/cobertura-e-limitacoes`) e tabelas completas.
4. **Liderança comunitária ou comerciante local (1 pessoa):** foco em sessões/pautas (`/sessoes`) e fornecedores Pessoa Jurídica (`/despesas`).

---

## 3. Tarefas Práticas de Usabilidade (15 a 20 minutos)

Peça para a pessoa pensar em voz alta (*think-aloud*) enquanto navega, sem ajudar no primeiro minuto de cada tarefa:

### Tarefa 1 — Independência e 3 perguntas na Página Inicial (`/`)
- **Instrução:** *"Abra a página inicial. Em 30 segundos, me diga: esse site é da Câmara Municipal ou é independente? E quanto a despesa paga da Câmara em 2026 representa por habitante de Inhumas por mês?"*
- **O que observar:**
  - Se a pessoa identifica a faixa superior de independência editorial.
  - Se localiza o indicador **R$ 16,39 / hab. / mês** (`R$ 163,92` em 10 meses, base IBGE 2026 de `54.133 hab.`) e a data da última coleta verificada (`12/11/2026`).

### Tarefa 2 — Lista de Vereadores e Preservação de `NULL` (`/vereadores` e `/vereadores/[id]`)
- **Instrução:** *"Entre na lista de vereadores. Como eles estão ordenados? Agora abra o perfil do Prof. Kelvy Fernandes e depois o perfil do Presidente da Câmara, Hugo Pessoni. O que você entende sobre o Custo da Estrutura do Mandato de cada um?"*
- **O que observar:**
  - Percepção de neutralidade: ordem alfabética e avatar uniforme com iniciais (`ADR-006 / D5`).
  - Compreensão de que **não existe cota parlamentar (CEAP)** em Inhumas.
  - Compreensão de que, no perfil de Hugo Pessoni, a folha de gabinete aparece como **"Não apurado"** (`LACUNA_PARCIAL_LOTACAO` na unidade `PRESIDENCIA`) — e **não** como `R$ 0,00`.

### Tarefa 3 — Para Onde Vai o Dinheiro, Favorecidos PJ e CSV (`/despesas`)
- **Instrução:** *"Vá para a página de Despesas. Descubra: (1) quanto a Câmara recebeu de duodécimo e quanto devolveu à Prefeitura em 2026; (2) quais empresas (Pessoa Jurídica) mais receberam pagamentos; e (3) baixe a planilha CSV do duodécimo ou dos fornecedores."*
- **O que observar:**
  - Uso do tooltip de glossário (`?`) para entender a diferença entre **Empenho**, **Liquidação**, **Pagamento** e **Duodécimo**.
  - Abertura do bloco expansível (`<details>`) com os 22 lançamentos do duodécimo.
  - Alternância entre gráfico e `"Ver dados em tabela"` e clique em `"Baixar CSV"`.

### Tarefa 4 — Diferença Técnica em Diárias (`/diarias`)
- **Instrução:** *"Abra a página de Diárias. O que a caixa de aviso explica sobre os registros de diárias de 2026?"*
- **O que observar:**
  - Se a pessoa compreende a diferença factual entre o módulo `cntdiarias` (`0` registros) e os 14 empenhos contábeis do **Elemento 14 (`R$ 6.600,00`)**, sem interpretar o texto como acusação ou veredicto (`ADR-006 / D6`).

### Tarefa 5 — Sessões, Votações e Canal de Correção (`/sessoes` e `/correcoes`)
- **Instrução:** *"Abra uma sessão plenária recente para ver quem estava presente e o que estava na pauta. Por fim, se um vereador ou cidadão encontrar um número divergente, onde ele pede correção?"*
- **O que observar:**
  - Navegação de `/sessoes` para `/sessoes/[id]` e `/materias/[id]`.
  - Localização da página `/correcoes`, do botão de envio para `firstonetrillion@gmail.com` e da tabela pública de registro de correções.

---

## 4. Checklist de Registro Pós-Teste (Sem Dados Pessoais — LGPD)

Para cada sessão de teste, registrar de forma anônima:

| Critério avaliado | Meta de aceite | Resultado observado |Ajuste necessário |
|---|---|---|---|
| Compreensão das 3 perguntas da Home | 100% entendem em < 1 min | | |
| Percepção de imparcialidade e ordem alfabética | 0 relatos de viés ou ranking punitivo | | |
| Distinção entre `Não apurado (NULL)` e `R$ 0,00` | Nenhum participante confunde lacuna com gasto zero | | |
| Clareza dos termos (Duodécimo, Empenho, CEAP) | Glossário (`?`) resolve a dúvida sem auxílio externo | | |
| Leitura e navegação no celular (sem rolagem horizontal quebrada) | 0 bloqueios de toque ou leitura | | |
| Localização da fonte, data de coleta e `/correcoes` | 100% encontram fonte e canal de correção | | |
