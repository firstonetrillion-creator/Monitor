import type { Metadata } from "next";
import { safeFetchApi } from "@/lib/api";
import type { ComparativoSiconfiOut } from "@/lib/types";
import { EstadoAusente } from "@/components/EstadoAusente";
import { ComparativoClient } from "./ComparativoClient";

export const metadata: Metadata = {
  title: "Comparativo com Municípios Semelhantes de Goiás | Cerrado Aberto",
  description:
    "Compare de forma neutra a despesa legislativa de Inhumas com municípios goianos de porte populacional semelhante usando dados oficiais do SICONFI/Tesouro Nacional.",
};

export const dynamic = "force-dynamic";

export default async function ComparativoPage() {
  const { data, error } = await safeFetchApi<ComparativoSiconfiOut>("/comparativo", { ano: 2025 });

  if (!data) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <EstadoAusente
          titulo="Comparativo intermunicipal indisponível no momento"
          descricao={error || "Não foi possível carregar os dados oficiais do SICONFI."}
        />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10 space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Contexto regional · SICONFI / Secretaria do Tesouro Nacional
        </p>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-[var(--ink)]">
          Comparativo com Cidades Semelhantes de Goiás
        </h1>
        <p className="text-sm sm:text-base text-[var(--ink-muted)] max-w-3xl leading-relaxed">
          Dados contábeis oficiais da <strong>Função 01 (Legislativa)</strong> declarados ao
          Tesouro Nacional por Inhumas e por 7 municípios goianos de faixa populacional próxima —
          apresentados com contexto e sem juízo de valor.
        </p>
      </header>

      <ComparativoClient inicial={data} />
    </div>
  );
}
