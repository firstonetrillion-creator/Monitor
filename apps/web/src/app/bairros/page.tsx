import type { Metadata } from "next";
import { safeFetchApi } from "@/lib/api";
import type { BairroDetalheOut, BairrosPainelOut } from "@/lib/types";
import { EstadoAusente } from "@/components/EstadoAusente";
import { BairrosClient } from "./BairrosClient";

export const metadata: Metadata = {
  title: "Mapa de Indicações e Requerimentos por Bairro | Cerrado Aberto",
  description:
    "Veja quais bairros, setores e distritos de Inhumas (GO) aparecem nos requerimentos e projetos de lei da Câmara Municipal.",
};

export const dynamic = "force-dynamic";

export default async function BairrosPage() {
  const { data: painel, error } = await safeFetchApi<BairrosPainelOut>("/bairros");
  if (!painel) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <EstadoAusente
          titulo="Mapa por bairros indisponível no momento"
          descricao={error || "Não foi possível carregar os dados geográficos das proposições."}
        />
      </div>
    );
  }

  let detalheInicial: BairroDetalheOut | null = null;
  if (painel.bairros.length > 0) {
    const det = await safeFetchApi<BairroDetalheOut>(`/bairros/${painel.bairros[0].slug}`);
    detalheInicial = det.data;
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10 space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Território e demandas da cidade · Inhumas (GO)
        </p>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-[var(--ink)]">
          Mapa de Indicações e Requerimentos por Bairro
        </h1>
        <p className="text-sm sm:text-base text-[var(--ink-muted)] max-w-3xl leading-relaxed">
          Descubra o que os vereadores têm solicitado para cada bairro, setor ou distrito de
          Inhumas — filtrado por tema (asfalto, trânsito, saúde, iluminação, educação) e com link
          para a proposição oficial no Nexlegis.
        </p>
      </header>

      <BairrosClient painelInicial={painel} detalheInicial={detalheInicial} />
    </div>
  );
}
