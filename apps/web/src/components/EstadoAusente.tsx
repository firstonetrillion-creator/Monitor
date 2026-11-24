import { AlertTriangle, Info } from "lucide-react";

interface EstadoAusenteProps {
  titulo: string;
  descricao: string;
  tom?: "neutro" | "aviso";
}

export function EstadoAusente({
  titulo,
  descricao,
  tom = "neutro",
}: EstadoAusenteProps) {
  const isAviso = tom === "aviso";
  return (
    <div
      role="status"
      className={`rounded-xl border p-4 flex items-start gap-3 text-sm ${
        isAviso
          ? "border-[var(--accent)]/40 bg-[var(--status-warn-bg)] text-[var(--status-warn-ink)]"
          : "border-[var(--border)] bg-[var(--status-null-bg)] text-[var(--status-null-ink)]"
      }`}
    >
      {isAviso ? (
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
      ) : (
        <Info className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
      )}
      <div className="min-w-0 break-words">
        <p className="font-semibold">{titulo}</p>
        <p className="mt-1 leading-relaxed opacity-95">{descricao}</p>
      </div>
    </div>
  );
}

interface EstadoErroAPIProps {
  titulo?: string;
  mensagem: string;
  onTentarNovamente?: () => void;
}

export function EstadoErroAPI({
  titulo = "Não foi possível carregar estes dados agora",
  mensagem,
  onTentarNovamente,
}: EstadoErroAPIProps) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-[var(--accent)]/50 bg-[var(--status-warn-bg)] text-[var(--status-warn-ink)] p-5"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="flex-1">
          <p className="font-semibold">{titulo}</p>
          <p className="mt-1 text-sm">{mensagem}</p>
          {onTentarNovamente && (
            <button
              type="button"
              onClick={onTentarNovamente}
              className="mt-3 inline-flex items-center rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-3.5 py-1.5 text-xs font-semibold hover:opacity-90"
            >
              Tentar novamente
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
