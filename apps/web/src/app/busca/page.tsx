import type { Metadata } from "next";
import { safeFetchApi } from "@/lib/api";
import type { BuscaUnificadaOut } from "@/lib/types";
import { BuscaClient } from "./BuscaClient";

export const metadata: Metadata = {
  title: "Busca Avançada Unificada | Cerrado Aberto",
  description:
    "Pesquise em português claro por proposições, leis municipais, vereadores, sessões e despesas públicas de Inhumas (GO).",
};

export const dynamic = "force-dynamic";

export default async function BuscaPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; categoria?: string; ano?: string }>;
}) {
  const sp = await searchParams;
  const termo = (sp.q || "").trim();
  const categoria = sp.categoria || "todos";
  const ano = sp.ano || "";

  let resultadoInicial: BuscaUnificadaOut | null = null;
  if (termo.length >= 2) {
    const res = await safeFetchApi<BuscaUnificadaOut>("/busca", {
      q: termo,
      categoria,
      ano: ano ? Number(ano) : undefined,
      page: 1,
      per_page: 20,
    });
    resultadoInicial = res.data;
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10 space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Pesquisa unificada em português
        </p>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-[var(--ink)]">
          Busca Avançada no Legislativo de Inhumas
        </h1>
        <p className="text-sm sm:text-base text-[var(--ink-muted)] max-w-3xl leading-relaxed">
          Encontre de uma só vez <strong>proposições parlamentares</strong>,{" "}
          <strong>leis municipais</strong>, <strong>vereadores</strong>,{" "}
          <strong>sessões plenárias</strong> e <strong>despesas públicas</strong> — sempre com
          acesso direto ao documento oficial.
        </p>
      </header>

      <BuscaClient
        termoInicial={termo}
        categoriaInicial={categoria}
        anoInicial={ano}
        resultadoInicial={resultadoInicial}
      />
    </div>
  );
}
