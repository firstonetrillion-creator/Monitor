"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Check, Copy, AlertCircle } from "lucide-react";

let ultimaMensagemStatus = "";

function copiarLegado(texto: string): boolean {
  const campo = Object.assign(document.createElement("textarea"), { value: texto });
  campo.setAttribute("readonly", "");
  campo.style.cssText = "position:fixed;inset-block-start:0;opacity:0";
  document.body.append(campo);
  campo.select();
  try {
    return document.execCommand("copy");
  } finally {
    campo.remove();
  }
}

interface BotaoCopiarProps {
  targetId: string;
  textoFallback?: string;
  rotulo: string;
  className?: string;
}

/**
 * Botão de cópia acessível seguindo modern-web-guidance (copy-button):
 * - Usa Invoker Commands (`command="--copy"` + `commandfor`) com fallback para navegadores sem CommandEvent.
 * - Mantém a live region `role="status"` fora do botão e visível via opacidade (nunca `display: none`).
 * - Nunca desabilita o botão durante o feedback e evita supressão de anúncios repetidos no VoiceOver.
 */
export function BotaoCopiar({
  targetId,
  textoFallback,
  rotulo,
  className = "",
}: BotaoCopiarProps) {
  const btnRef = useRef<HTMLButtonElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusId = useId();
  const [estado, setEstado] = useState<"idle" | "copied" | "failed">("idle");
  const [mensagemStatus, setMensagemStatus] = useState("");

  useEffect(() => {
    const btn = btnRef.current;
    if (!btn) return;

    const executarCopia = async () => {
      const alvo = document.getElementById(targetId);
      let texto = textoFallback || "";
      if (alvo) {
        if (alvo instanceof HTMLTextAreaElement || alvo instanceof HTMLInputElement) {
          texto = alvo.value;
        } else {
          texto = alvo.innerText.trim();
        }
      }
      if (!texto) return;

      let sucesso = false;
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(texto);
          sucesso = true;
        } else {
          sucesso = copiarLegado(texto);
        }
      } catch {
        sucesso = copiarLegado(texto);
      }

      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      let msg = sucesso ? "Copiado" : "Falha ao copiar";
      if (msg === ultimaMensagemStatus) {
        msg += "\u00A0";
      }
      ultimaMensagemStatus = msg;
      setEstado(sucesso ? "copied" : "failed");
      setMensagemStatus(msg);

      timerRef.current = setTimeout(() => {
        setEstado("idle");
        setMensagemStatus("");
      }, 2400);
    };

    const onCommand = (ev: Event) => {
      const cmdEvent = ev as Event & { command?: string; source?: EventTarget | null };
      if (cmdEvent.command === "--copy" && cmdEvent.source === btn) {
        void executarCopia();
      }
    };

    const onClickFallback = () => {
      void executarCopia();
    };

    const suportaCommandEvent = typeof window !== "undefined" && "CommandEvent" in window;
    if (suportaCommandEvent) {
      document.addEventListener("command", onCommand, true);
    } else {
      btn.addEventListener("click", onClickFallback);
    }

    return () => {
      if (suportaCommandEvent) {
        document.removeEventListener("command", onCommand, true);
      } else {
        btn.removeEventListener("click", onClickFallback);
      }
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [targetId, textoFallback]);

  const invokerAttrs = {
    command: "--copy",
    commandfor: targetId,
  } as Record<string, string>;

  return (
    <span className="inline-flex items-center gap-2">
      <button
        ref={btnRef}
        type="button"
        {...invokerAttrs}
        data-copied={estado === "copied" ? "" : undefined}
        data-failed={estado === "failed" ? "" : undefined}
        className={`inline-flex min-w-6 min-h-6 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)] transition-colors ${className}`}
      >
        {estado === "copied" ? (
          <Check className="w-3.5 h-3.5 text-[var(--primary)]" aria-hidden="true" />
        ) : estado === "failed" ? (
          <AlertCircle className="w-3.5 h-3.5 text-[var(--accent)]" aria-hidden="true" />
        ) : (
          <Copy className="w-3.5 h-3.5" aria-hidden="true" />
        )}
        <span>{rotulo}</span>
      </button>
      <span
        id={statusId}
        role="status"
        className={`text-xs font-semibold transition-opacity duration-150 ${
          mensagemStatus ? "opacity-100" : "opacity-0 pointer-events-none"
        } ${estado === "failed" ? "text-[var(--accent)]" : "text-[var(--primary)]"}`}
      >
        {mensagemStatus}
      </span>
    </span>
  );
}
