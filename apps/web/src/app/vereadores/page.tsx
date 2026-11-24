import { safeFetchApi } from "@/lib/api";
import type { PaginacaoOut, VereadorResumoOut } from "@/lib/types";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { VereadoresClient } from "./VereadoresClient";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Vereadores",
  description:
    "Lista de vereadores da Câmara Municipal de Inhumas em ordem alfabética, com presença, proposições e custo da estrutura do mandato.",
};

export default async function VereadoresPage() {
  const res = await safeFetchApi<PaginacaoOut<VereadorResumoOut>>("/vereadores", {
    apenas_legislatura_atual: true,
    per_page: 50,
    page: 1,
  });

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-bold text-[var(--ink)]">Vereadores</h1>
        <p className="mt-2 text-base text-[var(--ink-muted)]">
          Exibição em <strong>ordem alfabética</strong>, com os mesmos critérios e o mesmo destaque
          visual para todos os parlamentares. Não fazemos ranking de desempenho.
        </p>
      </header>

      {res.error || !res.data ? (
        <EstadoErroAPI
          mensagem={res.error || "Não foi possível carregar a lista de vereadores."}
        />
      ) : (
        <VereadoresClient initialData={res.data} />
      )}
    </div>
  );
}
