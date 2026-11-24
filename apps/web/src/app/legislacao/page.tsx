import type { Metadata } from "next";
import { safeFetchApi } from "@/lib/api";
import type { NormasListagemOut } from "@/lib/types";
import { EstadoAusente } from "@/components/EstadoAusente";
import { LegislacaoClient } from "./LegislacaoClient";

export const metadata: Metadata = {
  title: "Legislação Municipal Pesquisável | Cerrado Aberto",
  description:
    "Consulte leis ordinárias, complementares, Lei Orgânica, LDO, LOA e códigos municipais de Inhumas (GO) com busca em português e link oficial.",
};

export const dynamic = "force-dynamic";

export default async function LegislacaoPage() {
  const { data, error } = await safeFetchApi<NormasListagemOut>("/legislacao", {
    page: 1,
    per_page: 20,
  });

  if (!data) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <EstadoAusente
          titulo="Catálogo de legislação indisponível no momento"
          descricao={error || "Não foi possível carregar as leis municipais."}
        />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10 space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Acervo normativo · Portal da Legislação de Inhumas (GO)
        </p>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-[var(--ink)]">
          Legislação Municipal Pesquisável
        </h1>
        <p className="text-sm sm:text-base text-[var(--ink-muted)] max-w-3xl leading-relaxed">
          Pesquise nas leis municipais cadastradas no portal oficial da Câmara (desde a Lei Orgânica
          de 1990 até as normas de 2026), com resumo automático em linguagem simples e link
          permanente para o texto oficial.
        </p>
      </header>

      <LegislacaoClient inicial={data} />
    </div>
  );
}
