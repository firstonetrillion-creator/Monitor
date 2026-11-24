# 03 — Fontes de dados

**Estado atual: as 3 fontes principais foram verificadas tecnicamente na Fase 0 (2026-11-12).** Veja as fichas detalhadas em `docs/fontes/<fonte>.md` e as fixtures reais em `apps/coleta/tests/fixtures/<fonte>/`.

## Inventário

| ID | Fonte | URL informada | URL real confirmada | Estado | Ficha |
|---|---|---|---|---|---|
| `transparencia` | Portal da Transparência / Dados Abertos (NúcleoGov + CENTI) | `http://go.leg.br` | `https://acessoainformacao.inhumas.go.leg.br/` (e índice em `https://inhumas.go.leg.br/transparencia/`) | **Coletada para 2026 (Fase 2)** | [transparencia.md](fontes/transparencia.md) |
| `nexlegis` | Sistema de Processo Legislativo (Nexlegis) | `https://nexlegis.com.br` | `https://inhumas.nexlegis.com.br/` (REST API: `https://inhumas.nexlegis.com.br/api/`) | **Coleta 2025–2026 + Incremental semanal (Fases 1 e 4)** | [nexlegis.md](fontes/nexlegis.md) |
| `legislacao` | Leis, decretos, resoluções (NúcleoGov) | `go.leg.br/cidadao/legislacao/leis` | `https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis` (e `/decretos`, `/resolucoes`, `/portarias`) | **Metadados das 407 leis coletados + pipeline PDF/OCR pronto (Fase 5)** | [legislacao.md](fontes/legislacao.md) |
| `siconfi_stn` | SICONFI — Secretaria do Tesouro Nacional (`DCA-Anexo I-E`) | — | `https://apidatalake.tesouro.gov.br/ords/siconfi/tt` | **Coletada para 2024 e 2025 — Inhumas + 7 pares GO (Fase 5)** | [ADR-008](decisoes/ADR-008-aprofundamento-busca-bairros-legislacao-comparativo.md) |
| `pncp` | Portal Nacional de Contratações Públicas | — | — | Candidata (verificação cruzada) | — |
| `tcm_go` | Tribunal de Contas dos Municípios de Goiás | — | — | Candidata | — |
| `tse` | Dados eleitorais / doações | — | — | Candidata (necessária p/ filiação partidária estruturada) | — |
| `querido_diario` | Diário oficial (Open Knowledge Brasil) | — | — | Candidata | — |
| `receita_cnpj` | Dados abertos de CNPJ | — | — | Candidata (enriquecer fornecedores) | — |

## Template da ficha de fonte (`docs/fontes/<fonte>.md`)

```
# Ficha — <fonte>
- Data do reconhecimento / quem (agente) / versão
## 1. Acesso
- URL(s) de listagem e detalhe; exige JS? sessão? CAPTCHA? login?
- robots.txt e termos de uso (resumo, com link)
- Existe API, exportação CSV/XML/JSON, "dados abertos"? Onde?
## 2. Mecânica
- Como funciona a paginação/filtros (parâmetros, ViewState, XHR). Anexar exemplo de requisição (sem segredos).
- Rate limit observado; latência; horários de instabilidade
## 3. Conteúdo
- Entidades disponíveis e campos (nome, tipo, exemplo, % de preenchimento)
- Histórico disponível (desde quando) e lacunas
- Frequência de atualização; edição retroativa observada?
## 4. Qualidade
- Formatos de data/valor, encoding, duplicidades, nomes variantes
## 5. Amostras
- Caminho das fixtures salvas em apps/coleta/tests/fixtures/<fonte>/
## 6. Estratégia recomendada
- HTTP direto / XHR JSON / Playwright / download em lote / pedido via LAI — e por quê
## 7. Riscos e perguntas em aberto
```

## Pedido formal via LAI (a cargo do responsável humano)
Solicitar à Câmara as bases em formato aberto (CSV/JSON) das categorias acima, especialmente o acervo histórico pré-migração SIGEP → CENTI (anterior a 2026). Versão final pronta para protocolo pessoal em [pedido-lai-final.md](fase-0/pedido-lai-final.md) (e rascunho em [pedido-lai-rascunho.md](fase-0/pedido-lai-rascunho.md)).
