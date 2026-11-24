---
name: normalizacao-e-entidades
description: Limpa e normaliza dados públicos brasileiros (valores em R$, datas, encoding, CNPJ/CPF, nomes) e unifica entidades duplicadas como vereadores e fornecedores. Use sempre que for transformar dados brutos em tratados, criar tabela mestre de pessoas/fornecedores, resolver nomes variantes ("Dr. João", "João da Silva") ou lidar com categorias inconsistentes entre anos.
---

# Normalização e resolução de entidades

## Normalização
- **Valores:** "R$ 1.234,56" → `NUMERIC(14,2)`; nunca float. Guardar o texto original no bruto.
- **Datas:** converter para ISO 8601; registrar formato de origem; fuso `America/Sao_Paulo`; datas inválidas viram `NULL` + flag, nunca inventadas.
- **Texto:** UTF-8, trim, normalização Unicode (NFC), espaços duplicados; preservar acento (acento só é removido em chaves de busca derivadas).
- **Documentos:** CNPJ só dígitos + validação de dígito verificador; **CPF nunca armazenado completo** (mascarar `***.123.456-**` ou descartar).
- **Categorias:** mapear rótulos antigos/novos para um vocabulário controlado em tabela (`de_para_*`), versionado e documentado.

## Resolução de entidades
- **Vereador:** ID próprio (`vereador_id`). Nomes/apelidos em `vereador_alias`. Resolução **curada manualmente** (volume pequeno), com tabela de mapeamento revisável e registro de quem/quando decidiu.
- **Fornecedor:** chave = CNPJ quando existir; pessoas físicas por hash do documento com sal **ou** nome normalizado + flag de baixa confiança. Enriquecer razão social/CNAE com dados abertos da Receita.
- **Sem fusão automática silenciosa:** similaridade de nome (`pg_trgm`) só **sugere**; fusão exige regra explícita ou aprovação.
- Toda fusão é reversível (guardar IDs originais).

## Entrega
Funções puras e testadas (casos reais e de borda), tabelas `de_para_*`, documentação das regras em `docs/` e relatório de entidades de baixa confiança para revisão humana.
