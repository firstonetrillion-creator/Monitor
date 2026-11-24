import { ExternalLink } from "lucide-react";
import type { ProvenienciaOut } from "@/lib/types";
import { formatarDataHoraBR, rotuloFonte } from "@/lib/format";

interface ProvenienciaBoxProps {
  proveniencia: ProvenienciaOut;
  titulo?: string;
}

export function ProvenienciaBox({
  proveniencia,
  titulo = "Rastreabilidade e fonte oficial",
}: ProvenienciaBoxProps) {
  return (
    <aside className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--ink-muted)]">
      <p className="font-semibold text-[var(--ink)]">{titulo}</p>
      <dl className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="font-medium text-[var(--ink)]">Fonte</dt>
          <dd>{rotuloFonte(proveniencia.fonte_id)}</dd>
        </div>
        <div>
          <dt className="font-medium text-[var(--ink)]">Coletado em</dt>
          <dd className="tabular-nums">{formatarDataHoraBR(proveniencia.coletado_em)}</dd>
        </div>
        <div>
          <dt className="font-medium text-[var(--ink)]">Hash SHA-256</dt>
          <dd className="font-mono truncate" title={proveniencia.hash_conteudo}>
            {proveniencia.hash_conteudo.slice(0, 16)}…
          </dd>
        </div>
        <div>
          <dt className="font-medium text-[var(--ink)]">Endereço oficial</dt>
          <dd>
            <a
              href={proveniencia.fonte_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 underline hover:text-[var(--primary)] break-all"
            >
              <span>Abrir fonte</span>
              <ExternalLink className="w-3 h-3 shrink-0" aria-hidden="true" />
            </a>
          </dd>
        </div>
      </dl>
    </aside>
  );
}
