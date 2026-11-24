---
name: qualidade-de-dados
description: Cria testes, métricas e alertas de qualidade para o pipeline de dados públicos (cobertura, contagens, duplicidade, reconciliação de totais, detecção de mudança de layout). Use sempre que adicionar uma tabela ou coletor novo, antes de publicar qualquer indicador, ou quando os números do site divergirem do portal oficial.
---

# Qualidade de dados

## Camadas de teste
1. **Schema:** tipos, obrigatórios, domínios válidos, chaves únicas, integridade referencial.
2. **Volume e frescor:** contagem por execução vs. média histórica (alerta em variação anormal); data do último registro vs. frequência esperada.
3. **Cobertura:** por fonte/entidade, período realmente disponível (publicar "dados desde 20XX"; nunca esconder lacunas).
4. **Reconciliação:** totais do nosso banco vs. totais exibidos pelo portal (amostra por mês/ano), com tolerância documentada e diferenças explicadas.
5. **Consistência cruzada:** ex.: voto sem presença na sessão, despesa sem fornecedor, diária em data fora de mandato.
6. **Regressão de layout:** hash/estrutura do bruto muda → alerta.

## Regras
- Todo indicador publicável tem: definição, fórmula, fonte, período, limitações — em `docs/` e no site ("Como calculamos").
- Testes vivem junto do código (`pytest`/SQL tests) e rodam no CI.
- Falha de qualidade **bloqueia a publicação** do indicador afetado; o site mostra "dado em verificação" em vez de número duvidoso.
- Relatório de qualidade por execução salvo em `coleta_execucao`.

## Entrega
Suite de testes, relatório de cobertura/qualidade legível por humano, e lista de anomalias para revisão.
