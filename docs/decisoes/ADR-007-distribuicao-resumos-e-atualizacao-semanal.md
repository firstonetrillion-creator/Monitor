# ADR-007 — Distribuição Cidadã, Resumos em Linguagem Simples e Atualização Semanal (Fase 4)

- **Status:** Aceito (aprovado pelo responsável em 18/11/2026)
- **Data:** 2026-11-18
- **Contexto:** Abertura e execução da Fase 4 (*Distribuição e retenção*) do **Cerrado Aberto**, integrando a rotina de atualização semanal do Nexlegis, os resumos em linguagem simples e os cartões compartilháveis para WhatsApp e o **Instagram Oficial do Cerrado Aberto (`@cerradoaberto`)**.

---

## Decisões Aprovadas (D1–D5)

### D1 — Coleta Incremental Semanal no Nexlegis (`apps/coleta`)
- **Decisão:** Implementar o coletor incremental `apps/coleta/src/cerrado_aberto_coleta/nexlegis/incremental.py` com execução imediata da 1ª atualização semanal de 2026 (delta desde `12/11/2026` até `18/11/2026`, trazendo a **Sessão Ordinária 044/2026** de `17/11/2026` e `+16` proposições novas, totalizando `134` sessões e `1.311` proposições no PostgreSQL 16).
- **Regras técnicas:** verificação prévia de `robots.txt`, intervalo mínimo educado `>= 3,0s` entre requisições (`12` requisições na 1ª execução), mascaramento preventivo de CPF (LGPD), bruto imutável em `data/raw/inhumas-go/nexlegis/2026/` + manifesto em `data/raw/inhumas-go/nexlegis/incremental/YYYY-MM-DD/` e upsert 100% idempotente.

### D2 — Motor Determinístico de Resumos em Linguagem Simples (`apps/api`)
- **Decisão:** Adotar na v1 o motor determinístico `apps/api/src/cerrado_aberto_api/resumos.py` (custo `R$ 0`, zero risco de alucinação factual) que traduz tipo de proposição, ementa oficial, autoria e placar em 3 linhas claras (**O que é · O que propõe · Situação e resultado**).
- **Regra editorial (`docs/05-etica-legal-editorial.md` Regra 6):** todo resumo exibe obrigatoriamente o selo **"Resumo automático"**, o aviso de conferência do documento original com link direto para a fonte oficial e validação automatizada contra a lista de vocabulário proibido (`texto-cidadao`).

### D3 — Identidade do Instagram Oficial do Cerrado Aberto nos Cartões PNG
- **Decisão:** Adotar **`@cerradoaberto`** e **`cerradoaberto.org.br`** como assinatura oficial do nosso sistema nos cartões visuais gerados localmente em Canvas 2D (`1080×1350` Feed/Carrossel em 3 slides e `1080×1920` Stories/Status) e na legenda pronta em `/boletins`, acompanhados sempre pela declaração de independência editorial (*"Iniciativa cidadã independente, sem vínculo com a Câmara Municipal"*), fonte oficial e data da coleta.

### D4 — Distribuição Assistida para WhatsApp sem Custo Externo
- **Decisão:** Disponibilizar em `/boletins` (e a partir de qualquer `/sessoes/[id]`) um alerta pronto para WhatsApp estritamente limitado a **`<= 400` caracteres** (`texto-cidadao`), com fonte oficial, data da coleta, link de conferência e opção de saída (`"Para parar, responda SAIR."`), acompanhado por botão acessível de cópia a um clique (`BotaoCopiar`, seguindo `modern-web-guidance` `copy-button`) e link `https://wa.me/?text=...`, sem dependência de API paga da Meta.

### D5 — Script Semanal Local sob Controle do Responsável
- **Decisão:** Entregar o script operacional [atualizar-semana.ps1](../../scripts/atualizar-semana.ps1) pronto para execução sob demanda ou agendamento no Windows Task Scheduler, rodando a coleta incremental + testes de qualidade e LGPD sem disparo automático oculto.
