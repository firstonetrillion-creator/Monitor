import Link from "next/link";
import { formatarDataHoraBR, rotuloFonte } from "@/lib/format";

interface DadoComFonteProps {
  titulo: string;
  valor: string;
  subtitulo?: string;
  fonteId: string;
  fonteUrl?: string;
  coletadoEm?: string | null;
  destaque?: "primario" | "acento" | "neutro";
  ausente?: boolean;
}

export function DadoComFonte({
  titulo,
  valor,
  subtitulo,
  fonteId,
  fonteUrl,
  coletadoEm,
  destaque = "neutro",
  ausente = false,
}: DadoComFonteProps) {
  const corValor = ausente
    ? "text-[var(--ink-muted)] italic text-lg sm:text-xl"
    : destaque === "primario"
      ? "text-[var(--primary)] text-xl sm:text-2xl font-bold"
      : destaque === "acento"
        ? "text-[var(--accent)] text-xl sm:text-2xl font-bold"
        : "text-[var(--ink)] text-xl sm:text-2xl font-bold";

  return (
    <article className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 flex flex-col justify-between gap-3">
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)] font-sans">
          {titulo}
        </h3>
        <p className={`mt-2 tabular-nums leading-tight ${corValor}`}>{valor}</p>
        {subtitulo && (
          <p className="mt-1.5 text-xs text-[var(--ink-muted)] leading-relaxed">{subtitulo}</p>
        )}
      </div>

      <footer className="pt-3 border-t border-[var(--border)] text-[11px] text-[var(--ink-muted)] flex flex-wrap items-center justify-between gap-1.5">
        <span>
          Fonte:{" "}
          {fonteUrl ? (
            <a
              href={fonteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-[var(--primary)]"
            >
              {rotuloFonte(fonteId)}
            </a>
          ) : (
            rotuloFonte(fonteId)
          )}
          {coletadoEm ? ` · Coleta: ${formatarDataHoraBR(coletadoEm)}` : ""}
        </span>
        <Link href="/como-calculamos" className="underline hover:text-[var(--primary)]">
          Como calculamos
        </Link>
      </footer>
    </article>
  );
}
