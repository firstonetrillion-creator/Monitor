"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { Download, ExternalLink, Search, BookOpen } from "lucide-react";
import type { NormasListagemOut } from "@/lib/types";
import { api } from "@/lib/api";
import { baixarCsvNoNavegador } from "@/lib/csv";
import { formatarDataBR, formatarInteiro } from "@/lib/format";

interface LegislacaoClientProps {
  inicial: NormasListagemOut;
}

function rotuloStatusOcr(status: string): string {
  switch (status) {
    case "TEXTO_NATIVO_PDF":
      return "Texto integral disponível";
    case "OCR_CONCLUIDO":
      return "Texto extraído por OCR";
    case "PENDENTE_OCR":
      return "PDF escaneado (OCR pendente)";
    default:
      return "Metadados e ementa oficiais";
  }
}

export function LegislacaoClient({ inicial }: LegislacaoClientProps) {
  const [dados, setDados] = useState<NormasListagemOut>(inicial);
  const [q, setQ] = useState("");
  const [categoria, setCategoria] = useState("");
  const [ano, setAno] = useState("");
  const [isPending, startTransition] = useTransition();

  function carregar(novoQ: string, novaCat: string, novoAno: string, novaPag = 1) {
    startTransition(async () => {
      const res = await api.legislacao({
        q: novoQ.trim() || undefined,
        categoria: novaCat || undefined,
        ano: novoAno ? Number(novoAno) : undefined,
        page: novaPag,
        per_page: 20,
      });
      setDados(res);
    });
  }

  function aoSubmeter(e: React.FormEvent) {
    e.preventDefault();
    carregar(q, categoria, ano, 1);
  }

  function exportarCsvPagina() {
    baixarCsvNoNavegador(
      `cerrado-aberto-legislacao-inhumas-pag-${dados.page}.csv`,
      ["Número", "Ano", "Categoria", "Data de Publicação", "Ementa", "Status de Extração", "URL Oficial"],
      dados.items.map((n) => [
        n.numero,
        n.ano,
        n.categoria_descricao,
        n.data_publicacao ? formatarDataBR(n.data_publicacao) : null,
        n.ementa,
        rotuloStatusOcr(n.status_ocr),
        n.fonte_url,
      ]),
    );
  }

  return (
    <div className="space-y-6">
      <form
        onSubmit={aoSubmeter}
        role="search"
        aria-label="Pesquisar na legislação municipal"
        className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 grid gap-3 md:grid-cols-[1fr_200px_130px_auto] items-end"
      >
        <div>
          <label htmlFor="lei-busca" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Buscar por número ou assunto
          </label>
          <input
            id="lei-busca"
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ex.: 3577, estatuto, plano diretor, educação..."
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3.5 py-2.5 text-sm"
          />
        </div>
        <div>
          <label htmlFor="lei-cat" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Categoria normativa
          </label>
          <select
            id="lei-cat"
            value={categoria}
            onChange={(e) => {
              setCategoria(e.target.value);
              carregar(q, e.target.value, ano, 1);
            }}
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 py-2.5 text-sm"
          >
            <option value="">Todas ({dados.categorias_disponiveis.length})</option>
            {dados.categorias_disponiveis.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="lei-ano" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Ano
          </label>
          <select
            id="lei-ano"
            value={ano}
            onChange={(e) => {
              setAno(e.target.value);
              carregar(q, categoria, e.target.value, 1);
            }}
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 py-2.5 text-sm"
          >
            <option value="">Todos</option>
            {dados.anos_disponiveis.map((a) => (
              <option key={a} value={String(a)}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={isPending}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--primary)] text-[var(--primary-ink)] px-5 py-2.5 text-sm font-semibold hover:opacity-95"
        >
          <Search className="w-4 h-4" aria-hidden="true" />
          {isPending ? "Filtrando..." : "Pesquisar"}
        </button>
      </form>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <p className="text-[var(--ink-muted)]">
          Exibindo <strong className="text-[var(--ink)] tabular-nums">{formatarInteiro(dados.total)}</strong>{" "}
          norma(s) encontrada(s).
        </p>
        <button
          type="button"
          onClick={exportarCsvPagina}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
        >
          <Download className="w-3.5 h-3.5" aria-hidden="true" />
          Baixar página em CSV
        </button>
      </div>

      {dados.items.length === 0 ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--ink-muted)]">
          Nenhuma lei encontrada com esses filtros.
        </div>
      ) : (
        <ul className="space-y-3">
          {dados.items.map((n) => (
            <li
              key={n.norma_id}
              className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 hover:border-[var(--primary)]/50 transition-colors"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs mb-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-[var(--primary)]/10 text-[var(--primary)] px-2.5 py-0.5 font-semibold">
                    {n.categoria_descricao}
                  </span>
                  <span className="rounded-full bg-[var(--surface-alt)] text-[var(--ink-muted)] px-2.5 py-0.5 font-medium">
                    {rotuloStatusOcr(n.status_ocr)}
                  </span>
                </div>
                <span className="text-[var(--ink-muted)] tabular-nums">
                  Publicada em {formatarDataBR(n.data_publicacao)}
                </span>
              </div>

              <h2 className="font-display text-lg font-bold text-[var(--ink)]">
                <Link
                  href={`/legislacao/${n.norma_id}`}
                  className="hover:text-[var(--primary)] hover:underline"
                >
                  {n.categoria_descricao} nº {n.numero}
                  {n.ano ? `/${n.ano}` : ""}
                </Link>
              </h2>

              <p className="mt-1.5 text-sm text-[var(--ink)] leading-relaxed">{n.ementa}</p>

              <div className="mt-3 pt-2.5 border-t border-[var(--border)]/60 flex flex-wrap items-center justify-between gap-3 text-xs">
                <Link
                  href={`/legislacao/${n.norma_id}`}
                  className="inline-flex items-center gap-1.5 font-semibold text-[var(--primary)] hover:underline"
                >
                  <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
                  Abrir resumo em linguagem simples e proveniência
                </Link>
                <a
                  href={n.fonte_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[var(--ink-muted)] hover:text-[var(--primary)] underline"
                >
                  Página oficial da lei ({n.total_anexos} anexo{n.total_anexos === 1 ? "" : "s"})
                  <ExternalLink className="w-3 h-3" aria-hidden="true" />
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}

      {dados.total_pages > 1 && (
        <div className="flex items-center justify-between pt-2 text-sm">
          <button
            type="button"
            disabled={dados.page <= 1 || isPending}
            onClick={() => carregar(q, categoria, ano, dados.page - 1)}
            className="rounded-lg border border-[var(--border)] px-3.5 py-2 font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
          >
            Página anterior
          </button>
          <span className="text-xs text-[var(--ink-muted)] tabular-nums">
            Página {dados.page} de {dados.total_pages}
          </span>
          <button
            type="button"
            disabled={dados.page >= dados.total_pages || isPending}
            onClick={() => carregar(q, categoria, ano, dados.page + 1)}
            className="rounded-lg border border-[var(--border)] px-3.5 py-2 font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
          >
            Próxima página
          </button>
        </div>
      )}

      <aside className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--ink-muted)] leading-relaxed">
        <strong className="text-[var(--ink)]">Cobertura e acesso ao PDF oficial (ADR-004):</strong>{" "}
        {dados.nota_cobertura}
      </aside>
    </div>
  );
}
