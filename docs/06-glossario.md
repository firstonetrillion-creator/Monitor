# 06 — Glossário (para agentes e para o site)

**Legislativo**
- **Projeto de Lei (PL):** proposta de norma que, se aprovada e sancionada, vira lei.
- **Requerimento:** pedido formal feito por vereador (informações, providências, homenagens etc.).
- **Indicação:** sugestão ao Executivo para que faça algo (ex.: obra, serviço). Não obriga.
- **Moção:** manifestação da Câmara (aplauso, apelo, protesto, pesar). Não cria obrigação.
- **Pauta:** lista do que será discutido/votado na sessão.
- **Ata:** registro oficial do que ocorreu na sessão.
- **Votação nominal:** cada vereador vota e o voto fica registrado individualmente.
- **Legislatura:** período de 4 anos de mandato dos vereadores.
- **Julgamento de contas:** votação em que a Câmara analisa as contas anuais da Prefeitura após o parecer técnico do Tribunal de Contas dos Municípios (TCM-GO). *(Termo identificado em `inhumas.nexlegis.com.br/api/materias`, `tipo_id: 211`)*

**Finanças públicas**
- **Duodécimo:** repasse mensal do Executivo ao Legislativo (1/12 do orçamento da Câmara).
- **Devolução de duodécimo:** dinheiro do repasse mensal que a Câmara economizou (não gastou) e devolve aos cofres da Prefeitura para ser usado em áreas como saúde, educação ou obras. *(Termo identificado em `acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/sgduodecimo`)*
- **Empenho → Liquidação → Pagamento:** três estágios da despesa (reserva de verba → confirmação de entrega → saída do dinheiro).
- **Anulação de empenho:** cancelamento total ou parcial de uma reserva de dinheiro quando a compra não acontece ou custa menos do que o previsto. Deve ser descontada do valor empenhado bruto para calcular o gasto efetivo. *(Termo identificado em `acessoainformacao.inhumas.go.leg.br/api/centi` — campo `Anulacao`)*
- **Ordem cronológica de pagamentos:** regra que exige pagar fornecedores na ordem de exigibilidade.
- **Licitação / dispensa / inexigibilidade:** modalidades de contratação (com ou sem disputa).
- **Diária:** valor pago por deslocamento a serviço.
- **Cota parlamentar / verba de gabinete:** recurso indenizatório para custear atividade do mandato (combustível, material etc.). **Nota oficial em Inhumas:** *"Cota parlamentar (CEAP): inexistente, conforme declaração oficial da Câmara Municipal de Inhumas."* (período declarado: 2020–2026; fonte: `acessoainformacao.inhumas.go.leg.br/cidadao/transparencia/sggastosparlamentares`).
- **Custo da Estrutura do Mandato:** indicador composto por $\text{Subsídio Bruto do Vereador} + \text{Folha Bruta do Gabinete} + \text{Diárias Atribuíveis}$. Respeita a vigência histórica da lotação de cada servidor, exige identificação verificável para diárias, não confunde folha bruta com custo patronal total e nunca transforma dados ausentes em zero (`ADR-005`).
- **Subsídio:** remuneração mensal fixa do vereador.
- **SICONFI (Sistema de Informações Contábeis e Fiscais do Setor Público Brasileiro):** sistema oficial da Secretaria do Tesouro Nacional (Ministério da Fazenda) que reúne a Declaração de Contas Anuais (`DCA`) dos municípios brasileiros em padrão contábil único. *(Fonte: `apidatalake.tesouro.gov.br/ords/siconfi/tt`)*
- **Função 01 — Legislativa:** classificação funcional da despesa pública no `DCA-Anexo I-E` do SICONFI que agrupa os gastos vinculados à atividade do Poder Legislativo municipal, usada no comparativo intermunicipal do Cerrado Aberto. *(Fonte: `SICONFI / MCASP`)*
- **OCR (Reconhecimento Óptico de Caracteres):** conversão automatizada de PDFs digitalizados em imagem para texto pesquisável; no Cerrado Aberto, todo texto extraído por OCR recebe aviso explícito e link para o PDF oficial (`ADR-004`). *(Fonte: `acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis`)*

> Agentes: ao encontrar termo novo nas fontes, adicione aqui com definição em linguagem simples e cite a fonte da definição.
