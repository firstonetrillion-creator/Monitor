"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, ExternalLink, ArrowRight } from "lucide-react";
import type { BuscaUnificadaOut, ItemBuscaOut } from "@/lib/types";
import { api } from "@/lib/api";
import { formatarDataBR, formatarInteiro } from "@/lib/format";

interface BuscaClientProps {
  termoInicial: string;
  categoriaInicial: string;
  anoInicial: string;
  resultadoInicial: BuscaUnificadaOut | null;
}

const ABAS_CATEGORIA = [
  { id: "todos", label: "Todos" },
  { id: "proposicoes", label: "Proposições" },
  { id: "normas", label: "Leis" },
  { id: "vereadores", label: "Vereadores" },
  { id: "sessoes", label: "Sessões" },
  { id: "despesas", label: "Despesas" },
] as const;

const SUGESTOES_BUSCA = [
  "asfalto",
  "Parque São Jorge",
  "UBSF",
  "3577",
  "sinalização",
  "Prof. Kelvy",
];

function rotuloTipo(tipo: ItemBuscaOut["tipo"]): { texto: string; cor: string } {
  switch (tipo) {
    case "proposicao":
      return { texto: "Proposição", cor: "bg-[var(--primary)]/10 text-[var(--primary)]" };
    case "norma":
      return { texto: "Lei / Norma", cor: "bg-[var(--highlight)]/20 text-[var(--ink)]" };
    case "vereador":
      return { texto: "Vereador(a)", cor: "bg-[var(--surface-alt)] text-[var(--ink)]" };
    case "sessao":
      return { texto: "Sessão Plenária", cor: "bg-[var(--surface-alt)] text-[var(--primary)]" };
    case "despesa":
      return { texto: "Despesa Pública", cor: "bg-[var(--accent)]/12 text-[var(--accent)]" };
  }
}

