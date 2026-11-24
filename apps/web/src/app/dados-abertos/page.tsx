import type { Metadata } from "next";
import { safeFetchApi } from "@/lib/api";
import type { HealthOut } from "@/lib/types";
import { formatarInteiro } from "@/lib/format";
import { DadosAbertosClient } from "./DadosAbertosClient";

export const metadata: Metadata = {
  title: "API Pública e Dados Abertos | Cerrado Aberto",
  description:
    "Documentação prática da API pública somente leitura do Cerrado Aberto para jornalistas, pesquisadores e organizações civis.",
};

export const dynamic = "force-dynamic";

export default async function DadosAbertosPage() {
  const { data: health } = await safeFetchApi<HealthOut>("/health");
  const contagens = health?.contagens_persistidas;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10 space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Para jornalistas, pesquisadores e controle social
        </p>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-[var(--ink)]">
          API Pública e Dados Abertos
        </h1>
        <p className="text-sm sm:text-base text-[var(--ink-muted)] max-w-3xl leading-relaxed">
          Todos os dados tratados e normalizados pelo Cerrado Aberto podem ser consultados
          gratuitamente em JSON estruturado (com proveniência SHA-256 e proteção LGPD) ou baixados
          em planilhas CSV.
        </p>

        {contagens && (
          <div className="pt-2 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-[var(--surface-alt)] border border-[var(--border)] px-3 py-1 tabular-nums">
              <strong>{formatarInteiro(contagens.proposicao)}</strong> proposições
            </span>
            <span className="rounded-full bg-[var(--surface-alt)] border border-[var(--border)] px-3 py-1 tabular-nums">
              <strong>{formatarInteiro(contagens.norma)}</strong> leis municipais
            </span>
            <span className="rounded-full bg-[var(--surface-alt)] border border-[var(--border)] px-3 py-1 tabular-nums">
              <strong>{formatarInteiro(contagens.despesa_empenho)}</strong> empenhos 2026
            </span>
            <span className="rounded-full bg-[var(--surface-alt)] border border-[var(--border)] px-3 py-1 tabular-nums">
              <strong>{formatarInteiro(contagens.bairro)}</strong> bairros mapeados
            </span>
            <span className="rounded-full bg-[var(--surface-alt)] border border-[var(--border)] px-3 py-1 tabular-nums">
              <strong>{formatarInteiro(contagens.comparativo_legislativo_siconfi)}</strong> registros
              SICONFI
            </span>
          </div>
        )}
      </header>

      <DadosAbertosClient />
    </div>
  );
}
