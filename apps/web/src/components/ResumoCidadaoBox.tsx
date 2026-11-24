import Link from "next/link";
import { ExternalLink, FileText } from "lucide-react";
import type { ResumoCidadaoOut } from "@/lib/types";
import { formatarDataHoraBR } from "@/lib/format";

interface ResumoCidadaoBoxProps {
  resumo: ResumoCidadaoOut;
  titulo?: string;
}

/**
 * Bloco editorial neutro para exibição de resumos em linguagem simples (`texto-cidadao` / docs/05 Regra 6).
 * Sempre exibe o selo obrigatório "Resumo automático" + link para o documento original.
 */
export function ResumoCidadaoBox({
  resumo,
  titulo = "Resumo em linguagem simples",
}: ResumoCidadaoBoxProps) {
  return (
    <section
      aria-label={titulo}
      className="rounded-xl border border-[var(--primary)]/30 bg-[var(--surface)] p-5 space-y-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold text-[var(--ink)] flex items-center gap-2">
          <FileText className="w-4 h-4 text-[var(--primary)] shrink-0" aria-hidden="true" />
          <span>{titulo}</span>
        </h2>
        <span className="inline-flex items-center rounded-full bg-[var(--status-null-bg)] text-[var(--status-null-ink)] px-2.5 py-0.5 text-xs font-semibold">
          Resumo automático
        </span>
      </div>

      <p className="text-xs text-[var(--ink-muted)]">{resumo.rotulo_transparencia}</p>

      <dl className="grid gap-3 sm:grid-cols-3 pt-1 text-sm">
        <div className="rounded-lg bg-[var(--surface-alt)] p-3.5">
          <dt className="text-xs font-semibold uppercase text-[var(--primary)]">O que é</dt>
          <dd className="mt-1 text-[var(--ink)] leading-relaxed">{resumo.o_que_e}</dd>
        </div>
        <div className="rounded-lg bg-[var(--surface-alt)] p-3.5">
          <dt className="text-xs font-semibold uppercase text-[var(--primary)]">
            O que propõe / pauta
          </dt>
          <dd className="mt-1 text-[var(--ink)] leading-relaxed">{resumo.o_que_propoe}</dd>
        </div>
        <div className="rounded-lg bg-[var(--surface-alt)] p-3.5">
          <dt className="text-xs font-semibold uppercase text-[var(--primary)]">
            Situação e resultado
          </dt>
          <dd className="mt-1 text-[var(--ink)] leading-relaxed">
            {resumo.situacao_e_resultado}
          </dd>
        </div>
      </dl>

      <footer className="pt-2 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--ink-muted)]">
        <span className="tabular-nums">
          Base coletada em {formatarDataHoraBR(resumo.coletado_em)} ·{" "}
          <Link href="/como-calculamos" className="underline hover:text-[var(--primary)]">
            Como calculamos
          </Link>
        </span>
        <a
          href={resumo.fonte_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline"
        >
          Conferir documento original
          <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
        </a>
      </footer>
    </section>
  );
}