export function BuscaClient({
  termoInicial,
  categoriaInicial,
  anoInicial,
  resultadoInicial,
}: BuscaClientProps) {
  const router = useRouter();
  const [termo, setTermo] = useState(termoInicial);
  const [categoria, setCategoria] = useState(categoriaInicial || "todos");
  const [ano, setAno] = useState(anoInicial || "");
  const [resultado, setResultado] = useState<BuscaUnificadaOut | null>(resultadoInicial);
  const [erro, setErro] = useState<string | null>(null);
  const [page, setPage] = useState(resultadoInicial?.page || 1);
  const [isPending, startTransition] = useTransition();

  function executarBusca(novoTermo: string, novaCat: string, novoAno: string, novaPag = 1) {
    const qLimpo = novoTermo.trim();
    if (qLimpo.length < 2) {
      setErro("Digite pelo menos 2 caracteres para buscar em toda a base pública.");
      return;
    }
    setErro(null);
    const params = new URLSearchParams({ q: qLimpo });
    if (novaCat && novaCat !== "todos") {
      params.set("categoria", novaCat);
    }
    if (novoAno) {
      params.set("ano", novoAno);
    }
    router.replace(`/busca?${params.toString()}`, { scroll: false });

    startTransition(async () => {
      try {
        const res = await api.busca({
          q: qLimpo,
          categoria: novaCat,
          ano: novoAno ? Number(novoAno) : undefined,
          page: novaPag,
          per_page: 20,
        });
        setResultado(res);
        setPage(res.page);
      } catch (e) {
        setErro(e instanceof Error ? e.message : "Erro ao realizar busca.");
      }
    });
  }

  function aoSubmeter(e: React.FormEvent) {
    e.preventDefault();
    executarBusca(termo, categoria, ano, 1);
  }

  function selecionarAba(novaCat: string, btnEl?: HTMLButtonElement | null) {
    setCategoria(novaCat);
    btnEl?.scrollIntoView({ block: "nearest", inline: "nearest" });
    if (termo.trim().length >= 2) {
      executarBusca(termo, novaCat, ano, 1);
    }
  }

  return (
    <div className="space-y-6">
      {/* Formulário nativo acessível (submissão implícita segura para IME + botão submit explícito) */}
      <form
        onSubmit={aoSubmeter}
        role="search"
        aria-label="Busca avançada unificada"
        className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-xs space-y-4"
      >
        <div className="grid gap-3 md:grid-cols-[1fr_140px_auto] items-end">
          <div>
            <label
              htmlFor="campo-busca-unificada"
              className="block text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)] mb-1.5"
            >
              O que você quer encontrar em Inhumas?
            </label>
            <div className="relative">
              <Search
                className="w-4 h-4 text-[var(--ink-muted)] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
                aria-hidden="true"
              />
              <input
                id="campo-busca-unificada"
                type="search"
                value={termo}
                onChange={(e) => setTermo(e.target.value)}
                placeholder="Ex.: asfalto, UBSF, Parque São Jorge, 3577, Prof. Kelvy..."
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] pl-10 pr-4 py-2.5 text-sm text-[var(--ink)] placeholder:text-[var(--ink-muted)]"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="filtro-ano-busca"
              className="block text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)] mb-1.5"
            >
              Ano
            </label>
            <select
              id="filtro-ano-busca"
              value={ano}
              onChange={(e) => {
                setAno(e.target.value);
                if (termo.trim().length >= 2) {
                  executarBusca(termo, categoria, e.target.value, 1);
                }
              }}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 py-2.5 text-sm text-[var(--ink)]"
            >
              <option value="">Todos</option>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
              <option value="2024">2024</option>
              <option value="2023">2023</option>
              <option value="2022">2022</option>
              <option value="2021">2021</option>
              <option value="2020">2020</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={isPending}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--primary)] text-[var(--primary-ink)] px-5 py-2.5 text-sm font-semibold hover:opacity-95 transition-opacity"
          >
            <Search className="w-4 h-4" aria-hidden="true" />
            {isPending ? "Buscando..." : "Buscar"}
          </button>
        </div>

        {/* Sugestões rápidas para o cidadão */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-[var(--ink-muted)] font-medium">Sugestões:</span>
          {SUGESTOES_BUSCA.map((sug) => (
            <button
              key={sug}
              type="button"
              onClick={() => {
                setTermo(sug);
                executarBusca(sug, "todos", ano, 1);
              }}
              className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-[var(--ink)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-colors"
            >
              {sug}
            </button>
          ))}
        </div>
      </form>

      {erro && (
        <div
          role="alert"
          className="rounded-xl border border-[var(--accent)]/40 bg-[var(--accent)]/10 p-4 text-sm text-[var(--ink)]"
        >
          {erro}
        </div>
      )}

      {/* Abas de categorias em linha única rolável (modern-web-guidance: tabs com ativação explícita + borda sólida, sem aria-controls) */}
      {resultado && (
        <div className="space-y-4">
          <div
            role="tablist"
            aria-label="Filtrar resultados por tipo de registro"
            className="flex items-center gap-1 overflow-x-auto border-b border-[var(--border)] pb-px"
          >
            {ABAS_CATEGORIA.map((aba) => {
              const selecionada = categoria === aba.id;
              const qtd =
                aba.id === "todos"
                  ? Object.values(resultado.contagem_por_tipo).reduce((a, b) => a + b, 0)
                  : resultado.contagem_por_tipo[aba.id] || 0;
              return (
                <button
                  key={aba.id}
                  id={`tab-busca-${aba.id}`}
                  type="button"
                  role="tab"
                  aria-selected={selecionada}
                  onClick={(e) => selecionarAba(aba.id, e.currentTarget)}
                  className={`flex-none relative px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors border-b-[3px] ${
                    selecionada
                      ? "border-[var(--primary)] text-[var(--primary)]"
                      : "border-transparent text-[var(--ink-muted)] hover:text-[var(--ink)]"
                  }`}
                >
                  {aba.label}{" "}
                  <span className="ml-1 tabular-nums text-xs">
                    ({formatarInteiro(qtd)})
                  </span>
                </button>
              );
            })}
          </div>

          <div
            role="tabpanel"
            aria-labelledby={`tab-busca-${categoria}`}
            className="space-y-4"
          >
            <p className="text-sm text-[var(--ink-muted)]">
              Encontrados{" "}
              <strong className="text-[var(--ink)] tabular-nums">
                {formatarInteiro(resultado.total)}
              </strong>{" "}
              registro(s) para <strong className="text-[var(--ink)]">&ldquo;{resultado.termo}&rdquo;</strong>
              {resultado.ano ? ` em ${resultado.ano}` : ""}.
            </p>

            {resultado.items.length === 0 ? (
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--ink-muted)]">
                Nenhum registro encontrado com esses filtros. Experimente termos mais amplos ou
                remova o filtro de ano.
              </div>
            ) : (
              <ul className="space-y-3">
                {resultado.items.map((item) => {
                  const badge = rotuloTipo(item.tipo);
                  return (
                    <li
                      key={`${item.tipo}-${item.id}`}
                      className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 hover:border-[var(--primary)]/50 transition-colors"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.cor}`}
                        >
                          {badge.texto}
                        </span>
                        {item.data_referencia && (
                          <span className="text-xs text-[var(--ink-muted)] tabular-nums">
                            {formatarDataBR(item.data_referencia)}
                          </span>
                        )}
                      </div>

                      <h2 className="font-display text-lg font-bold text-[var(--ink)]">
                        <Link
                          href={item.url_interna}
                          className="hover:text-[var(--primary)] hover:underline"
                        >
                          {item.titulo}
                        </Link>
                      </h2>

                      {item.subtitulo && (
                        <p className="text-xs font-medium text-[var(--ink-muted)] mt-0.5">
                          {item.subtitulo}
                        </p>
                      )}

                      {item.trecho_destaque && (
                        <p className="text-sm text-[var(--ink)] mt-2 leading-relaxed">
                          {item.trecho_destaque}
                        </p>
                      )}

                      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 pt-2.5 border-t border-[var(--border)]/60 text-xs">
                        <Link
                          href={item.url_interna}
                          className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] hover:underline"
                        >
                          Ver detalhes no Cerrado Aberto
                          <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                        </Link>
                        {item.fonte_url && (
                          <a
                            href={item.fonte_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[var(--ink-muted)] hover:text-[var(--primary)] underline"
                          >
                            Conferir na fonte oficial
                            <ExternalLink className="w-3 h-3" aria-hidden="true" />
                          </a>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            {resultado.total_pages > 1 && (
              <div className="flex items-center justify-between pt-2 text-sm">
                <button
                  type="button"
                  disabled={page <= 1 || isPending}
                  onClick={() => executarBusca(termo, categoria, ano, page - 1)}
                  className="rounded-lg border border-[var(--border)] px-3.5 py-2 font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
                >
                  Página anterior
                </button>
                <span className="text-xs text-[var(--ink-muted)] tabular-nums">
                  Página {page} de {resultado.total_pages}
                </span>
                <button
                  type="button"
                  disabled={page >= resultado.total_pages || isPending}
                  onClick={() => executarBusca(termo, categoria, ano, page + 1)}
                  className="rounded-lg border border-[var(--border)] px-3.5 py-2 font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
                >
                  Próxima página
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
