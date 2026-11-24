"use client";

import { useState } from "react";
import Link from "next/link";
import { Download, Search } from "lucide-react";
import { api } from "@/lib/api";
import { baixarCsvNoNavegador } from "@/lib/csv";
import type { FolhaPagamentoOut, PaginacaoOut, VereadorResumoOut } from "@/lib/types";
import {
  formatarBRL,
  formatarDocumentoFavorecido,
  formatarInteiro,
  nomeMesLongo,
} from "@/lib/format";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";

interface FolhaClientProps {
  initialData: PaginacaoOut<FolhaPagamentoOut>;
  vereadores: VereadorResumoOut[];
  initialFilters: {
    mes: number;
    gabineteVereadorId: string;
    apenasVereadores: boolean;
    q: string;
  };
}

export function FolhaClient({
  initialData,
  vereadores,
  initialFilters,
}: FolhaClientProps) {
  const [dados, setDados] = useState<PaginacaoOut<FolhaPagamentoOut>>(initialData);
  const [mes, setMes] = useState<number>(initialFilters.mes);
  const [gabineteId, setGabineteId] = useState<string>(initialFilters.gabineteVereadorId);
  const [apenasVereadores, setApenasVereadores] = useState<boolean>(
    initialFilters.apenasVereadores,
  );
  const [q, setQ] = useState<string>(initialFilters.q);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buscar = async (opts?: {
    page?: number;
    mes?: number;
    gabineteId?: string;
    apenasVereadores?: boolean;
    q?: string;
  }) => {
    const nextMes = opts?.mes ?? mes;
    const nextGab = opts?.gabineteId ?? gabineteId;
    const nextVer = opts?.apenasVereadores ?? apenasVereadores;
    const nextQ = opts?.q ?? q;

    setLoading(true);
    setError(null);
    try {
      const res = await api.folha({
        ano: 2026,
        mes: nextMes === 0 ? undefined : nextMes,
        gabinete_vereador_id: nextGab || undefined,
        apenas_vereadores: nextVer ? true : undefined,
        q: nextQ.trim() || undefined,
        page: opts?.page ?? 1,
        per_page: 20,
      });
      setDados(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao consultar a folha de pagamento.",
      );
    } finally {
      setLoading(false);
    }
  };

  const limparFiltros = () => {
    setMes(10);
    setGabineteId("");
    setApenasVereadores(false);
    setQ("");
    void buscar({ page: 1, mes: 10, gabineteId: "", apenasVereadores: false, q: "" });
  };

  const exportarCsvPagina = () => {
    baixarCsvNoNavegador(
      `cerrado-aberto-folha-2026-pag-${dados.page}.csv`,
      [
        "Referência",
        "Matrícula",
        "Servidor",
        "CPF Mascarado",
        "Cargo",
        "Vínculo",
        "Lotação",
        "Tipo de Folha",
        "Salário Base (R$)",
        "Remuneração Bruta (R$)",
        "Descontos (R$)",
        "Remuneração Líquida (R$)",
        "Fonte URL",
      ],
      dados.items.map((r) => [
        r.referencia,
        r.matricula,
        r.nome_servidor,
        formatarDocumentoFavorecido(r.cpf_mascarado, "PESSOA_FISICA"),
        r.cargo,
        r.tipo_admissao,
        r.lotacao,
        r.tipo_folha,
        r.salario_base,
        r.remuneracao_bruta,
        r.descontos,
        r.remuneracao_liquida,
        r.proveniencia.fonte_url,
      ]),
    );
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void buscar({ page: 1 });
        }}
        role="search"
        aria-label="Filtrar folha de pagamento de 2026"
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 space-y-4"
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 items-end">
          <div>
            <label htmlFor="folha-busca" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Nome, cargo ou lotação
            </label>
            <input
              id="folha-busca"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ex.: assessor, PRESIDENCIA, motorista..."
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            />
          </div>

          <div>
            <label htmlFor="folha-mes" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Competência (2026)
            </label>
            <select
              id="folha-mes"
              value={mes}
              onChange={(e) => {
                const novoMes = Number(e.target.value);
                setMes(novoMes);
                void buscar({ mes: novoMes, page: 1 });
              }}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            >
              <option value={0}>Todos os meses publicados (jan–out/2026)</option>
              {Array.from({ length: 12 }, (_, idx) => idx + 1).map((m) => (
                <option key={m} value={m}>
                  {nomeMesLongo(m)}/2026 {m >= 11 ? "(em aberto)" : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="folha-gabinete" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Gabinete de vereador(a)
            </label>
            <select
              id="folha-gabinete"
              value={gabineteId}
              onChange={(e) => {
                const val = e.target.value;
                setGabineteId(val);
                void buscar({ gabineteId: val, page: 1 });
              }}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            >
              <option value="">Todos os setores e gabinetes</option>
              {vereadores.map((v) => (
                <option key={v.vereador_id} value={v.vereador_id}>
                  {v.nome_exibicao}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 pb-1">
            <input
              id="folha-apenas-ver"
              type="checkbox"
              checked={apenasVereadores}
              onChange={(e) => {
                const checked = e.target.checked;
                setApenasVereadores(checked);
                void buscar({ apenasVereadores: checked, page: 1 });
              }}
              className="h-4 w-4 rounded border-[var(--border)]"
            />
            <label htmlFor="folha-apenas-ver" className="text-sm text-[var(--ink)] cursor-pointer">
              Somente vereadores
            </label>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-4 py-2 text-sm font-semibold hover:opacity-90 disabled:opacity-60"
            >
              <Search className="w-4 h-4" aria-hidden="true" />
              {loading ? "Consultando..." : "Filtrar"}
            </button>
            <button
              type="button"
              onClick={limparFiltros}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-2 text-sm font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
            >
              Limpar
            </button>
          </div>

          <button
            type="button"
            onClick={exportarCsvPagina}
            disabled={dados.items.length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3.5 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)] disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" aria-hidden="true" />
            Baixar CSV
          </button>
        </div>
      </form>

      {error && <EstadoErroAPI mensagem={error} onTentarNovamente={() => void buscar()} />}

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--ink-muted)]">
        <span className="tabular-nums">
          Mostrando <strong>{dados.items.length}</strong> de{" "}
          <strong>{formatarInteiro(dados.total)}</strong> registro(s) encontrado(s)
        </span>
        <span className="tabular-nums">
          Página {dados.page} de {dados.total_pages}
        </span>
      </div>

      {dados.items.length === 0 ? (
        <EstadoAusente
          titulo="Nenhum registro publicado para estes filtros"
          descricao={
            mes >= 11
              ? "As competências 11/2026 e 12/2026 ainda não foram fechadas/publicadas no Portal da Transparência."
              : "Tente limpar a busca ou selecionar todos os meses publicados (jan–out/2026)."
          }
        />
      ) : (
        <div
          className="responsive-table-wrapper rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5"
          tabIndex={0}
          role="region"
          aria-labelledby="folha-table-caption"
        >
          <table className="w-full text-left text-sm min-w-[760px]">
            <caption id="folha-table-caption" className="sr-only">
              Folha de pagamento e lotação da Câmara Municipal de Inhumas em 2026
            </caption>
            <thead>
              <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                <th scope="col" className="py-2.5 pr-3">Servidor / Cargo</th>
                <th scope="col" className="py-2.5 pr-3">Lotação</th>
                <th scope="col" className="py-2.5 pr-3">Competência</th>
                <th scope="col" className="py-2.5 pr-3 text-right">Bruto</th>
                <th scope="col" className="py-2.5 pr-3 text-right">Descontos</th>
                <th scope="col" className="py-2.5 text-right">Líquido</th>
              </tr>
            </thead>
            <tbody>
              {dados.items.map((r) => (
                <tr key={r.folha_id} className="border-b border-[var(--border)]/60 align-top">
                  <th scope="row" className="py-3 pr-3 font-normal">
                    {r.vereador_id ? (
                      <Link
                        href={`/vereadores/${r.vereador_id}`}
                        className="font-semibold text-[var(--primary)] hover:underline"
                      >
                        {r.nome_servidor}
                      </Link>
                    ) : (
                      <span className="font-semibold text-[var(--ink)]">{r.nome_servidor}</span>
                    )}
                    <p className="text-xs text-[var(--ink-muted)]">{r.cargo}</p>
                    <p className="text-[11px] text-[var(--ink-muted)]">
                      {r.tipo_admissao || "Vínculo não informado"} · Mat. {r.matricula}
                    </p>
                  </th>
                  <td data-label="Lotação" className="py-3 pr-3 text-xs">
                    {r.gabinete_vereador_id ? (
                      <Link
                        href={`/vereadores/${r.gabinete_vereador_id}`}
                        className="text-[var(--primary)] font-medium hover:underline"
                      >
                        {r.lotacao}
                      </Link>
                    ) : (
                      <span className="text-[var(--ink)]">{r.lotacao}</span>
                    )}
                  </td>
                  <td data-label="Competência" className="py-3 pr-3 text-xs tabular-nums whitespace-nowrap">
                    <span className="font-medium text-[var(--ink)]">{r.referencia}</span>
                    <p className="text-[var(--ink-muted)]">{r.tipo_folha}</p>
                  </td>
                  <td data-label="Remuneração bruta" className="py-3 pr-3 text-right font-semibold tabular-nums whitespace-nowrap">
                    {formatarBRL(r.remuneracao_bruta, "Não publicado")}
                  </td>
                  <td data-label="Descontos" className="py-3 pr-3 text-right tabular-nums whitespace-nowrap text-[var(--ink-muted)]">
                    {formatarBRL(r.descontos, "Não publicado")}
                  </td>
                  <td data-label="Remuneração líquida" className="py-3 text-right font-bold tabular-nums whitespace-nowrap text-[var(--primary)]">
                    {formatarBRL(r.remuneracao_liquida, "Não publicado")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dados.total_pages > 1 && (
        <nav aria-label="Paginação da folha de pagamento" className="flex items-center justify-between pt-2">
          <button
            type="button"
            disabled={dados.page <= 1 || loading}
            onClick={() => void buscar({ page: dados.page - 1 })}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2 text-sm font-semibold disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="text-xs text-[var(--ink-muted)] tabular-nums">
            Página {dados.page} de {dados.total_pages}
          </span>
          <button
            type="button"
            disabled={dados.page >= dados.total_pages || loading}
            onClick={() => void buscar({ page: dados.page + 1 })}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2 text-sm font-semibold disabled:opacity-40"
          >
            Próxima
          </button>
        </nav>
      )}

      {dados.items[0] && <ProvenienciaBox proveniencia={dados.items[0].proveniencia} />}
    </div>
  );
}
