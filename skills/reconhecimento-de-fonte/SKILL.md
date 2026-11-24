---
name: reconhecimento-de-fonte
description: Investiga tecnicamente uma fonte de dados públicos (portal da transparência, Nexlegis, página de legislação, qualquer site de câmara/prefeitura) ANTES de escrever um coletor. Use sempre que for começar a coletar de uma fonte nova, quando um coletor quebrar por mudança de layout, ou quando alguém perguntar "como esse portal funciona", "tem API?", "como paginar?", mesmo que não peçam um "reconhecimento" explicitamente.
---

# Reconhecimento de fonte

Objetivo: descobrir **como** coletar, **o que** existe e **quais riscos** há, com evidência, antes de qualquer código de coleta. Saída: ficha em `docs/fontes/<fonte>.md` (template em `docs/03-fontes-de-dados.md`) + fixtures pequenas.

## Regras
- Tráfego de reconhecimento **mínimo**: poucas requisições, intervalo ≥ 2s, User-Agent identificável. Nada de varredura ampla.
- Respeite `robots.txt` e termos de uso; registre o resumo com link.
- Não burle CAPTCHA/login. Se houver, pare e reporte.
- Não invente: tudo na ficha precisa de evidência (URL, trecho de resposta, captura).

## Procedimento
1. **Verificar a URL base** e variações (http/https, www, barras). Registre redirecionamentos e a URL correta.
2. **Procurar canais oficiais abertos primeiro:** "dados abertos", exportação CSV/XML/JSON, API, feed RSS, sitemap. Se existir, prefira-os a raspar HTML.
3. **Mapear a navegação:** páginas de listagem → detalhe → anexos (PDF). Anote parâmetros de URL, filtros, ordenação.
4. **Entender a paginação:** query string? POST com ViewState/token? XHR devolvendo JSON? Identifique a requisição mínima que reproduz cada página (use inspeção de rede: copie como cURL, remova cookies/segredos desnecessários).
5. **Medir o conteúdo:** entidades e campos disponíveis, exemplos, % de preenchimento, menor e maior data (histórico), frequência de atualização, sinais de edição retroativa.
6. **Observar qualidade:** formatos de data/valor, encoding, duplicidade, variações de nome.
7. **Salvar fixtures** em `apps/coleta/tests/fixtures/<fonte>/` (uma por tipo de página/variação; anonimizar se necessário; tamanho pequeno).
8. **Recomendar estratégia:** HTTP direto, XHR/JSON, download em lote, Playwright (justifique), ou pedido formal via LAI.
9. **Listar riscos e perguntas em aberto** para o responsável humano.

## Saída esperada
- `docs/fontes/<fonte>.md` completa (todas as seções do template)
- Fixtures salvas e listadas
- Atualização da tabela de inventário em `docs/03-fontes-de-dados.md`
- Se houve decisão (ex.: "usar XHR em vez de Playwright"), um ADR em `docs/decisoes/`
