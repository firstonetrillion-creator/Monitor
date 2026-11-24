import { safeFetchApi } from "@/lib/api";
import type { PaginacaoOut, SessaoResumoOut } from "@/lib/types";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { SessoesClient } from "./SessoesClient";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Sessões e Votações",
  description:
    "Sessões plenárias da Câmara Municipal de Inhumas (2025–2026), com pautas, presenças, proposições discutidas e votações nominais.",
};

export default async function SessoesPage() {
  const res = await safeFetchApi<PaginacaoOut<SessaoResumoOut>>("/sessoes", {
    page: 1,
    per_page: 20,
  });

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-bold text-[var(--ink)]">Sessões e Votações</h1>
        <p className="mt-2 text-base text-[var(--ink-muted)]">
          Registro oficial das sessões plenárias de 2025 e 2026 no Nexlegis, com lista de
          presença, pautas deliberadas, placares e votos nominais quando disponíveis.
        </p>
      </header>

      {res.error || !res.data ? (
        <EstadoErroAPI
          mensagem={res.error || "Não foi possível carregar as sessões plenárias."}
        />
      ) : (
        <SessoesClient initialData={res.data} />
      )}
    </div>
  );
}
