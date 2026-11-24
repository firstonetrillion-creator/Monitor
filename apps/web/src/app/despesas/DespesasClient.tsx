"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, Download, ExternalLink, Search } from "lucide-react";
import { api } from "@/lib/api";
import { baixarCsvNoNavegador } from "@/lib/csv";
import type {
  DespesaEmpenhoOut,
  DespesasResumoOut,
  DuodecimoOut,
  PaginacaoOut,
} from "@/lib/types";
import {
  formatarBRL,
  formatarDataBR,
  formatarDataHoraBR,
  formatarDocumentoFavorecido,
  rotuloFonte,
} from "@/lib/format";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { GlossarioTooltip } from "@/components/GlossarioTooltip";
import { DespesasGraficosSection } from "./DespesasGraficosSection";
import { DuodecimoSection } from "./DuodecimoSection";

interface DespesasClientProps {
  initialResumo: DespesasResumoOut;
  initialLista: PaginacaoOut<DespesaEmpenhoOut>;
  duodecimo: DuodecimoOut[];
}

export function DespesasClient({
  initialResumo,
  initialLista,
  duodecimo,
}: DespesasClientProps) {
  const [resumo, setResumo] = useState<DespesasResumoOut>(initialResumo);
  const [lista, setLista] = useState<PaginacaoOut<DespesaEmpenhoOut>>(initialLista);

  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [fornecedorId, setFornecedorId] = useState("");
  const [elementoDespesa, setElementoDespesa] = useState("");
  const [q, setQ] = useState("");
  const [apenasDiaria, setApenasDiaria] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandidoId, setExpandidoId] = useState<string | null>(null);

  const buscar = async (opts?: {
    page?: number;
    dataInicio?: string;
    dataFim?: string;
    fornecedorId?: string;
    elementoDespesa?: string;
    q?: string;
    apenasDiaria?: boolean;
  }) => {
    const p = {
      ano: 2026,
      page: opts?.page ?? 1,
      per_page: 20,
      data_inicio: (opts?.dataInicio ?? dataInicio) || undefined,
      data_fim: (opts?.dataFim ?? dataFim) || undefined,
      fornecedor_id: (opts?.fornecedorId ?? fornecedorId) || undefined,
      elemento_despesa: (opts?.elementoDespesa ?? elementoDespesa) || undefined,
      q: (opts?.q ?? q).trim() || undefined,
      eh_diaria: (opts?.apenasDiaria ?? apenasDiaria) ? true : undefined,
    };

    setLoading(true);
    setError(null);
    try {
      const [novoResumo, novaLista] = await Promise.all([
        api.despesasResumo({
          ano: 2026,
          data_inicio: p.data_inicio,
          data_fim: p.data_fim,
          fornecedor_id: p.fornecedor_id,
          elemento_despesa: p.elemento_despesa,
          q: p.q,
          eh_diaria: p.eh_diaria,
        }),
        api.despesas(p),
      ]);
      setResumo(novoResumo);
      setLista(novaLista);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao filtrar despesas públicas.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void buscar({ page: 1 });
  };

  const limparFiltros = () => {
    setDataInicio("");
    setDataFim("");
    setFornecedorId("");
    setElementoDespesa("");
    setQ("");
    setApenasDiaria(false);
    void buscar({
      page: 1,
      dataInicio: "",
      dataFim: "",
      fornecedorId: "",
      elementoDespesa: "",
      q: "",
      apenasDiaria: false,
    });
  };

  const exportarEmpenhosPaginaCsv = () => {
    baixarCsvNoNavegador(
      `empenhos-2026-pagina-${lista.page}.csv`,
      [
        "Número Empenho",
        "Data",
        "Favorecido",
        "Documento",
        "Tipo Pessoa",
        "Elemento de Despesa",
        "Empenhado Bruto (R$)",
        "Anulação (R$)",
        "Empenhado Líquido (R$)",
        "Liquidado (R$)",
        "Pago (R$)",
        "Saldo a Pagar (R$)",
        "Histórico",
        "Fonte URL",
        "Coletado em",
      ],
      lista.items.map((emp) => [
        emp.numero_empenho,
        formatarDataBR(emp.data_empenho),
        emp.favorecido_nome,
        formatarDocumentoFavorecido(emp.documento_favorecido, emp.tipo_pessoa_favorecido),
        emp.tipo_pessoa_favorecido,
        emp.elemento_despesa || "Não classificado",
        emp.valor_empenhado_bruto,
        emp.valor_anulacao,
        emp.valor_empenhado_liquido,
        emp.valor_liquidado,
        emp.valor_pago,
        emp.saldo_pagar,
        emp.historico,
        emp.proveniencia.fonte_url,
        formatarDataHoraBR(emp.proveniencia.coletado_em),
      ]),
    );
  };

  return (
    <div className="space-y-8">
      {/* Totais dos estágios da despesa */}
      <section aria-labelledby="sec-estagios" className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="sec-estagios" className="text-xl font-bold text-[var(--ink)]">
            Estágios da despesa no recorte ({resumo.totais.quantidade_empenhos} empenhos)
          </h2>
          {resumo.data_primeiro_empenho && resumo.data_ultimo_empenho && (
            <p className="text-xs text-[var(--ink-muted)] tabular-nums">
              Período: {formatarDataBR(resumo.data_primeiro_empenho)} a{" "}
              {formatarDataBR(resumo.data_ultimo_empenho)}
            </p>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
              <GlossarioTooltip termo="empenho" label="Empenho bruto" />
            </p>
            <p className="mt-1 text-lg font-bold tabular-nums">
              {formatarBRL(resumo.totais.valor_empenhado_bruto)}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
              Anulações
            </p>
            <p className="mt-1 text-lg font-bold tabular-nums">
              {formatarBRL(resumo.totais.valor_anulacao)}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
              Empenho líquido
            </p>
            <p className="mt-1 text-lg font-bold tabular-nums text-[var(--primary)]">
              {formatarBRL(resumo.totais.valor_empenhado_liquido)}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
              <GlossarioTooltip termo="liquidacao" label="Liquidado" />
            </p>
            <p className="mt-1 text-lg font-bold tabular-nums">
              {formatarBRL(resumo.totais.valor_liquidado)}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
              <GlossarioTooltip termo="pagamento" label="Pago" />
            </p>
            <p className="mt-1 text-lg font-bold tabular-nums text-[var(--accent)]">
              {formatarBRL(resumo.totais.valor_pago)}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--ink-muted)]">
          <p>
            {resumo.nota_metodologica}
            {resumo.ultima_coleta_em
              ? ` Fonte: Portal da Transparência CENTI · Última coleta verificada: ${formatarDataHoraBR(resumo.ultima_coleta_em)}.`
              : ""}
          </p>
          <Link
            href="/como-calculamos"
            className="underline font-semibold hover:text-[var(--primary)] shrink-0"
          >
            Como calculamos
          </Link>
        </div>
      </section>

      <DuodecimoSection duodecimo={duodecimo} />

      {/* Filtros */}
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-4"
      >
        <h2 className="text-lg font-bold text-[var(--ink)]">Filtrar empenhos</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label htmlFor="desp-inicio" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Data inicial
            </label>
            <input
              id="desp-inicio"
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            />
          </div>
          <div>
            <label htmlFor="desp-fim" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Data final
            </label>
            <input
              id="desp-fim"
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            />
          </div>
          <div>
            <label htmlFor="desp-elemento" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Classificação (Elemento de despesa)
            </label>
            <select
              id="desp-elemento"
              value={elementoDespesa}
              onChange={(e) => setElementoDespesa(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            >
              <option value="">Todas as classificações</option>
              {initialResumo.por_elemento.map((el) => {
                if (!el.elemento_despesa) return null;
                return (
                  <option key={el.elemento_despesa} value={el.elemento_despesa}>
                    {el.elemento_despesa} ({el.quantidade_empenhos})
                  </option>
                );
              })}
            </select>
          </div>
          <div>
            <label htmlFor="desp-fornecedor" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Fornecedor / Favorecido
            </label>
            <select
              id="desp-fornecedor"
              value={fornecedorId}
              onChange={(e) => setFornecedorId(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            >
              <option value="">Todos os favorecidos</option>
              {initialResumo.favorecidos.map((f) => (
                <option key={f.fornecedor_id} value={f.fornecedor_id}>
                  {f.favorecido_nome} ({f.quantidade_empenhos})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="desp-busca" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Palavra-chave, histórico ou nº do empenho
            </label>
            <div className="relative">
              <Search
                className="w-4 h-4 text-[var(--ink-muted)] absolute left-3 top-1/2 -translate-y-1/2"
                aria-hidden="true"
              />
              <input
                id="desp-busca"
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Ex.: combustível, energia, 224943..."
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] pl-9 pr-3 py-2 text-sm text-[var(--ink)]"
              />
            </div>
          </div>
          <div className="flex flex-col justify-end gap-2">
            <label className="flex items-center gap-2 text-sm text-[var(--ink)] cursor-pointer">
              <input
                type="checkbox"
                checked={apenasDiaria}
                onChange={(e) => setApenasDiaria(e.target.checked)}
                className="w-4 h-4 accent-[var(--primary)]"
              />
              <span>Somente diárias (Elemento 14)</span>
            </label>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-4 py-2 text-sm font-semibold hover:opacity-90 disabled:opacity-60"
              >
                {loading ? "Aplicando..." : "Aplicar filtros"}
              </button>
              <button
                type="button"
                onClick={limparFiltros}
                className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--ink)] hover:bg-[var(--surface-alt)]"
              >
                Limpar
              </button>
            </div>
          </div>
        </div>
      </form>

      {error && <EstadoErroAPI mensagem={error} onTentarNovamente={() => void buscar()} />}

      <DespesasGraficosSection resumo={resumo} />

      {/* Tabela paginada de empenhos */}
      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-bold text-[var(--ink)]">
              Lista de empenhos ({lista.total})
            </h2>
            <p className="text-xs text-[var(--ink-muted)] tabular-nums">
              Página {lista.page} de {Math.max(1, lista.total_pages)}
            </p>
          </div>
          {lista.items.length > 0 && (
            <button
              type="button"
              onClick={exportarEmpenhosPaginaCsv}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Baixar CSV desta página
            </button>
          )}
        </div>

        {lista.items.length === 0 ? (
          <EstadoAusente
            titulo="Nenhum empenho encontrado para os filtros aplicados"
            descricao="Altere o período, favorecido ou classificação para ver outros registros."
          />
        ) : (
          <div
            className="overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabela de empenhos de despesas públicas"
          >
            <table className="w-full text-left text-sm border-collapse min-w-[820px]">
              <thead className="sticky top-0 bg-[var(--surface)] z-10">
                <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                  <th scope="col" className="py-2 pr-3">Data / Empenho</th>
                  <th scope="col" className="py-2 pr-3">Favorecido</th>
                  <th scope="col" className="py-2 pr-3">Classificação</th>
                  <th scope="col" className="py-2 pr-3 text-right">Empenhado líq.</th>
                  <th scope="col" className="py-2 pr-3 text-right">Liquidado</th>
                  <th scope="col" className="py-2 pr-3 text-right">Pago</th>
                  <th scope="col" className="py-2 text-right">Detalhes</th>
                </tr>
              </thead>
              <tbody>
                {lista.items.map((emp) => {
                  const aberto = expandidoId === emp.empenho_id;
                  return (
                    <Fragment key={emp.empenho_id}>
                      <tr className="border-b border-[var(--border)]/60">
                        <td className="py-3 pr-3 tabular-nums whitespace-nowrap">
                          <span className="font-semibold">{formatarDataBR(emp.data_empenho)}</span>
                          <span className="block text-xs font-mono text-[var(--ink-muted)]">
                            #{emp.numero_empenho}
                          </span>
                        </td>
                        <td className="py-3 pr-3">
                          <span className="font-semibold text-[var(--ink)]">
                            {emp.favorecido_nome}
                          </span>
                          <span className="block text-[11px] text-[var(--ink-muted)]">
                            {formatarDocumentoFavorecido(
                              emp.documento_favorecido,
                              emp.tipo_pessoa_favorecido,
                            )}
                          </span>
                        </td>
                        <td className="py-3 pr-3 text-xs text-[var(--ink-muted)] max-w-xs">
                          {emp.elemento_despesa || "Não classificado"}
                        </td>
                        <td className="py-3 pr-3 text-right tabular-nums whitespace-nowrap">
                          {formatarBRL(emp.valor_empenhado_liquido)}
                        </td>
                        <td className="py-3 pr-3 text-right tabular-nums whitespace-nowrap">
                          {formatarBRL(emp.valor_liquidado)}
                        </td>
                        <td className="py-3 pr-3 text-right font-bold tabular-nums whitespace-nowrap">
                          {formatarBRL(emp.valor_pago)}
                        </td>
                        <td className="py-3 text-right whitespace-nowrap">
                          <button
                            type="button"
                            aria-expanded={aberto}
                            onClick={() =>
                              setExpandidoId(aberto ? null : emp.empenho_id)
                            }
                            className="inline-flex items-center gap-1 rounded-lg border border-[var(--border)] px-2.5 py-1 text-xs font-semibold hover:border-[var(--primary)]"
                          >
                            {aberto ? (
                              <>
                                Fechar <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
                              </>
                            ) : (
                              <>
                                Ver <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
                              </>
                            )}
                          </button>
                        </td>
                      </tr>
                      {aberto && (
                        <tr className="bg-[var(--surface-alt)]">
                          <td colSpan={7} className="p-4 text-xs space-y-2">
                            <p>
                              <strong>Histórico publicado:</strong> {emp.historico}
                            </p>
                            <div className="flex flex-wrap gap-4 text-[var(--ink-muted)]">
                              <span>
                                <strong>Bruto:</strong> {formatarBRL(emp.valor_empenhado_bruto)}
                              </span>
                              <span>
                                <strong>Anulação:</strong> {formatarBRL(emp.valor_anulacao)}
                              </span>
                              <span>
                                <strong>Saldo a pagar:</strong> {formatarBRL(emp.saldo_pagar)}
                              </span>
                              <span>
                                <strong>Processo:</strong>{" "}
                                {emp.processo_licitatorio || "Não informado"}
                              </span>
                              <span>
                                <strong>Fonte de recurso:</strong>{" "}
                                {emp.fonte_recurso || "Não informada"}
                              </span>
                            </div>
                            <div className="pt-2 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-2 text-[var(--ink-muted)]">
                              <span>
                                Fonte: {rotuloFonte(emp.proveniencia.fonte_id)} · Coleta:{" "}
                                {formatarDataHoraBR(emp.proveniencia.coletado_em)}
                              </span>
                              <a
                                href={emp.proveniencia.fonte_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 underline hover:text-[var(--primary)]"
                              >
                                Abrir portal oficial{" "}
                                <ExternalLink className="w-3 h-3" aria-hidden="true" />
                              </a>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginação */}
        {lista.total_pages > 1 && (
          <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
            <button
              type="button"
              disabled={lista.page <= 1 || loading}
              onClick={() => void buscar({ page: lista.page - 1 })}
              className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-sm font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
            >
              Anterior
            </button>
            <span className="text-xs text-[var(--ink-muted)] tabular-nums">
              Página {lista.page} de {lista.total_pages}
            </span>
            <button
              type="button"
              disabled={lista.page >= lista.total_pages || loading}
              onClick={() => void buscar({ page: lista.page + 1 })}
              className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-sm font-medium disabled:opacity-40 hover:bg-[var(--surface-alt)]"
            >
              Próxima
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
