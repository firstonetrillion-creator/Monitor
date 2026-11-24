"use client";

import Link from "next/link";
import { Download } from "lucide-react";
import { baixarCsvNoNavegador } from "@/lib/csv";
import type { DuodecimoOut } from "@/lib/types";
import {
  formatarBRL,
  formatarDataBR,
  formatarDataHoraBR,
  rotuloFonte,
} from "@/lib/format";
import { GlossarioTooltip } from "@/components/GlossarioTooltip";

interface DuodecimoSectionProps {
  duodecimo: DuodecimoOut[];
}

export function DuodecimoSection({ duodecimo }: DuodecimoSectionProps) {
  if (duodecimo.length === 0) {
    return null;
  }

  const repasses = duodecimo.filter((d) => d.tipo_natureza === "RECEITA_REPASSE");
  const devolucoes = duodecimo.filter((d) => d.tipo_natureza === "DEVOLUCAO_DUODECIMO");
  const totalRepasses = repasses.reduce((acc, d) => acc + Number(d.valor || 0), 0);
  const totalDevolucoes = devolucoes.reduce((acc, d) => acc + Number(d.valor || 0), 0);

  const exportarDuodecimoCsv = () => {
    baixarCsvNoNavegador(
      "duodecimo-2026-inhumas.csv",
      [
        "Data",
        "Mês/Ano",
        "Natureza",
        "Código",
        "Descrição",
        "Valor (R$)",
        "Fonte",
        "Coletado em",
      ],
      duodecimo.map((d) => [
        formatarDataBR(d.data_lancamento),
        `${String(d.mes).padStart(2, "0")}/${d.ano}`,
        d.tipo_natureza === "RECEITA_REPASSE"
          ? "Repasse de Duodécimo"
          : "Devolução de Duodécimo",
        d.tipo_codigo,
        d.descricao,
        d.valor,
        d.proveniencia.fonte_url,
        formatarDataHoraBR(d.proveniencia.coletado_em),
      ]),
    );
  };

  return (
    <section
      aria-labelledby="sec-duodecimo"
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="sec-duodecimo" className="text-lg font-bold text-[var(--ink)]">
            Repasses do duodécimo e devoluções (2026)
          </h2>
          <p className="text-xs text-[var(--ink-muted)]">
            Fonte: {rotuloFonte(duodecimo[0].proveniencia.fonte_id)} · Coleta:{" "}
            {formatarDataHoraBR(duodecimo[0].proveniencia.coletado_em)} ·{" "}
            <Link href="/como-calculamos" className="underline hover:text-[var(--primary)]">
              Como calculamos
            </Link>
          </p>
        </div>
        <button
          type="button"
          onClick={exportarDuodecimoCsv}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
        >
          <Download className="w-3.5 h-3.5" aria-hidden="true" />
          Baixar CSV do duodécimo
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg bg-[var(--surface-alt)] p-4">
          <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
            <GlossarioTooltip termo="duodecimo" label="Duodécimo recebido (2026)" />
          </p>
          <p className="mt-1 text-xl font-bold tabular-nums text-[var(--primary)]">
            {formatarBRL(totalRepasses)}
          </p>
          <p className="text-xs text-[var(--ink-muted)]">
            {repasses.length} repasses recebidos da Prefeitura
          </p>
        </div>
        <div className="rounded-lg bg-[var(--surface-alt)] p-4">
          <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
            Devoluções à Prefeitura (2026)
          </p>
          <p className="mt-1 text-xl font-bold tabular-nums">
            {formatarBRL(totalDevolucoes)}
          </p>
          <p className="text-xs text-[var(--ink-muted)]">
            {devolucoes.length} devoluções registradas no período
          </p>
        </div>
      </div>

      <details className="group rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3">
        <summary className="cursor-pointer text-xs font-semibold text-[var(--primary)] select-none">
          Ver os {duodecimo.length} lançamentos do duodécimo (repasses e devoluções)
        </summary>
        <div
          className="mt-3 overflow-x-auto max-h-[360px]"
          tabIndex={0}
          role="region"
          aria-label="Lançamentos de duodécimo em 2026"
        >
          <table className="w-full text-left text-xs border-collapse min-w-[580px]">
            <thead className="sticky top-0 bg-[var(--bg)] z-10">
              <tr className="border-b border-[var(--border)] uppercase text-[var(--ink-muted)]">
                <th scope="col" className="py-2 pr-3">
                  Data
                </th>
                <th scope="col" className="py-2 pr-3">
                  Competência
                </th>
                <th scope="col" className="py-2 pr-3">
                  Natureza
                </th>
                <th scope="col" className="py-2 pr-3">
                  Descrição publicada
                </th>
                <th scope="col" className="py-2 text-right">
                  Valor
                </th>
              </tr>
            </thead>
            <tbody>
              {duodecimo.map((d) => (
                <tr key={d.duodecimo_id} className="border-b border-[var(--border)]/60">
                  <td className="py-2 pr-3 tabular-nums whitespace-nowrap">
                    {formatarDataBR(d.data_lancamento)}
                  </td>
                  <td className="py-2 pr-3 tabular-nums whitespace-nowrap">
                    {String(d.mes).padStart(2, "0")}/${d.ano}
                  </td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 font-semibold ${
                        d.tipo_natureza === "RECEITA_REPASSE"
                          ? "bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)]"
                          : "bg-[var(--status-warn-bg)] text-[var(--status-warn-ink)]"
                      }`}
                    >
                      {d.tipo_natureza === "RECEITA_REPASSE" ? "Repasse" : "Devolução"}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-[var(--ink-muted)]">{d.descricao}</td>
                  <td className="py-2 text-right font-bold tabular-nums whitespace-nowrap">
                    {formatarBRL(d.valor)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
