# Plano — Fase 4: Distribuição, Retenção e Atualização Semanal

> **Status:** aprovado pelo responsável e implementado em 18/11/2026 (ver `docs/decisoes/ADR-007-distribuicao-resumos-e-atualizacao-semanal.md`).
> **Base:** `docs/01-produto.md`, `docs/04-roadmap.md`, `docs/05-etica-legal-editorial.md`, skills `texto-cidadao`, `frontend-cidadao`, `scraper-resiliente`, `qualidade-de-dados` e `regex-vs-llm-structured-text`.

---

## 1. Contexto e Diagnóstico (Verificado via Browser em 18/11/2026)

1. **Canais Oficiais do Cerrado Aberto (nosso sistema):**
   - A Fase 4 estrutura a distribuição oficial da nossa plataforma no **Instagram Oficial do Cerrado Aberto** e no **WhatsApp** (além de presença institucional no rodapé, cabeçalho e página `/sobre` do sistema).
   - O sistema passa a contar com uma central integrada (`/boletins` e botões em `/sessoes/[id]` e `/materias/[id]`) que gera automaticamente os **cartões visuais oficiais do Cerrado Aberto** (carrossel `1080×1350` para Feed e `1080×1920` para Stories/Status, com nossa paleta do cerrado, tipografia Fraunces + Inter, assinatura `@cerradoaberto` / `cerradoaberto.org.br` e selo de independência) + **legenda pronta para o Instagram** e **alerta curto (`<= 400 caracteres`) para WhatsApp**.
2. **Novos dados legislativos disponíveis após o corte de 12/11/2026 (`inhumas.nexlegis.com.br`):**
   - A verificação via browser confirmou que o Nexlegis já publicou a **Sessão Ordinária 044/2026** realizada em **`17/11/2026` (`16:00h`)**, com 12 itens na pauta (`Ata da Sessão 043/2026`, `Projeto de Lei do Legislativo 026/2026` e `Requerimentos 315, 316, 317, 319, 320, 322, 323, 324, 325 e 326/2026` — chegando ao `id_origem = 2786`, total de `394` sessões e `2.733` matérias).

---

## 2. Objetivo e Critérios de Aceite

**Objetivo:** Integrar ao Cerrado Aberto:
1. **Atualização incremental semanal dos dados** (coletando apenas o delta de sessões e proposições novas, como a Sessão `044/2026` de `17/11/2026`, com mínimo de requisições e proveniência integral);
2. **Resumos em linguagem simples** para proposições e para o boletim semanal da sessão, com selo obrigatório **`Resumo automático`** e link para o documento original;
3. **Central de Alertas e Cartões Compartilháveis (`/boletins`)** para **WhatsApp** (texto curto de até ~400 caracteres + compartilhamento rápido) e **Instagram Oficial do Cerrado Aberto** (gerador de cards PNG `1080×1350` Feed/Carrossel e `1080×1920` Stories/Status direto no navegador, a custo zero).

**Critérios de aceite:**
- Coleta incremental idempotente, respeitando `robots.txt` e intervalo `>= 3,0s` entre requisições, persistindo bruto imutável e atualizando o PostgreSQL 16 sem duplicar registros.
- 100% dos resumos automáticos rotulados com *"Resumo automático"*, linkando a fonte oficial, sem juízo de valor e aprovados pela auditoria automatizada de vocabulário (`texto-cidadao`) e LGPD (`0` CPF).
- Geração funcional de texto para WhatsApp (com cópia a um clique e link `wa.me`) e download de cartões PNG para Instagram (`1080×1350` e `1080×1920`) com fonte, data da coleta e declaração de independência.

---

## 3. Arquitetura dos 3 Submódulos

### Pilar A — Atualização Incremental Semanal (`apps/coleta`)
- **Arquivo novo:** `apps/coleta/src/cerrado_aberto_coleta/nexlegis/incremental.py`
- **Comportamento:**
  1. Lê no PostgreSQL 16 (ou nos manifestos locais) o maior `id_origem_nexlegis` e a última data de sessão/matéria coletada em 2026.
  2. Consulta apenas a primeira página de `/api/sessoes?per_page=20` e `/api/materias?per_page=50`.
  3. Baixa apenas os detalhes (`/api/sessoes/{id}` e `/api/materias/{id}`) das sessões e matérias de 2026 novas ou atualizadas desde a última coleta (ex.: `Sessão Ordinária 044/2026` e matérias `2775` a `2786` — cerca de 10 a 15 requisições no total, com `>= 3,0s` de intervalo).
  4. Grava os payloads brutos e o manifesto auditável em `data/raw/inhumas-go/nexlegis/incremental/YYYY-MM-DD/` com hash SHA-256 e mascaramento preventivo de CPF.
  5. Executa o upsert idempotente no PostgreSQL 16 via `postgres_loader.py` e registra a execução em `coleta_execucao`.
