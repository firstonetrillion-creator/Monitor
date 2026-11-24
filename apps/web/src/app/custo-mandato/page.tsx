import { safeFetchApi } from "@/lib/api";
import type {
  CustoMandatoMensalOut,
  DeclaracaoTransparenciaOut,
  PaginacaoOut,
} from "@/lib/types";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { CustoMandatoClient } from "./CustoMandatoClient";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Custo da Estrutura do Mandato",
  description:
    "Apuração mensal e acumulada de 2026: Subsídio Bruto + Folha Bruta do Gabinete + Diárias Atribuíveis, com transparência de lacunas.",
};

export default async function CustoMandatoPage() {
  const [custoRes, declRes] = await Promise.all([
    safeFetchApi<PaginacaoOut<CustoMandatoMensalOut>>("/transparencia/custo-mandato", {
      ano: 2026,
      per_page: 100,
      page: 1,
    }),
    safeFetchApi<DeclaracaoTransparenciaOut[]>("/transparencia/declaracoes"),
  ]);

  let todosItens = custoRes.data?.items || [];
  if (custoRes.data && custoRes.data.total_pages > 1) {
    const page2 = await safeFetchApi<PaginacaoOut<CustoMandatoMensalOut>>(
      "/transparencia/custo-mandato",
      { ano: 2026, per_page: 100, page: 2 },
    );
    if (page2.data) {
      todosItens = [...todosItens, ...page2.data.items];
    }
  }

  const declCeap = (declRes.data || []).find(
    (d) => d.tipo_declaracao === "INEXISTENCIA_COTA_PARLAMENTAR",
  );

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Custo da Estrutura do Mandato (2026)
        </h1>
        <p className="mt-2 text-base text-[var(--ink-muted)]">
          Fórmula aprovada (ADR-005):{" "}
          <strong>
            Subsídio bruto do vereador + Folha bruta do gabinete + Diárias atribuíveis
          </strong>
          . Valores ausentes permanecem não apurados (<code>NULL</code>), sem conversão em zero.
        </p>
      </header>

      {custoRes.error || !custoRes.data ? (
        <EstadoErroAPI
          mensagem={
            custoRes.error || "Não foi possível carregar os dados de Custo da Estrutura do Mandato."
          }
        />
      ) : (
        <CustoMandatoClient registros={todosItens} declaracaoCeap={declCeap || null} />
      )}
    </div>
  );
}
