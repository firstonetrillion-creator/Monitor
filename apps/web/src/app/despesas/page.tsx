import { safeFetchApi } from "@/lib/api";
import type {
  DespesaEmpenhoOut,
  DespesasResumoOut,
  DuodecimoOut,
  PaginacaoOut,
} from "@/lib/types";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { DespesasClient } from "./DespesasClient";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Despesas Públicas",
  description:
    "Empenho bruto, anulações, empenho líquido, liquidado e pago da Câmara Municipal de Inhumas em 2026, com filtros por período, fornecedor e classificação.",
};

export default async function DespesasPage() {
  const [resumoRes, listaRes, duodecimoRes] = await Promise.all([
    safeFetchApi<DespesasResumoOut>("/transparencia/despesas/resumo", { ano: 2026 }),
    safeFetchApi<PaginacaoOut<DespesaEmpenhoOut>>("/transparencia/despesas", {
      ano: 2026,
      page: 1,
      per_page: 20,
    }),
    safeFetchApi<PaginacaoOut<DuodecimoOut>>("/transparencia/duodecimo", {
      ano: 2026,
      per_page: 50,
    }),
  ]);

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Despesas Públicas (2026)
        </h1>
        <p className="mt-2 text-base text-[var(--ink-muted)]">
          Execução orçamentária da Câmara Municipal de Inhumas com separação estrita dos estágios da
          despesa pública (<strong>empenhado</strong>, <strong>liquidado</strong> e{" "}
          <strong>pago</strong>) e mascaramento LGPD de documentos de pessoa física.
        </p>
      </header>

      {resumoRes.error || listaRes.error || !resumoRes.data || !listaRes.data ? (
        <EstadoErroAPI
          mensagem={
            resumoRes.error ||
            listaRes.error ||
            "Não foi possível carregar as despesas de 2026."
          }
        />
      ) : (
        <DespesasClient
          initialResumo={resumoRes.data}
          initialLista={listaRes.data}
          duodecimo={duodecimoRes.data?.items || []}
        />
      )}
    </div>
  );
}
