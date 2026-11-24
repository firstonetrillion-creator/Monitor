# Relatório da Fase 4 — Distribuição Cidadã, Resumos em Linguagem Simples e Atualização Semanal

> **Projeto:** Cerrado Aberto (`cerradoaberto.org.br`) — Plataforma Cidadã Independente de Transparência Legislativa  
> **Escopo:** Fase 4 (*Distribuição e retenção*) implementada e validada em homologação (`apps/coleta` + `apps/api` + `apps/web` + `scripts/atualizar-semana.ps1`)  
> **Data:** 18/11/2026  
> **Decisões relacionadas:** [ADR-007](../decisoes/ADR-007-distribuicao-resumos-e-atualizacao-semanal.md) · [Plano da Fase 4](plano-distribuicao-e-retencao.md)

---

## 1. Atualização Incremental Semanal (`apps/coleta` — D1 e D5)

- **Implementação:** [incremental.py](../../apps/coleta/src/cerrado_aberto_coleta/nexlegis/incremental.py) + testes em [test_nexlegis_incremental.py](../../apps/coleta/tests/test_nexlegis_incremental.py) + script operacional [atualizar-semana.ps1](../../scripts/atualizar-semana.ps1).
- **1ª execução semanal autorizada (18/11/2026, UTC `2026-11-19T00:55:48Z` / Goiás `18/11/2026 21:55`):**
  - `execucao_id`: `6d9b5d8d-3bb1-4899-8639-90555fba9beb`
  - **Coleta educada:** `robots.txt` validado (`robots_txt_permite_coleta: true`), `12` requisições HTTP no total com intervalo mínimo de `3,0s` e `0` CPFs expostos (`cpfs_mascarados_total: 0`).
  - **Bruto imutável e manifesto:** payloads armazenados por SHA-256 em `data/raw/inhumas-go/nexlegis/2026/` e manifesto auditável em `data/raw/inhumas-go/nexlegis/incremental/2026-11-19/manifesto_6d9b5d8d-3bb1-4899-8639-90555fba9beb.json`.
  - **Delta incorporado no PostgreSQL 16 (`data/pgdata`):**
    - **Sessão nova:** `Sessão Ordinária 044/2026` (`17/11/2026`, `id_origem_nexlegis = 1035`, `13` presentes, `2` ausentes, `11` proposições parlamentares + `1` ata = `12` itens em pauta, destaque `PROJETO DE LEI DO LEGISLATIVO 026/2026`).
    - **Totais persistidos atualizados:** `134` sessões (`+1`), `2.010` registros de presença (`+15`), `1.311` proposições (`+16`), `1.692` itens de pauta (`+12`), `1.613` votações (`+13`) e `290` documentos brutos (`+7`).

### Como executar ou agendar semanalmente no Windows

```powershell
# Execução manual completa (coleta incremental + validação de qualidade e LGPD):
.\scripts\atualizar-semana.ps1 -MunicipioId inhumas-go -Ano 2026

# Execução apenas da coleta incremental (sem rodar a suíte de validação ao final):
.\scripts\atualizar-semana.ps1 -MunicipioId inhumas-go -Ano 2026 -PularTestes
```

> Para automatizar toda quarta-feira às 08h (após as sessões ordinárias de terça-feira), crie uma tarefa no **Agendador de Tarefas do Windows** executando `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<CAMINHO_DO_REPOSITORIO>\scripts\atualizar-semana.ps1"`.

---

## 2. Motor Determinístico de Resumos em Linguagem Simples e Endpoint de Boletins (`apps/api` — D2)