- **Comando CLI semanal (manual ou agendável via Task Scheduler/cron local):**
  `uv run --directory apps/coleta python -m cerrado_aberto_coleta.nexlegis.incremental --municipio-id inhumas-go --ano 2026`

### Pilar B — Resumos em Linguagem Simples (`apps/coleta` + `apps/api`)
- **Abordagem recomendada (determinística e gratuita por padrão, conforme `regex-vs-llm-structured-text` e `AGENTS.md` Seção 8):**
  - Para não depender de chave de API paga nem correr risco de alucinação factual, o motor padrão de resumo (`apps/api/src/cerrado_aberto_api/resumos.py`) estrutura cada proposição e cada sessão em português claro a partir dos metadados oficiais verificados:
    1. **O que é este documento:** explica o tipo em linguagem cidadã (ex.: *"Requerimento: pedido formal de providência ou informação feito por vereador à Prefeitura ou à Mesa Diretora"*, *"Projeto de Lei do Legislativo: proposta de nova lei municipal criada por vereador"*).
    2. **O que propõe (em linguagem simples):** limpa jargões repetitivos da ementa oficial (como *"REQUER QUE SEJA ENCAMINHADO OFÍCIO AO EXCELENTÍSSIMO SENHOR PREFEITO MUNICIPAL..."* → *"Solicita ao Prefeito Municipal..."*) mantendo 100% de fidelidade ao objeto original; se a ementa for genérica, informa explicitamente *"A ementa publicada não detalha o endereço ou valor; confira o anexo original"*.
    3. **Quando, quem propôs e qual o resultado:** data, autoria e placar em plenário (ex.: *"Aprovado por unanimidade na Sessão Ordinária 044/2026 em 17/11/2026"*).
  - **Selo obrigatório (`docs/05-etica-legal-editorial.md`):** todo resumo retorna `rotulo_transparencia = "Resumo automático gerado a partir dos metadados oficiais"`, `revisado_por_humano` e `documento_original_url`.
- **Endpoints novos na API FastAPI v1 (somente leitura `GET`):**
  - `GET /api/v1/boletins/resumo-semanal`: retorna o boletim estruturado da sessão plenária mais recente (ou de uma `sessao_id` escolhida), incluindo resumo em linguagem simples, contagem de presentes/ausentes, proposições votadas agrupadas por tipo, panorama financeiro 2026 com fonte/data e textos pré-formatados para WhatsApp e Instagram.
  - Campo `resumo_cidadao` adicionado em `GET /api/v1/materias/{id}` e `GET /api/v1/sessoes/{id}`.

### Pilar C — Alertas WhatsApp e Cartões para o Instagram Oficial (`apps/web`)
- **Nova página `/boletins` ("Resumo da Semana e Cartões para Compartilhar") + componente `<CompartilharCard>` integrado em `/sessoes/[id]` e `/materias/[id]`:**
  1. **Alerta pronto para WhatsApp (`<= 400 caracteres`):**
     - Texto enxuto seguindo `texto-cidadao`: título da sessão, data, presenças, resumo das matérias votadas, fonte oficial, data da coleta e link para conferência.
     - Botões **"Copiar texto para WhatsApp"** e **"Enviar no WhatsApp"** (`https://wa.me/?text=...`), além de legenda completa pronta para post do Instagram.
  2. **Gerador de Cartões Visuais (Instagram Oficial do Cerrado Aberto & Status do WhatsApp):**
     - Renderizador visual client-side em Canvas/SVG de alta resolução (**sem dependências externas pagas**), gerando imagens PNG prontas para download em dois formatos:
       - **Instagram Feed / Carrossel (`1080×1350` — proporção 4:5)** em 3 slides:
         - **Slide 1 (Capa da Sessão):** Nome da sessão, data, quórum/presenças e destaque do Cerrado Aberto.
         - **Slide 2 (O que entrou na pauta e foi votado):** Projetos de lei, requerimentos e indicações da sessão em linguagem simples.
         - **Slide 3 (Transparência e Fonte):** Dados acumulados da Câmara em 2026 (`R$ 16,39 / hab. / mês`), fonte oficial, data/hora da coleta e aviso de iniciativa cidadã independente.
       - **Instagram Stories / Status do WhatsApp (`1080×1920` — proporção 9:16)**: cartão vertical único resumindo a sessão ou matéria.
     - Botão **"Baixar PNG (1080×1350)"** e **"Baixar Story/Status (1080×1920)"** a um clique.

