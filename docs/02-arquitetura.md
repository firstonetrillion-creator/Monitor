# 02 — Arquitetura

## Visão em camadas
```
Fontes oficiais → [Coletores (apps/coleta)] → BRUTO (data/raw/ SHA-256, imutável)
                                           → TRATADO (PostgreSQL 16, migrações 0001–0003)
                                           → ANALÍTICO (views e tabelas derivadas documentadas)
                                           → API (FastAPI v1 — 21 endpoints GET somente leitura)
                                           → Web (Next.js 16) / Boletins WhatsApp & Instagram / Dados abertos
```

## Stack consolidada (`ADR-001` a `ADR-008`)
| Camada | Escolha implementada | Nota |
|---|---|---|
| Coleta | Python 3.12 + `uv`, `httpx`, `pydantic` | Sessão Playwright apenas quando JS/sessão é indispensável (ex.: [`scripts/coletar-legislacao-leis.mjs`](../scripts/coletar-legislacao-leis.mjs)); nunca contorna CAPTCHA |
| PDF e OCR | `pdfplumber` + Tesseract OCR (`por`) + `pypdfium2` | Pipeline híbrido em [`ocr.py`](../apps/coleta/src/cerrado_aberto_coleta/legislacao/ocr.py) com fallback seguro (`PENDENTE_OCR`) e revisão humana sinalizada |
| Bruto | Armazenamento local versionado em `data/raw/` (SHA-256) via protocolo `StorageBackend` | Pronto para migração S3-compatível (`ADR-005`); download imediato de links temporários S3 preservando URL canônica pública |
| Banco | PostgreSQL 16 (portátil via `pgserver` em `data/pgdata` ou externo via `DATABASE_URL`) | Migrações SQL versionadas `0001`–`0003`; Full-Text Search `portuguese` com função `IMMUTABLE` `normalizar_texto_busca(TEXT)` e 5 índices GIN (sem depender de extensões contrib) |
| Qualidade & Normalização | Python determinístico + `pytest` contra fixtures reais | Resolução curada de vereadores/aliases, extração determinística de 52 bairros, reconciliação de totais e checagem estrita LGPD (`0` CPF completo) |
| Automação local | Script PowerShell [`scripts/atualizar-semana.ps1`](../scripts/atualizar-semana.ps1) + launcher [`CerradoAbertoLauncher.cs`](../scripts/launcher/CerradoAbertoLauncher.cs) | Coleta incremental semanal do Nexlegis sob controle do responsável; CI automatizado em `.github/workflows/ci.yml` |
| API | FastAPI + `uvicorn` + `psycopg` (conexões `read_only = True`) | 21 endpoints `GET` somente leitura, documentação OpenAPI em `/docs`, sanitização LGPD e rate limiting configurável por IP (`CERRADO_RATE_LIMIT_RPM`) |
| Web | Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS 4 + Observable Plot | 23 rotas, proxy `GET`-only `/api/v1/[...path]`, mapa vetorial SVG local (`/bairros`), gerador Canvas 2D local de cards PNG (`/boletins`) e E2E Playwright + `axe-core` WCAG 2.1 A/AA |
| Produção (próxima etapa) | VPS / Fly.io + PostgreSQL 16 gerenciado | A ser desenhado na Fase 6 após validação jurídica e de usuários |

## Modelo de dados conceitual (nomes de domínio em português)
Toda tabela de fato carrega: `municipio_id`, `fonte_id`, `fonte_url`, `coletado_em`, `hash_conteudo`, `versao_coletor`, e `valido_de`/`valido_ate` quando o dado puder ser editado retroativamente.

- **Estrutura (`0001`):** `municipio`, `casa_legislativa`, `legislatura`, `partido`, `fonte`, `coleta_execucao`, `documento_bruto`, `lacuna_historica`
- **Pessoas (`0001`):** `vereador` (ID próprio, chave normalizada), `vereador_alias`, `mandato`
- **Atividade legislativa (`0001` e `0003`):** `de_para_tipo_proposicao`, `sessao`, `presenca`, `proposicao` (separa proposições parlamentares de atas e julgamentos administrativos), `autoria`, `tramitacao`, `pauta_item`, `votacao`, `voto`, `norma` (leis municipais com status OCR), `bairro`, `proposicao_bairro`
- **Finanças (`0002` e `0003`):** `fornecedor` (CNPJ ou documento mascarado `***.***.***-**`), `folha_pagamento` (sem CPF), `despesa_empenho` (empenhado, anulado, liquidado, pago), `diaria`, `receita_duodecimo` (repasses e devoluções), `declaracao_oficial_transparencia`, `comparativo_legislativo_siconfi` (Função `01 - Legislativa`, `DCA-Anexo I-E`)
- **Derivados (`0002`):** `custo_estrutura_mandato_mensal` (`Subsídio Bruto + Folha Bruta do Gabinete + Diárias Atribuíveis`, preservando `NULL` em lacunas como `PRESIDENCIA` e competências em aberto)

## Desafios conhecidos e respostas
| Desafio | Resposta |
|---|---|
| Paginação dinâmica, APIs WCF e formulários POST | Reproduzir requisições XHR (`POST /api` e `POST /api/centi`) com `httpx`; sessão Playwright como plano B apenas em fluxos sem login/CAPTCHA |
| Mudança silenciosa de layout | Testes de contrato/schema (`LayoutQuebradoError`, `LayoutLegislacaoAlteradoError`), reconciliação de totais e bruto SHA-256 preservado |
| Edição retroativa pela Câmara | Versionamento idempotente em reexecuções e exibição da última coleta por fonte em `/api/v1/health` |
| Resolução de entidades (nomes variantes) | Tabela mestre `vereador` + `vereador_alias` curada; catálogo canônico de `bairro` com bloqueio de falsos positivos; CNPJ como chave para fornecedores PJ |
| Dados sujos (R$ como texto, datas mistas, encoding) | Camada pura de normalização (`normalizacao.py`) com regras unitariamente testadas e preservação estrita de `NULL` |
| PDFs escaneados e URLs S3 temporárias | Download imediato do PDF bruto, registro da URL canônica permanente (`/legislacao/lei/id={id}`) e pipeline híbrido `pdfplumber` + Tesseract OCR |
| Histórico incompleto | Tabela `lacuna_historica`, página `/cobertura-e-limitacoes` e pedido formal via LAI (`docs/fase-0/pedido-lai-final.md`) |
| Limites legais/éticos da coleta | `robots.txt`, `Crawl-Delay >= 3,0s` (Nexlegis) / `>= 5,0s` (Transparência/Legislação), `User-Agent` identificável e zero contorno de CAPTCHA |
| LGPD e acesso público | Mascaramento preventivo em ingestão/banco/API (`FiltroLogLGPD`, `LGPDAndReadOnlyMiddleware`), zero CPF completo e rate limiting por IP |
| Acessibilidade e custo zero | WCAG 2.1 A/AA verificada via `@axe-core/playwright`, tabelas HTML + CSV para todo gráfico, resumos determinísticos sem LLM paga e cards PNG em Canvas 2D local |

## Observabilidade mínima
Log estruturado por execução de coleta (`coleta_execucao` + manifestos JSON em `data/raw/`): início, fim, registros lidos, status e hash dos documentos brutos; `/api/v1/health` expõe contagens persistidas, última coleta por fonte e lacunas documentadas.