- **Motor:** [resumos.py](../../apps/api/src/cerrado_aberto_api/resumos.py) — custo `R$ 0`, 100% determinístico e auditável:
  - Traduz o tipo oficial da matéria (*Requerimento*, *Indicação*, *Projeto de Lei do Legislativo/Executivo*, *Moção*, *Ata*) em português claro;
  - Limpa preâmbulos burocráticos repetitivos e caixa alta excessiva preservando siglas oficiais (`SUS`, `UBSF`, `GO-070`, `IBGE`, `CEAP`, `LGPD` etc.) e corrigindo verbo inicial duplicado na fonte oficial (ex.: `"SOLICITA SOLICITAM..."`);
  - Formata datas de coleta no fuso oficial de Goiás (`UTC-3`) e trunca textos em limites de palavras com reticências (`…`);
  - Carrega obrigatoriamente `rotulo_transparencia = "Resumo automático gerado a partir dos registros oficiais — confira sempre o documento original."`, `metodo_geracao = "AUTOMATICO_DETERMINISTICO"`, `revisado_por_humano = false` e `fonte_url` oficial;
  - Verifica neutralidade editorial (`0` ocorrências de vocabulário proibido conforme `docs/05-etica-legal-editorial.md` e skill `texto-cidadao`).
- **Endpoints FastAPI v1 (somente leitura `GET`):**
  - `GET /api/v1/boletins/resumo-semanal` ([boletins_router.py](../../apps/api/src/cerrado_aberto_api/boletins_router.py)): retorna o boletim da sessão mais recente (ou de qualquer `sessao_id`), com alerta WhatsApp estritamente `<= 400` caracteres (`291/400` na Sessão `044/2026`), legenda pronta para o Instagram Oficial `@cerradoaberto`, 3 slides estruturados, lista de proposições em linguagem simples e panorama financeiro 2026 (`R$ 16,39 / hab. / mês`, `R$ 8.873.608,80` pagos em 10 meses).
  - `GET /api/v1/sessoes/{id}` e `GET /api/v1/materias/{id}`: agora acoplam o objeto `resumo_cidadao` diretamente na resposta.

---

## 3. Central `/boletins`, Alertas WhatsApp e Cartões PNG do Instagram Oficial (`apps/web` — D3 e D4)

- **Central de distribuição:** [boletins/page.tsx](../../apps/web/src/app/boletins/page.tsx) e [BoletinsClient.tsx](../../apps/web/src/app/boletins/BoletinsClient.tsx).
- **Resumos em linguagem simples nas páginas existentes:** [ResumoCidadaoBox.tsx](../../apps/web/src/components/ResumoCidadaoBox.tsx) exibido no topo de `/sessoes/[id]` e `/materias/[id]`, com botão direto *"Gerar alerta WhatsApp e cards Instagram desta sessão"*.
- **Cópia acessível (WCAG):** [BotaoCopiar.tsx](../../apps/web/src/components/BotaoCopiar.tsx) implementado segundo `modern-web-guidance` (`copy-button`), com região `aria-live="polite"` externa ao botão, foco preservado durante feedback (sem `disabled`) e dedup de anúncios repetidos via `\u00A0`.
- **Gerador client-side de cartões PNG (`Canvas 2D`, custo zero):** [cardCanvas.ts](../../apps/web/src/lib/cardCanvas.ts):
  - **Carrossel Feed (`1080×1350`, 3 slides PNG):** Slide 1 (Resumo da Sessão), Slide 2 (Principais propostas em linguagem simples), Slide 3 (Panorama financeiro 2026 — `R$ 16,39 / hab. / mês`, duodécimo, devoluções, IBGE e CEAP inexistente);
  - **Story / Status (`1080×1920`, PNG vertical único):** resumo pronto para Stories do Instagram Oficial `@cerradoaberto` e Status do WhatsApp;
  - Todos os cartões trazem a paleta oficial do Cerrado Aberto (`#FAF7F2`, `#1F4E3D`, `#B44B2A`, `#D99B16`), selo *"Resumo automático · Sem vínculo com a Câmara Municipal de Inhumas"*, fonte, data da coleta (`18/11/2026`), `@cerradoaberto` e `cerradoaberto.org.br`.
- **Navegação integrada:** links para `/boletins` e `@cerradoaberto` adicionados em `SiteHeader.tsx`, `SiteFooter.tsx`, `/sobre` e destaque na Página Inicial (`/`).