---

## 4. Decisões para sua Aprovação (D1–D5)

| # | Decisão | Recomendação |
|---|---|---|
| **D1** | **Execução imediata da 1ª atualização incremental semanal (Nexlegis até 18/11/2026):** buscar a `Sessão Ordinária 044/2026` (`17/11/2026`) e as proposições novas publicadas entre `12/11/2026` e `18/11/2026` (~12 a 15 requisições com intervalo `>= 3,0s`). | **Aprovar** a coleta incremental de 2026 para que o primeiro Boletim da Semana já saia com a sessão de ontem (`17/11/2026`). |
| **D2** | **Motor dos resumos em linguagem simples:** usar tradutor estruturado determinístico (gratuito, zero alucinação, limpa juridiquês da ementa + explica o tipo de matéria + mostra placar) rotulado como *"Resumo automático"*. | **Adotar o motor determinístico** na v1 da Fase 4 (custo R$ 0, auditável e 100% determinístico nos testes). |
| **D3** | **Handle oficial do Instagram do Cerrado Aberto nos cartões:** qual `@handle` exibir no rodapé dos cards gerados para o Instagram? | Usar **`@cerradoaberto`** (ou **`cerradoaberto.org.br`** configurável em constante de município) com a faixa *"Iniciativa cidadã independente — sem vínculo com a Câmara Municipal"*. |
| **D4** | **Modelo de distribuição no WhatsApp:** API oficial da Meta tem custo por mensagem; compartilhamento 1-clique (`Copiar texto` + `wa.me` + download do card PNG para Canal/Comunidade/Grupos) tem custo zero. | **Compartilhamento assistido a 1 clique** (texto <= 400 caracteres + card PNG + link para Canal/Lista do WhatsApp quando você criar o link de convite). |
| **D5** | **Geração da rotina semanal:** deixar comando CLI + script PowerShell agendável no Windows Task Scheduler (`scripts/atualizar-semana.ps1`) que roda a coleta incremental, valida os testes de qualidade/LGPD e atualiza o banco local. | **Aprovar** script local sob seu controle (sem rodar em background sem seu comando ou agendamento explícito). |

---

## 5. Etapas de Implementação (após aprovação)

1. **Etapa 1 — Coletor Incremental Semanal (`apps/coleta`):** implementar e testar `nexlegis/incremental.py` contra fixtures, executar a atualização incremental trazendo a `Sessão Ordinária 044/2026` (`17/11/2026`) e matérias novas para o PostgreSQL 16, com relatório de qualidade.
2. **Etapa 2 — Motor de Resumos em Linguagem Simples e Endpoint de Boletins (`apps/api`):** implementar `resumos.py`, expor `resumo_cidadao` em `/api/v1/materias/{id}` e `/api/v1/sessoes/{id}` e criar `GET /api/v1/boletins/resumo-semanal`, validados por `pytest` (incluindo checagem LGPD e de vocabulário proibido).
3. **Etapa 3 — Página `/boletins`, Resumos na UI e Gerador de Cartões WhatsApp/Instagram (`apps/web`):** construir a central `/boletins`, exibir o bloco *"Resumo automático em linguagem simples"* nas páginas de sessões e matérias, e implementar o gerador de texto WhatsApp (`<= 400 caracteres`) + exportador de cards PNG (`1080×1350` Carrossel de 3 slides e `1080×1920` Stories/Status).
4. **Etapa 4 — Qualidade, Acessibilidade e Capturas (`playwright test` + `ADR-007`):** validar todas as rotas novas no Playwright + `axe-core` (desktop e mobile), gerar capturas dos cartões exportados e da tela `/boletins`, e registrar o `ADR-007`.
