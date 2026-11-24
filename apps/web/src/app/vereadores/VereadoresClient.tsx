"use client";

import { useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import type { PaginacaoOut, VereadorResumoOut } from "@/lib/types";
import { formatarBRL, formatarInteiro, rotuloFonte } from "@/lib/format";
import { AvatarVereador } from "@/components/AvatarVereador";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";

interface VereadoresClientProps {
  initialData: PaginacaoOut<VereadorResumoOut>;
}

export function VereadoresClient({ initialData }: VereadoresClientProps) {
  const [data, setData] = useState<PaginacaoOut<VereadorResumoOut>>(initialData);
  const [q, setQ] = useState("");
  const [condicao, setCondicao] = useState("");
  const [apenasAtual, setApenasAtual] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const carregar = async (opts?: {
    page?: number;
    q?: string;
    condicao?: string;
    apenasAtual?: boolean;
  }) => {
    const nextQ = opts?.q ?? q;
    const nextCond = opts?.condicao ?? condicao;
    const nextAtual = opts?.apenasAtual ?? apenasAtual;
    const nextPage = opts?.page ?? 1;

    setLoading(true);
    setError(null);
    try {
      const result = await api.vereadores({
        page: nextPage,
        per_page: 50,
        q: nextQ.trim() || undefined,
        condicao: nextCond || undefined,
        apenas_legislatura_atual: nextAtual,
      });
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Não foi possível atualizar a lista de vereadores.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void carregar({ page: 1 });
  };

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 items-end"
      >
        <div>
          <label htmlFor="busca-vereador" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Buscar por nome
          </label>
          <div className="relative">
            <Search
              className="w-4 h-4 text-[var(--ink-muted)] absolute left-3 top-1/2 -translate-y-1/2"
              aria-hidden="true"
            />
            <input
              id="busca-vereador"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ex.: Kelvy, Jôsy, Hugo..."
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] pl-9 pr-3 py-2 text-sm text-[var(--ink)]"
            />
          </div>
        </div>

        <div>
          <label htmlFor="filtro-condicao" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
            Condição do mandato
          </label>
          <select
            id="filtro-condicao"
            value={condicao}
            onChange={(e) => {
              const val = e.target.value;
              setCondicao(val);
              void carregar({ condicao: val, page: 1 });
            }}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
          >
            <option value="">Todas</option>
            <option value="TITULAR">Titular</option>
            <option value="SUPLENTE">Suplente</option>
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm text-[var(--ink)] py-2 cursor-pointer">
          <input
            type="checkbox"
            checked={apenasAtual}
            onChange={(e) => {
              const checked = e.target.checked;
              setApenasAtual(checked);
              void carregar({ apenasAtual: checked, page: 1 });
            }}
            className="w-4 h-4 accent-[var(--primary)]"
          />
          <span>Somente legislatura 2025–2028</span>
        </label>

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
              setQ("");
              setCondicao("");
              setApenasAtual(true);
              void carregar({ q: "", condicao: "", apenasAtual: true, page: 1 });
            }}
            className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--ink)] hover:bg-[var(--surface-alt)]"
          >
            Limpar
          </button>
        </div>
      </form>

      {error && <EstadoErroAPI mensagem={error} onTentarNovamente={() => void carregar()} />}

      <p className="text-sm text-[var(--ink-muted)] tabular-nums">
        Exibindo {data.items.length} de {data.total} vereadores encontrados.
      </p>

      {data.items.length === 0 ? (
        <EstadoAusente
          titulo="Nenhum vereador encontrado para estes filtros"
          descricao="Tente limpar a busca ou incluir legislaturas anteriores."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.items.map((v) => (
            <Link
              key={v.vereador_id}
              href={`/vereadores/${v.vereador_id}`}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 hover:border-[var(--primary)] transition-colors flex flex-col justify-between gap-4"
            >
              <div className="flex items-start gap-3.5">
                <AvatarVereador nome={v.nome_exibicao} />
                <div className="min-w-0">
                  <h2 className="text-lg font-bold text-[var(--ink)] leading-snug">
                    {v.nome_exibicao}
                  </h2>
                  {v.nome_civil && v.nome_civil !== v.nome_exibicao && (
                    <p className="text-xs text-[var(--ink-muted)] truncate">{v.nome_civil}</p>
                  )}
                  <div className="mt-1.5 flex flex-wrap gap-1.5 text-[11px]">
                    <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 font-medium text-[var(--ink-muted)]">
                      {v.condicao_mandato_2025_2028 || "Legislatura anterior"}
                    </span>
                    <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 font-medium text-[var(--ink-muted)]">
                      Partido: {v.partido_sigla || "Não informado na fonte"}
                    </span>
                  </div>
                </div>
              </div>

              <dl className="grid grid-cols-2 gap-3 pt-3 border-t border-[var(--border)] text-xs">
                <div>
                  <dt className="text-[var(--ink-muted)]">Presenças 2026</dt>
                  <dd className="mt-0.5 font-bold text-sm tabular-nums text-[var(--ink)]">
                    {formatarInteiro(v.sessoes_presente_2026)} sessões
                  </dd>
                </div>
                <div>
                  <dt className="text-[var(--ink-muted)]">Proposições 2026</dt>
                  <dd className="mt-0.5 font-bold text-sm tabular-nums text-[var(--ink)]">
                    {formatarInteiro(v.total_proposicoes_parlamentares_2026)}
                  </dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-[var(--ink-muted)]">
                    Custo da Estrutura do Mandato (2026, {v.competencias_custo_fechadas_2026} meses fechados)
                  </dt>
                  <dd
                    className={`mt-0.5 font-bold text-sm tabular-nums ${
                      v.custo_estrutura_mandato_acumulado_2026
                        ? "text-[var(--primary)]"
                        : "text-[var(--ink-muted)] italic font-medium"
                    }`}
                  >
                    {v.custo_estrutura_mandato_acumulado_2026
                      ? formatarBRL(v.custo_estrutura_mandato_acumulado_2026)
                      : "Não apurado no total (há lacuna de lotação ou competência)"}
                  </dd>
                </div>
              </dl>

              <p className="text-[11px] text-[var(--ink-muted)]">
                Fonte: {rotuloFonte(v.proveniencia.fonte_id)}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
