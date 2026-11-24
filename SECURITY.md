# Política de Segurança e Privacidade (LGPD) — Cerrado Aberto

O **Cerrado Aberto** trata exclusivamente de dados públicos oficiais do Poder Legislativo municipal, porém adota o princípio estrito de **minimização e privacidade (LGPD — Lei nº 13.709/2018)** e transparência técnica.

## Escopo deste canal

Reporte imediatamente se você identificar neste repositório, na API ou na interface web:
- Qualquer **CPF completo**, dado bancário pessoal, endereço residencial, telefone particular ou informação sensível exposta acidentalmente em código, fixtures, logs ou respostas da API;
- Qualquer **credencial, chave, token ou arquivo de ambiente** versionado por engano;
- Vulnerabilidades de segurança na API FastAPI (`apps/api`), no proxy ou frontend Next.js (`apps/web`), nas consultas SQL (`db/migrations/` / loaders) ou nos coletores (`apps/coleta`).

## Como reportar

Envie uma descrição objetiva (com o arquivo/URL afetado e passos para reproduzir, sem publicar dados pessoais em issues públicas) para:

- **E-mail de segurança e retificações (homologação):** `firstonetrillion@gmail.com`

> Caso o aviso envolva pedido formal de retificação factual ou direito de resposta de dado público exibido na plataforma, utilize também a página `/correcoes` conforme [`docs/05-etica-legal-editorial.md`](docs/05-etica-legal-editorial.md).

## Controles já implementados no código

- **API estritamente somente leitura:** o backend FastAPI abre conexões PostgreSQL com `conn.read_only = True` e o middleware [`LGPDAndReadOnlyMiddleware`](apps/api/src/cerrado_aberto_api/security.py) bloqueia métodos de escrita na API e no proxy Next.js (`/api/v1/[...path]`).
- **Sanitização e bloqueio LGPD em múltiplas camadas:** validação na ingestão (`validar_ausencia_cpf_em_valores`, `sanitizar_cpf_em_bytes_json`), mascaramento para `***.***.***-**` antes da persistência em banco, filtro de logs (`FiltroLogLGPD`) e varredura automatizada em testes `pytest` e `playwright`.
- **Rate limiting configurável por IP:** [`RateLimitMiddleware`](apps/api/src/cerrado_aberto_api/rate_limit.py) limita requisições excessivas (`CERRADO_RATE_LIMIT_RPM`, padrão `240` req/min).
- **Segredos fora do Git:** variáveis de ambiente locais (`.env`, `.env.*`) e dados brutos locais (`data/`) são bloqueados pelo [`.gitignore`](.gitignore).
