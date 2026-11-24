"use client";

import { useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import type { PaginacaoOut, SessaoResumoOut } from "@/lib/types";
import { formatarDataBR, rotuloFonte } from "@/lib/format";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";

interface SessoesClientProps {
  initialData: PaginacaoOut<SessaoResumoOut>;
}

export function SessoesClient({ initialData }: SessoesClientProps) {
  const [data, setData] = useState<PaginacaoOut<SessaoResumoOut>>(initialData);
  const [ano, setAno] = useState<string>("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buscar = async (opts?: {
    page?: number;
    ano?: string;
    dataInicio?: string;
    dataFim?: string;
    q?: string;
  }) => {
    const nextAno = opts?.ano ?? ano;
    const nextIni = opts?.dataInicio ?? dataInicio;
    const nextFim = opts?.dataFim ?? dataFim;
    const nextQ = opts?.q ?? q;

    setLoading(true);
    setError(null);
    try {
      const result = await api.sessoes({
        page: opts?.page ?? 1,
        per_page: 20,
        ano: nextAno ? Number(nextAno) : undefined,
        data_inicio: nextIni || undefined,
        data_fim: nextFim || undefined,
        q: nextQ.trim() || undefined,
      });
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao filtrar sessões plenárias.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void buscar({ page: 1 });
        }}
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5 items-end"
      >
        <div>
          <label htmlFor="sessao-ano" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Ano
          </label>
          <select
            id="sessao-ano"
            value={ano}
            onChange={(e) => {
              const val = e.target.value;
              setAno(val);
              void buscar({ ano: val, page: 1 });
            }}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
          >
            <option value="">2025 e 2026</option>
            <option value="2026">2026</option>
            <option value="2025">2025</option>
          </select>
        </div>

        <div>
          <label htmlFor="sessao-inicio" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Data inicial
          </label>
          <input
            id="sessao-inicio"
            type="date"
            value={dataInicio}
            onChange={(e) => setDataInicio(e.target.value)}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
          />
        </div>

        <div>
          <label htmlFor="sessao-fim" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Data final
          </label>
          <input
            id="sessao-fim"
            type="date"
            value={dataFim}
            onChange={(e) => setDataFim(e.target.value)}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
          />
        </div>

        <div>
          <label htmlFor="sessao-busca" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Buscar sessão
          </label>
          <div className="relative">
            <Search
              className="w-4 h-4 text-[var(--ink-muted)] absolute left-3 top-1/2 -translate-y-1/2"
              aria-hidden="true"
            />
            <input
              id="sessao-busca"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ex.: Ordinária, Extraordinária..."
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] pl-9 pr-3 py-2 text-sm text-[var(--ink)]"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-4 py-2 text-sm font-semibold hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Buscando..." : "Filtrar"}
          </button>
          <button
            type="button"
            onClick={() => {
              setAno("");
              setDataInicio("");
              setDataFim("");
              setQ("");
              void buscar({ page: 1, ano: "", dataInicio: "", dataFim: "", q: "" });
            }}
            className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--ink)] hover:bg-[var(--surface-alt)]"
          >
            Limpar
          </button>
        </div>
      </form>

      {error && <EstadoErroAPI mensagem={error} onTentarNovamente={() => void buscar()} />}

      <p className="text-sm text-[var(--ink-muted)] tabular-nums">
        {data.total} sessões encontradas (página {data.page} de {Math.max(1, data.total_pages)}).
      </p>

      {data.items.length === 0 ? (
        <EstadoAusente
          titulo="Nenhuma sessão encontrada"
          descricao="Ajuste os filtros de data ou ano para visualizar outras sessões."
        />
      ) : (
        <div className="space-y-3">
          {data.items.map((s) => (
            <Link
              key={s.sessao_id}
              href={`/sessoes/${s.sessao_id}`}
              className="block rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 hover:border-[var(--primary)] transition-colors"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-[var(--surface-alt)] px-2.5 py-0.5 font-semibold text-[var(--ink-muted)]">
                      {s.tipo_descricao}
                    </span>
                    <span className="tabular-nums text-[var(--ink-muted)]">
                      {formatarDataBR(s.data_abertura)}
                      {s.horario_abertura ? ` às ${s.horario_abertura}` : ""}
                    </span>
                  </div>
                  <h2 className="mt-2 text-lg font-bold text-[var(--ink)]">{s.nome_sessao}</h2>
                  <p className="mt-1 text-xs text-[var(--ink-muted)]">
                    Fonte: {rotuloFonte(s.proveniencia.fonte_id)}
                  </p>
                </div>

                <div className="flex flex-wrap gap-3 text-xs tabular-nums">
                  <span className="rounded-lg bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)] px-3 py-1.5 font-semibold">
                    {s.total_presentes} presentes
                  </span>
                  <span className="rounded-lg bg-[var(--surface-alt)] px-3 py-1.5 font-semibold text-[var(--ink)]">
                    {s.total_itens_pauta} itens na pauta
                  </span>
                  <span className="rounded-lg bg-[var(--surface-alt)] px-3 py-1.5 font-semibold text-[var(--ink)]">
                    {s.total_votacoes} votações
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {data.total_pages > 1 && (
        <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
          <button
            type="button"
            disabled={data.page <= 1 || loading}
            onClick={() => void buscar({ page: data.page - 1 })}
            className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-sm font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
          >
            Anterior
          </button>
          <span className="text-xs text-[var(--ink-muted)] tabular-nums">
            Página {data.page} de {data.total_pages}
          </span>
          <button
            type="button"
            disabled={data.page >= data.total_pages || loading}
            onClick={() => void buscar({ page: data.page + 1 })}
            className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-sm font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  );
}
