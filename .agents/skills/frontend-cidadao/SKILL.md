---
name: frontend-cidadao
description: Constrói telas, componentes e gráficos do site cidadão (home com 3 perguntas, perfil do vereador, página de gastos, pauta da semana) seguindo a identidade visual e os princípios de acessibilidade do projeto. Use sempre que for criar ou alterar UI, páginas, gráficos ou estilos do apps/web, mesmo que o pedido seja só "faz uma tela de X".
---

# Frontend para o cidadão

Leia `docs/01-produto.md` (identidade e UX). Use a skill `modern-web-guidance` (`GoogleChrome/modern-web-guidance-src`) **em conjunto**, subordinada a este guia, consultando-a no início de qualquer implementação de HTML, CSS, componentes nativos (`<dialog>`, `popover`, tabelas responsivas), modo escuro, acessibilidade e performance (Core Web Vitals).

## Identidade
- Paleta: fundo off-white quente; primária verde-cerrado profundo; acento terra vermelha/laterita; destaque amarelo-ipê. **Evitar** azul-institucional e verde-amarelo literal. Definir como tokens (CSS variables) com suporte a modo escuro.
- Tipografia: títulos com personalidade (Fraunces ou Space Grotesk), corpo Inter, **numerais tabulares** em dados.
- Visual: cartões grandes, muito espaço, gráficos simples (barras/linhas antes de qualquer coisa sofisticada). Fotos de vereadores com o **mesmo tratamento** e mesma ordem (alfabética por padrão).

## UX
- Home responde 3 perguntas: Quem me representa? Para onde vai o dinheiro? O que vai ser votado agora?
- Detalhe pesado (tabelas, CSV, documentos) sempre a **um clique**, nunca na primeira dobra.
- Glossário em tooltip nos termos técnicos; busca em linguagem natural quando disponível.
- **Todo número** mostra fonte, data da coleta e link "Como calculamos".
- Estado "dado em verificação" quando a qualidade bloquear um indicador; nunca número duvidoso.

## Qualidade técnica
- Mobile-first (a maioria acessa pelo celular), conexão lenta tolerada: páginas estáticas/ISR, imagens otimizadas.
- Acessibilidade: contraste AA, navegação por teclado, rótulos para leitor de tela, gráficos com alternativa em texto/tabela.
- Textos via skill `texto-cidadao`.
- Nada de rastreamento invasivo; analytics com privacidade (sem cookies de terceiros).

## Entrega
Componentes reutilizáveis, página/rota funcionando com dados reais ou mock claramente marcado, testes de componente/e2e básicos e captura da tela para revisão humana.
