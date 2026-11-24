# Tarefa — Fase 0: Reconhecimento das fontes

**Skill principal:** `reconhecimento-de-fonte`
**Contexto:** `docs/03-fontes-de-dados.md`, `docs/05-etica-legal-editorial.md`

## Objetivo
Para cada fonte (`transparencia`, `nexlegis`, `legislacao`), descobrir com evidência como coletar, o que existe, desde quando e quais riscos, **sem escrever coletor ainda**.

## Escopo e limites
- Apenas requisições de reconhecimento (dezenas, não milhares), intervalo ≥ 2s, User-Agent identificável.
- Respeitar `robots.txt`/termos; parar e reportar diante de CAPTCHA/login.
- Nenhum dado pessoal armazenado além do necessário para a amostra (mascarar CPF).

## Passos
1. Validar as URLs informadas (a de legislação foi passada malformada). Registrar a URL correta.
2. Procurar primeiro canais abertos (dados abertos, CSV/XML/JSON, API, RSS, sitemap).
3. Mapear listagem → detalhe → anexos; documentar paginação/filtros e a requisição mínima reproduzível.
4. Medir conteúdo, histórico, frequência de atualização, qualidade e sinais de edição retroativa.
5. Salvar fixtures pequenas em `apps/coleta/tests/fixtures/<fonte>/`.
6. Preencher `docs/fontes/<fonte>.md` (template em `docs/03`) e atualizar a tabela de inventário.
7. Recomendar a estratégia de coleta por fonte e abrir ADR (`docs/decisoes/ADR-00X-estrategia-<fonte>.md`).
8. Redigir o **rascunho** do pedido formal via LAI (o humano protocola).
9. Redigir o roteiro de entrevistas (8–10 pessoas de Inhumas) com perguntas abertas sobre o que querem saber da Câmara.
10. Propor shortlist de nomes (Clareira, Vidraça, Cerrado Aberto + 2 alternativas) com checagem de disponibilidade de domínio e handles.

## Entrega (formato do relatório final)
- Resumo executivo (máx. 15 linhas): estado de cada fonte e a recomendação principal
- Links para as fichas, fixtures, ADRs e rascunhos
- Lista de riscos, suposições `[SUPOSIÇÃO]` e perguntas abertas para o responsável
- Proposta de escopo e critérios de aceite da Fase 1

## Critério de aceite
Para cada fonte sabemos *como* coletar, *o que* há, *desde quando* e *quais riscos* — com evidência. Nenhum coletor em volume foi executado.
