"use client";

import { useState } from "react";
import { HelpCircle } from "lucide-react";

const TERMOS: Record<string, string> = {
  duodecimo:
    "Duodécimo é o repasse mensal obrigatório feito pela Prefeitura para custear o funcionamento da Câmara Municipal. Eventuais sobras devolvidas ao Executivo também aparecem nos lançamentos.",
  empenho:
    "Empenho é o primeiro estágio da despesa pública: reserva parte do orçamento para pagar um fornecedor ou servidor. Pode ser reduzido por anulação.",
  liquidacao:
    "Liquidação é o segundo estágio da despesa: verifica que o bem foi entregue ou o serviço foi prestado antes da liberação do pagamento.",
  pagamento:
    "Pagamento é o terceiro estágio: o repasse efetivo do dinheiro ao favorecido após a liquidação. Os estágios não devem ser somados entre si.",
  ceap:
    "Cota para o Exercício da Atividade Parlamentar (CEAP) é uma verba indenizatória comum em algumas casas legislativas. Em Inhumas, a Câmara declarou oficialmente que essa cota não existe (2020–2026).",
  elemento14:
    "Elemento 14 (Diárias – Civil) é a classificação contábil usada nos empenhos para pagamentos de diárias de deslocamento a vereadores e servidores.",
  subsidio:
    "Subsídio é a remuneração bruta mensal paga ao vereador pelo exercício do mandato, prevista em lei municipal.",
};

interface GlossarioTooltipProps {
  termo: keyof typeof TERMOS;
  label: string;
}

export function GlossarioTooltip({ termo, label }: GlossarioTooltipProps) {
  const [aberto, setAberto] = useState(false);
  const explicacao = TERMOS[termo];

  return (
    <span className="relative inline-flex items-center gap-1 align-baseline">
      <span>{label}</span>
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        aria-label={`Explicar o termo ${label}`}
        className="inline-flex min-w-6 min-h-6 items-center justify-center text-[var(--primary)] hover:opacity-80 rounded-full p-1"
      >
        <HelpCircle className="w-3.5 h-3.5" aria-hidden="true" />
      </button>
      {aberto && (
        <span
          role="note"
          className="absolute left-0 top-full mt-1.5 z-30 w-72 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-xs font-normal text-[var(--ink)] shadow-lg"
        >
          <strong className="block text-[var(--primary)] mb-1">{label}</strong>
          {explicacao}
        </span>
      )}
    </span>
  );
}
