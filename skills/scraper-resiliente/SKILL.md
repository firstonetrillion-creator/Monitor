---
name: scraper-resiliente
description: Implementa ou altera coletores (scrapers/ingestão) de dados públicos com proveniência, idempotência, retentativas e testes contra fixtures reais. Use sempre que for escrever, corrigir ou refatorar um coletor, parser de HTML/JSON/PDF ou rotina de ingestão, mesmo que o pedido seja só "pega os dados de X".
---

# Scraper resiliente

Pré-requisito: existe ficha em `docs/fontes/<fonte>.md`. Se não existir, use primeiro `reconhecimento-de-fonte`.

## Arquitetura de um coletor (em `apps/coleta/`)
Separe **três etapas** independentes:
1. **Fetch:** baixa e grava o **bruto** (HTML/JSON/PDF) com `fonte_url`, `coletado_em`, `hash_conteudo`, status HTTP. Nunca transforma.
2. **Parse:** lê o bruto → registros estruturados. Pode ser reexecutado sem rede.
3. **Load:** grava no PostgreSQL de forma idempotente (upsert por chave natural + versionamento quando o conteúdo mudar).

## Regras
- **Educado:** `robots.txt`, taxa baixa e configurável, User-Agent com contato, cache por hash/ETag/If-Modified-Since, backoff exponencial com jitter, limite de tentativas.
- **Idempotente:** reexecutar não duplica. Mudança de conteúdo gera nova versão (`valido_de`/`valido_ate`), não sobrescreve.
- **Resiliente a layout:** seletores centralizados em um módulo por fonte; ao falhar, erro claro com URL e hash do bruto (nunca gravar lixo silenciosamente).
- **Validação de schema** na saída do parse (ex.: Pydantic): campo obrigatório ausente = falha da coleta daquele item, registrada.
- **Registro de execução:** cada run grava em `coleta_execucao` (início, fim, lidos/novos/alterados/erros, versão do coletor).
- **`municipio_id` obrigatório**, vindo de configuração. Nada de constantes de Inhumas no código.
- **Playwright só como fallback** e com justificativa em ADR.
- **Sem dados pessoais desnecessários** (mascarar CPF na entrada do pipeline).

## Testes (obrigatórios)
- Parser testado contra **fixtures reais** (todas as variações de layout conhecidas).
- Teste de idempotência (rodar duas vezes → mesmo estado).
- Teste de "layout quebrado" (fixture adulterada → falha explícita, não lixo).
- Sem teste que acesse a internet; rede só em marcadores `@integration` manuais.

## Entrega
Código + testes + atualização da ficha da fonte + nota no `docs/04-roadmap.md` (checklist) + resumo com riscos.
