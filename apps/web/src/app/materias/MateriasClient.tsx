"use client";

import { useState } from "react";
import Link from "next/link";
import { Download, ExternalLink, Search } from "lucide-react";
import { api } from "@/lib/api";
import { baixarCsvNoNavegador } from "@/lib/csv";
import type { MateriaResumoOut, PaginacaoOut, VereadorResumoOut } from "@/lib/types";
import { formatarDataBR, formatarInteiro } from "@/lib/format";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";

const TIPOS_MATERIA_OPCOES: { id: number; label: string }[] = [
  { id: 5, label: "Requerimento" },
  { id: 113, label: "Projeto de Lei do Legislativo" },
  { id: 4, label: "Projeto de Lei" },
  { id: 6, label: "Indicação" },
  { id: 1, label: "Moção de Aplausos" },
  { id: 7, label: "Moção" },
  { id: 214, label: "Moção de Apoio" },
  { id: 3, label: "Projeto de Decreto Legislativo" },
  { id: 12, label: "Projeto de Resolução" },
  { id: 112, label: "Emenda" },
  { id: 10, label: "Projeto de Lei Complementar" },
  { id: 243, label: "PLC do Legislativo" },
  { id: 144, label: "Ata da Sessão (ato administrativo)" },
  { id: 211, label: "Julgamento de Contas (ato externo)" },
  { id: 375, label: "Mensagem do Prefeito" },
];

interface MateriasClientProps {
  initialData: PaginacaoOut<MateriaResumoOut>;
  vereadores: VereadorResumoOut[];
  initialFilters: {
    q: string;
    ano: string;
    tipoId: string;
    vereadorId: string;
    classificacao: string;
  };
}

