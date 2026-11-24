# Relatório da Fase 2 — Portal da Transparência CENTI/NúcleoGov e Custo da Estrutura do Mandato (2026)

> **Projeto:** Cerrado Aberto (`cerradoaberto.org.br`) — Plataforma Cidadã Independente de Transparência Legislativa  
> **Município:** Inhumas (GO) (`inhumas-go`)  
> **Escopo:** Exercício de **2026** (janeiro a 12/11/2026)  
> **Data de conclusão:** 12/11/2026  

---

## 1. Escopo Executado e Proveniência

Foram coletados, sanitizados, versionados com SHA-256 em `data/raw/inhumas-go/transparencia_centi/2026/` e persistidos de forma idempotente no **PostgreSQL 16** todos os módulos públicos de 2026 do Portal da Transparência (`https://acessoainformacao.inhumas.go.leg.br/`):

| Módulo | Fonte | Registros (2026) | Observações e Reconciliação |
|---|---|---:|---|
| **Folha de Pagamento (`servidores_cnt`)** | `transparencia_centi` | **939** | Competências fechadas `01/2026` a `10/2026` (inclui folhas `MENSAL`, `FÉRIAS`, `Adiantamento 13º Salario` e `RESCISÃO`). Competências `11/2026` e `12/2026` ainda em aberto (preservadas como `NULL`). |
| **Despesas / Empenhos (`cntdespesas`)** | `transparencia_centi` | **360** | Período `01/01/2026` a `12/11/2026`. Reconciliação exata com o cabeçalho/rodapé oficial do portal: **Empenhado Bruto** `R$ 11.122.741,47`, **Anulações** `R$ 1.244.416,61`, **Empenhado Líquido** `R$ 9.878.324,86`, **Liquidado** `R$ 8.873.608,80`, **Pago** `R$ 8.873.608,80`. |
| **Fornecedores / Favorecidos** | `transparencia_centi` | **102** | 102 favorecidos distintos (Pessoa Jurídica com CNPJ 14 dígitos e Pessoa Física com CPF integralmente mascarado). |
| **Diárias (Cruzamento `cntdiarias` × `cntdespesas`)** | `transparencia_centi` | **14** | Ver Seção 3 sobre a divergência contábil entre o submódulo `cntdiarias` (`0` registros) e o Elemento `14 - Diárias – Civil` (`14` empenhos pagos, `R$ 6.600,00`, dos quais `R$ 1.600,00` diretamente a 3 vereadores). |
| **Duodécimo (`sgduodecimo`)** | `transparencia_nucleogov` | **22** | 11 repasses recebidos do Executivo (**`R$ 9.111.797,89`**) e 11 devoluções à Prefeitura (**`R$ 99.000,00`**). |
| **Declarações Oficiais** | `transparencia_nucleogov` / `centi` | **2** | Declaração de Inexistência de Cota Parlamentar/CEAP (`01/01/2020` a `22/10/2026`) e Declaração de Não Concessão de Diárias (`/cidadao/p/declaracao/16`). |

---

## 2. Proteção LGPD Aplicada

- **35 empenhos** de Pessoa Física que vinham no CSV oficial com CPF parcialmente mascarado (`050.xxx.xxx-63`) tiveram o documento substituído antes da gravação em disco por **`***.***.***-**`**.
- **939 registros** da folha de pagamento foram armazenados exclusivamente com **`***.***.***-**`**, sem CPF completo em disco, banco de dados, logs ou respostas da API.
- O validador `validar_ausencia_cpf_em_valores` bloqueia com `ViolacaoLGPDError` qualquer tentativa de persistência de CPF completo, e o middleware/filtro de log da FastAPI v1 sanitiza automaticamente eventuais ocorrências em respostas ou mensagens de erro.

---

## 3. Custo da Estrutura do Mandato (2026) — Metodologia, Cruzamento e Achados Objetivos

Fórmula aplicada (ADR-005, Decisão 3):

> **Custo da Estrutura do Mandato = Subsídio Bruto do Vereador + Folha Bruta do Gabinete + Diárias Atribuíveis**

### Principais achados verificados nos dados reais de 2026:
1. **Subsídio Bruto Padrão:** `R$ 12.796,93/mês` (com adicional de férias em janeiro/2026 de `R$ 17.062,15` e adiantamento de 13º salário de `R$ 8.957,85` para os parlamentares que optaram pelo adiantamento entre fev e set/2026).
2. **Lotação da Presidência (`PRESIDENCIA`):** O vereador **Hugo Leonardo Pessoni** (Presidente da Câmara em 2026) está lotado na unidade institucional `PRESIDENCIA` junto a cargos de assessoria administrativa/jurídica institucional, sem lotação apartada `GAB. DO VEREADOR HUGO PESSONI`. Conforme o princípio de **nunca estimar nem converter dado ausente em zero**, suas competências `01/2026` a `10/2026` registram `competencia_status = 'LACUNA_PARCIAL_LOTACAO'`, mantendo `folha_bruta_gabinete = NULL` e `custo_estrutura_mandato_total = NULL` (enquanto `subsidio_bruto_vereador` = `R$ 141.192,37` e `diarias_atribuiveis_pagas` = `R$ 200,00` são exibidos separadamente).
3. **Divergência Contábil de Diárias (`cntdiarias` × Elemento `14`):**
   - O submódulo específico `cntdiarias` (`acao=diarias`) retorna `0` registros em 2026, e há declaração formal de não concessão para `01/03/2026–14/04/2026` e `01/05/2026–22/10/2026`.
   - Contudo, o cruzamento contábil com `cntdespesas` (Elemento `14 - Diárias – Civil`) identificou **14 empenhos pagos em 2026** (`R$ 6.600,00` ao todo), dos quais **4 empenhos** (em janeiro e fevereiro/2026, fora da janela da declaração de março–outubro) foram emitidos diretamente em nome de 3 vereadores:
     - **Jôsy Militão Galdine:** `R$ 1.000,00` (Empenho `219886`, `26/02/2026`)
     - **Rubens Cardoso da Silva:** `R$ 400,00` (Empenhos `217377` e `217383`, `22/01/2026`)
     - **Hugo Leonardo Pessoni:** `R$ 200,00` (Empenho `219892`, `25/02/2026`)
   - Os demais 10 empenhos (`R$ 5.000,00`) referem-se a servidores (incluindo motoristas, controle interno e assessores).
4. **Cota Parlamentar (CEAP):** Confirmada inexistência oficial de cota parlamentar ou verbas indenizatórias (`01/01/2020` a `22/10/2026`), exibida como nota metodológica obrigatória em todos os registros do indicador.
5. **Competências Abertas (`11/2026` e `12/2026`):** Preservadas integralmente como `NULL` (`ABERTA_SEM_PUBLICACAO`), sem conversão em zero.

---

## 4. Integração na API FastAPI v1

- `GET /api/v1/vereadores` e `GET /api/v1/vereadores/{id}` agora integram os dados legislativos do **Nexlegis (2025–2026)** com a série mensal e acumulada de **2026 do Custo da Estrutura do Mandato** (`custo_estrutura_mandato_2026`), incluindo metodologia, nota da CEAP e limitações.
- Novos endpoints somente leitura (`GET`):
  - `/api/v1/transparencia/custo-mandato`
  - `/api/v1/transparencia/folha`
  - `/api/v1/transparencia/despesas`
  - `/api/v1/transparencia/diarias`
  - `/api/v1/transparencia/duodecimo`
  - `/api/v1/transparencia/declaracoes`
