import type { Metadata } from "next";
import { safeFetchApi } from "@/lib/api";
import type { MateriaResumoOut, PaginacaoOut, VereadorResumoOut } from "@/lib/types";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { MateriasClient } from "./MateriasClient";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Proposições e Matérias Legislativas",
  description:
    "Catálogo completo e filtrável de projetos de lei, requerimentos, indicações, moções e atos registrados no Nexlegis da Câmara Municipal de Inhumas (2025–2026).",
};

interface MateriasSearchParams {
  q?: string;
  ano?: string;
  tipo_id?: string;
  vereador_id?: string;
  eh_proposicao_parlamentar?: string;
  page?: string;
}

export default async function MateriasPage({
  searchParams,
}: {
  searchParams: Promise<MateriasSearchParams>;
}) {
  const sp = await searchParams;
  const anoInicial = sp.ano && (sp.ano === "2025" || sp.ano === "2026") ? Number(sp.ano) : undefined;
  const tipoInicial = sp.tipo_id && Number(sp.tipo_id) > 0 ? Number(sp.tipo_id) : undefined;
  const pageInicial = sp.page && Number(sp.page) >= 1 ? Number(sp.page) : 1;

  let ehParlamentarApi: boolean | undefined = true;
  let classificacaoUi = "true";
  if (sp.eh_proposicao_parlamentar === "false") {
    ehParlamentarApi = false;
    classificacaoUi = "false";
  } else if (sp.eh_proposicao_parlamentar === "all" || sp.eh_proposicao_parlamentar === "") {
    ehParlamentarApi = undefined;
    classificacaoUi = "all";
  }

  const [materiasRes, vereadoresRes] = await Promise.all([
    safeFetchApi<PaginacaoOut<MateriaResumoOut>>("/materias", {
      ano: anoInicial,
      tipo_id: tipoInicial,
      vereador_id: sp.vereador_id || undefined,
      eh_proposicao_parlamentar: ehParlamentarApi,
      q: sp.q?.trim() || undefined,
      page: pageInicial,
      per_page: 20,
    }),
    safeFetchApi<PaginacaoOut<VereadorResumoOut>>("/vereadores", {
      per_page: 50,
    }),
  ]);

  const vereadoresOrdenados = [...(vereadoresRes.data?.items || [])].sort((a, b) =>
    a.nome_exibicao.localeCompare(b.nome_exibicao, "pt-BR"),
  );

  return (
    <div className="space-y-6">
      <header className="max-w-3xl space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Produção Legislativa · Nexlegis (2025–2026)
        </p>
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Proposições e Matérias Legislativas
        </h1>
        <p className="text-base text-[var(--ink-muted)] leading-relaxed">
          Explore todos os projetos de lei, requerimentos, indicações, moções e documentos
          tramitados na Câmara Municipal de Inhumas, com filtro por autor, tipo, ano e busca na
          ementa.
        </p>
      </header>

      <EstadoAusente
        titulo="Separação metodológica (ADR-005): proposições parlamentares vs. atos administrativos"
        descricao="No sistema oficial Nexlegis, atas de sessão e julgamentos de contas compartilham a mesma listagem dos projetos de lei e requerimentos. Por padrão, exibimos apenas proposições parlamentares; você pode alternar o filtro para incluir atas e documentos administrativos."
      />

      {materiasRes.error || !materiasRes.data ? (
        <EstadoErroAPI
          mensagem={materiasRes.error || "Não foi possível carregar as proposições."}
        />
      ) : (
        <MateriasClient
          initialData={materiasRes.data}
          vereadores={vereadoresOrdenados}
          initialFilters={{
            q: sp.q || "",
            ano: sp.ano || "",
            tipoId: sp.tipo_id || "",
            vereadorId: sp.vereador_id || "",
            classificacao: classificacaoUi,
          }}
        />
      )}
    </div>
  );
}