export function MateriasClient({
  initialData,
  vereadores,
  initialFilters,
}: MateriasClientProps) {
  const [dados, setDados] = useState<PaginacaoOut<MateriaResumoOut>>(initialData);
  const [q, setQ] = useState(initialFilters.q);
  const [ano, setAno] = useState(initialFilters.ano);
  const [tipoId, setTipoId] = useState(initialFilters.tipoId);
  const [vereadorId, setVereadorId] = useState(initialFilters.vereadorId);
  const [classificacao, setClassificacao] = useState(initialFilters.classificacao);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resolverFlagParlamentar = (val: string): boolean | undefined => {
    if (val === "true") return true;
    if (val === "false") return false;
    return undefined;
  };

  const buscar = async (opts?: {
    page?: number;
    q?: string;
    ano?: string;
    tipoId?: string;
    vereadorId?: string;
    classificacao?: string;
  }) => {
    const nextQ = opts?.q ?? q;
    const nextAno = opts?.ano ?? ano;
    const nextTipo = opts?.tipoId ?? tipoId;
    const nextVer = opts?.vereadorId ?? vereadorId;
    const nextClass = opts?.classificacao ?? classificacao;

    setLoading(true);
    setError(null);
    try {
      const res = await api.materias({
        page: opts?.page ?? 1,
        per_page: 20,
        q: nextQ.trim() || undefined,
        ano: nextAno ? Number(nextAno) : undefined,
        tipo_id: nextTipo ? Number(nextTipo) : undefined,
        vereador_id: nextVer || undefined,
        eh_proposicao_parlamentar: resolverFlagParlamentar(nextClass),
      });
      setDados(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao consultar proposições e matérias.",
      );
    } finally {
      setLoading(false);
    }
  };

  const limparFiltros = () => {
    setQ("");
    setAno("");
    setTipoId("");
    setVereadorId("");
    setClassificacao("true");
    void buscar({ page: 1, q: "", ano: "", tipoId: "", vereadorId: "", classificacao: "true" });
  };

  const exportarCsvPagina = () => {
    baixarCsvNoNavegador(
      `cerrado-aberto-materias-pag-${dados.page}.csv`,
      [
        "Matéria",
        "Tipo",
        "Ano",
        "Data de Publicação",
        "Situação Atual",
        "Proposição Parlamentar",
        "Autores",
        "Ementa",
        "Fonte URL",
      ],
      dados.items.map((m) => [
        m.nome_materia,
        m.tipo_descricao_origem,
        m.ano,
        m.data_publicacao ? formatarDataBR(m.data_publicacao) : null,
        m.situacao_atual,
        m.eh_proposicao_parlamentar ? "Sim" : "Não (ato administrativo/externo)",
        m.autores
          .map((a) => a.nome_exibicao || a.nome_politico || a.autor_institucional || a.tipo_autor)
          .join("; "),
        m.ementa,
        m.proveniencia.fonte_url,
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
        aria-label="Filtrar proposições e matérias legislativas"
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 space-y-4"
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5 items-end">
          <div className="lg:col-span-2">
            <label htmlFor="mat-busca" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Buscar na ementa ou número
            </label>
            <input
              id="mat-busca"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ex.: asfalto, escola, 026/2026..."
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            />
          </div>

          <div>
            <label htmlFor="mat-tipo" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Tipo de matéria
            </label>
            <select
              id="mat-tipo"
              value={tipoId}
              onChange={(e) => {
                const val = e.target.value;
                setTipoId(val);
                void buscar({ tipoId: val, page: 1 });
              }}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            >
              <option value="">Todos os tipos</option>
              {TIPOS_MATERIA_OPCOES.map((t) => (
                <option key={t.id} value={String(t.id)}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="mat-vereador" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Vereador(a) autor(a)
            </label>
            <select
              id="mat-vereador"
              value={vereadorId}
              onChange={(e) => {
                const val = e.target.value;
                setVereadorId(val);
                void buscar({ vereadorId: val, page: 1 });
              }}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
            >
              <option value="">Todos os autores</option>
              {vereadores.map((v) => (
                <option key={v.vereador_id} value={v.vereador_id}>
                  {v.nome_exibicao}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="mat-ano" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Ano
            </label>
            <select
              id="mat-ano"
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
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <label htmlFor="mat-class" className="sr-only">
                Classificação ADR-005
              </label>
              <select
                id="mat-class"
                value={classificacao}
                onChange={(e) => {
                  const val = e.target.value;
                  setClassificacao(val);
                  void buscar({ classificacao: val, page: 1 });
                }}
                className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs font-medium text-[var(--ink)]"
              >
                <option value="true">Somente proposições parlamentares (ADR-005)</option>
                <option value="all">Todas as matérias (inclui atas e atos)</option>
                <option value="false">Somente atas e atos administrativos</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-4 py-2 text-sm font-semibold hover:opacity-90 disabled:opacity-60"
            >
              <Search className="w-4 h-4" aria-hidden="true" />
              {loading ? "Buscando..." : "Filtrar"}
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
          <strong>{formatarInteiro(dados.total)}</strong> matéria(s) encontrada(s)
        </span>
        <span className="tabular-nums">
          Página {dados.page} de {dados.total_pages}
        </span>
      </div>

      {dados.items.length === 0 ? (
        <EstadoAusente
          titulo="Nenhuma matéria encontrada para estes filtros"
          descricao="Tente remover o filtro de tipo, mudar o vereador selecionado ou incluir atas e atos administrativos."
        />
      ) : (
        <ul className="space-y-3">
          {dados.items.map((m) => (
            <li
              key={m.proposicao_id}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-[var(--primary)]/10 text-[var(--primary)] px-2.5 py-0.5 font-semibold">
                    {m.tipo_descricao_origem}
                  </span>
                  {!m.eh_proposicao_parlamentar && (
                    <span className="rounded-full bg-[var(--status-null-bg)] text-[var(--status-null-ink)] px-2.5 py-0.5 font-medium">
                      Ato administrativo / externo
                    </span>
                  )}
                  {m.situacao_atual && (
                    <span className="rounded-full bg-[var(--surface-alt)] px-2.5 py-0.5 text-[var(--ink)]">
                      {m.situacao_atual}
                    </span>
                  )}
                </div>
                <span className="text-[var(--ink-muted)] tabular-nums">
                  {m.data_publicacao ? formatarDataBR(m.data_publicacao) : `Ano ${m.ano}`}
                </span>
              </div>

              <h2 className="font-display text-lg font-bold text-[var(--ink)]">
                <Link
                  href={`/materias/${m.proposicao_id}`}
                  className="hover:text-[var(--primary)] hover:underline"
                >
                  {m.nome_materia}
                </Link>
              </h2>

              <p className="text-sm text-[var(--ink)] leading-relaxed">{m.ementa}</p>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border)]/60 text-xs text-[var(--ink-muted)]">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span>Autoria:</span>
                  {m.autores.length === 0 ? (
                    <span className="italic">Não informada</span>
                  ) : (
                    m.autores.map((a, idx) => (
                      <span key={a.autoria_id}>
                        {a.vereador_id ? (
                          <Link
                            href={`/vereadores/${a.vereador_id}`}
                            className="font-semibold text-[var(--primary)] hover:underline"
                          >
                            {a.nome_exibicao || a.nome_politico}
                          </Link>
                        ) : (
                          <span>{a.autor_institucional || a.tipo_autor}</span>
                        )}
                        {idx < m.autores.length - 1 ? ", " : ""}
                      </span>
                    ))
                  )}
                </div>

                <a
                  href={m.proveniencia.fonte_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 underline hover:text-[var(--primary)]"
                >
                  Documento no Nexlegis
                  <ExternalLink className="w-3 h-3" aria-hidden="true" />
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}

      {dados.total_pages > 1 && (
        <nav aria-label="Paginação de matérias" className="flex items-center justify-between pt-2">
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
