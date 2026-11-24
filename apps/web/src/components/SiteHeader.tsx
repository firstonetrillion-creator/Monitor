"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, ShieldCheck } from "lucide-react";

const NAV_LINKS_DESKTOP = [
  { href: "/", label: "Início" },
  { href: "/busca", label: "Busca" },
  { href: "/boletins", label: "Boletim" },
  { href: "/vereadores", label: "Vereadores" },
  { href: "/despesas", label: "Despesas" },
  { href: "/bairros", label: "Bairros" },
  { href: "/legislacao", label: "Leis" },
  { href: "/comparativo", label: "Comparativo" },
  { href: "/sessoes", label: "Sessões" },
  { href: "/dados-abertos", label: "API" },
];

const NAV_LINKS_MOBILE = [
  ...NAV_LINKS_DESKTOP,
  { href: "/materias", label: "Proposições" },
  { href: "/folha", label: "Folha de Pagamento" },
  { href: "/custo-mandato", label: "Custo do Mandato" },
  { href: "/diarias", label: "Diárias" },
  { href: "/como-calculamos", label: "Como Calculamos" },
  { href: "/correcoes", label: "Correções" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/";
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)]">
      {/* Faixa de independência editorial */}
      <div className="bg-[var(--primary)] text-[var(--primary-ink)] text-xs sm:text-sm py-2 px-4">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <p className="flex items-center gap-2 font-medium">
            <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>
              <strong>Cerrado Aberto</strong> — Iniciativa cidadã independente, sem vínculo
              institucional, contratual ou político com a Câmara Municipal de Inhumas.
            </span>
          </p>
          <span className="inline-flex items-center rounded-full bg-black/20 px-2.5 py-0.5 text-xs font-semibold">
            Ambiente de Homologação (MVP)
          </span>
        </div>
      </div>

      {/* Navegação principal */}
      <div className="max-w-6xl mx-auto px-4 py-3.5 flex items-center justify-between gap-4">
        <Link
          href="/"
          className="flex items-baseline gap-2.5 group focus-visible:rounded-md"
        >
          <span className="font-display text-xl sm:text-2xl font-bold text-[var(--primary)] tracking-tight">
            Cerrado Aberto
          </span>
          <span className="text-xs font-medium text-[var(--ink-muted)] hidden sm:inline">
            Inhumas (GO)
          </span>
        </Link>

        {/* Menu desktop */}
        <nav aria-label="Principal" className="hidden lg:flex items-center gap-0.5">
          {NAV_LINKS_DESKTOP.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`px-2.5 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  active
                    ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                    : "text-[var(--ink)] hover:bg-[var(--surface-alt)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Botão menu mobile */}
        <button
          type="button"
          onClick={() => setMenuOpen((prev) => !prev)}
          aria-expanded={menuOpen}
          aria-controls="mobile-nav"
          aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}
          className="lg:hidden inline-flex items-center justify-center p-2 rounded-lg border border-[var(--border)] text-[var(--ink)] hover:bg-[var(--surface-alt)]"
        >
          {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Menu mobile */}
      {menuOpen && (
        <nav
          id="mobile-nav"
          aria-label="Principal em dispositivos móveis"
          className="lg:hidden border-t border-[var(--border)] bg-[var(--surface)] px-4 py-3 flex flex-col gap-1"
        >
          {NAV_LINKS_MOBILE.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                aria-current={active ? "page" : undefined}
                className={`px-3 py-2.5 rounded-lg text-sm font-medium ${
                  active
                    ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                    : "text-[var(--ink)] hover:bg-[var(--surface-alt)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
