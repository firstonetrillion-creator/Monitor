# Contribuindo com o Cerrado Aberto

Obrigado pelo interesse em revisar, propor ideias ou contribuir com o **Cerrado Aberto** (`cerradoaberto.org.br`). Este repositório aceita contribuições técnicas de pessoas desenvolvedoras, jornalistas de dados, pesquisadoras e agentes de IA assistidos por humanos.

## 1. Leitura Obrigatória Antes de Abrir um PR

1. [`AGENTS.md`](AGENTS.md) — missão, princípios inegociáveis, convenções e definição de pronto.
2. [`docs/BRIEFING-PARA-AGENTES.md`](docs/BRIEFING-PARA-AGENTES.md) — mapa completo do código, síntese das ADRs e dívidas técnicas atuais.
3. [`docs/04-roadmap.md`](docs/04-roadmap.md) — **regra de fase ativa**: não abra mudanças de arquitetura, esquema de banco ou coleta em lote fora da fase aprovada sem discussão prévia.
4. [`docs/05-etica-legal-editorial.md`](docs/05-etica-legal-editorial.md) — regras editoriais e de privacidade (LGPD).

## 2. Convenções do Projeto

- **Idioma:** documentação, mensagens de UI e textos para o cidadão em **português do Brasil (PT-BR)** claro e sem juridiquês; código, commits e infraestrutura em inglês; entidades de domínio em **português sem acento** (`vereador`, `proposicao`, `sessao`, `empenho`, `norma`, `bairro`), em `snake_case`.
- **Commits:** siga [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`).
- **Neutralidade editorial:** textos voltados ao público não podem conter acusações, rankings sensacionalistas nem vocabulário proibido (`fraude`, `desvio`, `esquema`, `irregular`, `suspeito`, `escândalo`, `absurdo`, `farra`, `mamata`).
- **Privacidade (LGPD):** nunca armazene, registre em log ou exponha CPF completo (`XXX.XXX.XXX-XX`), endereço residencial ou dados bancários pessoais.
- **Multi-município:** nunca fixe regras, chaves ou tabelas assumindo apenas Inhumas/GO sem parâmetro `municipio_id`.
- **Coleta educada:** coletores novos exigem ficha prévia em `docs/fontes/`, fixtures reais em `apps/coleta/tests/fixtures/`, `Crawl-Delay` respeitando `robots.txt` e zero contorno de CAPTCHA ou autenticação.

## 3. Checklist Obrigatório Antes de Enviar Mudanças

Execute localmente (e garanta que o workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) passe):

```bash
node scripts/validate-docs.mjs
uv run --directory apps/coleta ruff check src tests
uv run --directory apps/coleta pytest -q tests/test_nexlegis_pipeline.py tests/test_regras_negocio_adr005.py tests/test_nexlegis_incremental.py tests/test_transparencia_2026.py tests/test_fase5_coleta.py -k "not persistencia_bairros_e_normas and not persistencia_postgres_transparencia_2026"
uv run --directory apps/api ruff check src tests
uv run --directory apps/api pytest -q tests/test_boletins_e_resumos.py -k "not endpoint_boletim_semanal"
npm --prefix apps/web run lint
npm --prefix apps/web run build
```

Se houver mudança de arquitetura ou regra de negócio relevante, crie um novo ADR em [`docs/decisoes/`](docs/decisoes/) em vez de reverter decisões anteriores silenciosamente.

## 4. Licença

Este repositório está **sem licença open-source definida por enquanto**. A escolha e adoção da licença definitiva ocorrerão na abertura da **Fase 6 (Replicação)**. Até lá, todos os direitos sobre o código-fonte permanecem reservados, sendo o repositório disponibilizado para auditoria, revisão e discussão técnica.