---

## 4. Matriz de Verificação Automatizada (Executada em 18/11/2026)

| Camada / Comando | Resultado | Cobertura verificada |
|---|---|---|
| `uv run --directory apps/coleta ruff check src tests` | **PASS** (`0` erros) | Padrões Python/PEP 8 e tipagem em `apps/coleta` |
| `uv run --directory apps/coleta pytest -q` | **PASS (`21 passed` em 56,05s)** | Incremental semanal (fixtures, idempotência, LGPD, layout quebrado), persistência PostgreSQL 16 (`134` sessões / `1.311` proposições), Transparência 2026 e Custo do Mandato |
| `uv run --directory apps/api ruff check src tests` | **PASS** (`0` erros) | Padrões Python/FastAPI em `apps/api` |
| `uv run --directory apps/api pytest -q` | **PASS (`11 passed` em 26,19s)** | Todos os endpoints v1, `/api/v1/boletins/resumo-semanal`, `resumo_cidadao`, limite `<= 400` chars WhatsApp, neutralidade editorial, fuso Goiás, OpenAPI e sanitização LGPD |
| `npm --prefix apps/web run lint` | **PASS** (`0` erros, `0` avisos) | ESLint + regras de qualidade/tamanho de arquivo em `apps/web` |
| `npm --prefix apps/web run build` | **PASS** (`17` rotas, TypeScript limpo) | Build de produção Next.js 16.4.6 (Turbopack) |
| `npm --prefix apps/web run test:e2e` | **PASS (`16 passed` em 1,1m)** | `8` testes desktop (`1280×800`) + `8` testes mobile (`390×844`) no Chromium: `0` violações críticas/sérias `axe-core` WCAG 2.1 A/AA, `0` CPF completo, `0` palavras proibidas, `0` overflow horizontal mobile, download verificado dos 3 slides PNG (`1080×1350`) e Story PNG (`1080×1920`) |

---

## 5. Capturas e Cartões PNG Gerados

Todos os arquivos gerados durante a validação estão em `docs/fase-4/capturas/` (25 arquivos PNG):
- `13-boletins-desktop.png` e `13-boletins-mobile.png`: Central `/boletins` com Sessão Ordinária `044/2026`, alerta WhatsApp (`291/400 caracteres`), legenda Instagram Oficial `@cerradoaberto`, pré-visualização dos 3 slides e lista das 11 proposições em linguagem simples.
- `08-sessao-detalhe-desktop.png`: `/sessoes/inhumas-go-sessao-1035` exibindo o novo bloco *"Resumo automático da sessão em linguagem simples"* e o atalho para `/boletins`.
- `card-instagram-slide-1-1080x1350.png`, `card-instagram-slide-2-1080x1350.png`, `card-instagram-slide-3-1080x1350.png` e `card-instagram-story-1080x1920.png`: cartões PNG exportados diretamente pelo gerador Canvas 2D do navegador e inspecionados visualmente.

---

## 6. Transparência sobre Limitações e Próximos Passos

1. **Verificação via browser do Portal da Transparência (`acessoainformacao.inhumas.go.leg.br`):** durante a checagem pré-implementação por subagente de navegador, o subagente confirmou `GET /api/sessoes` (`HTTP 200`, `Sessão Ordinária 044/2026` de `17/11/2026`) no Nexlegis, mas sofreu timeout interno de IPC do webview antes de abrir `acessoainformacao.inhumas.go.leg.br`. Portanto, a folha/despesas de **novembro/2026** ainda não foi checada no portal CENTI e permanece como pendência natural da próxima coleta mensal da Transparência (prevista após o fechamento de novembro/2026).
2. **Operação pelo responsável:** publicar os primeiros cartões no `@cerradoaberto`, criar (quando desejar) o Canal/Comunidade no WhatsApp para compartilhar o alerta semanal e agendar `scripts/atualizar-semana.ps1` para acompanhamento da métrica de **retorno semanal**.
