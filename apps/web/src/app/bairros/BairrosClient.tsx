"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { Download, ExternalLink, MapPin, Table2 } from "lucide-react";
import type { BairroDetalheOut, BairrosPainelOut, VereadorResumoOut } from "@/lib/types";
import { api } from "@/lib/api";
import { baixarCsvNoNavegador } from "@/lib/csv";
import { formatarDataBR, formatarInteiro } from "@/lib/format";
import { MapaBairrosSvg } from "./MapaBairrosSvg";

interface BairrosClientProps {
  painelInicial: BairrosPainelOut;
  detalheInicial: BairroDetalheOut | null;
  vereadores: VereadorResumoOut[];
}

export function BairrosClient({ painelInicial, detalheInicial, vereadores }: BairrosClientProps) {
  const [painel, setPainel] = useState<BairrosPainelOut>(painelInicial);
  const [detalhe, setDetalhe] = useState<BairroDetalheOut | null>(detalheInicial);
  const [ano, setAno] = useState<string>("");
  const [tema, setTema] = useState<string>("");
  const [vereadorId, setVereadorId] = useState<string>("");
  const [buscaBairro, setBuscaBairro] = useState("");
  const [mostrarTabela, setMostrarTabela] = useState(false);
  const [isPending, startTransition] = useTransition();

  const vereadorSelecionado = vereadores.find((v) => v.vereador_id === vereadorId) || null;

  const bairrosFiltrados = painel.bairros.filter((b) =>
    !buscaBairro.trim()
      ? true
      : b.nome_oficial.toLowerCase().includes(buscaBairro.trim().toLowerCase()) ||
        b.regiao.toLowerCase().includes(buscaBairro.trim().toLowerCase()),
  );

  function aplicarFiltros(novoAno: string, novoTema: string, novoVereadorId: string) {
    setAno(novoAno);
    setTema(novoTema);
    setVereadorId(novoVereadorId);
    startTransition(async () => {
      const novoPainel = await api.bairros({
        ano: novoAno ? Number(novoAno) : undefined,
        tema: novoTema || undefined,
        vereador_id: novoVereadorId || undefined,
      });
      setPainel(novoPainel);
      const slugAlvo =
        detalhe && novoPainel.bairros.some((b) => b.slug === detalhe.bairro.slug)
          ? detalhe.bairro.slug
          : novoPainel.bairros[0]?.slug || null;
      if (slugAlvo) {
        const novoDet = await api.bairro(slugAlvo, {
          ano: novoAno ? Number(novoAno) : undefined,
          tema: novoTema || undefined,
          per_page: novoVereadorId ? 50 : 20,
        });
        setDetalhe(novoDet);
      } else {
        setDetalhe(null);
      }
    });
  }

  function selecionarBairro(slug: string) {
    startTransition(async () => {
      const novoDet = await api.bairro(slug, {
        ano: ano ? Number(ano) : undefined,
        tema: tema || undefined,
        per_page: vereadorId ? 50 : 20,
      });
      setDetalhe(novoDet);
    });
  }

  function exportarCsvBairros() {
    baixarCsvNoNavegador(
      `cerrado-aberto-bairros-inhumas${ano ? `-${ano}` : ""}.csv`,
      ["Bairro", "Região", "Tipo", "Proposições Citando o Bairro", "Tema Mais Frequente", "Último Registro"],
      painel.bairros.map((b) => [
        b.nome_oficial,
        b.regiao,
        b.tipo_localidade,
        b.total_proposicoes,
        b.tema_mais_frequente,
        b.ultimo_registro ? formatarDataBR(b.ultimo_registro) : null,
      ]),
    );
  }

  return (
    <div className="space-y-6">
      {/* Indicadores transparentes de cobertura */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
            Proposições citando bairro
          </p>
          <p className="mt-1 font-display text-3xl font-bold text-[var(--primary)] tabular-nums">
            {formatarInteiro(painel.proposicoes_com_bairro)}
          </p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            de {formatarInteiro(painel.proposicoes_parlamentares_total)} proposições parlamentares
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
            Bairros e distritos mapeados
          </p>
          <p className="mt-1 font-display text-3xl font-bold text-[var(--ink)] tabular-nums">
            {formatarInteiro(painel.bairros.length)}
          </p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            com menção verificável na ementa oficial
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
            Sem localidade na ementa
          </p>
          <p className="mt-1 font-display text-3xl font-bold text-[var(--ink-muted)] tabular-nums">
            {formatarInteiro(painel.proposicoes_sem_bairro)}
          </p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            temas gerais do município (não atribuídas a bairros)
          </p>
        </div>
      </div>

      {/* Filtros + ações */}
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="bairro-ano" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Ano
            </label>
            <select
              id="bairro-ano"
              value={ano}
              onChange={(e) => aplicarFiltros(e.target.value, tema, vereadorId)}
              className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
            >
              <option value="">2025 e 2026</option>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
            </select>
          </div>
          <div>
            <label htmlFor="bairro-tema" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Tema principal
            </label>
            <select
              id="bairro-tema"
              value={tema}
              onChange={(e) => aplicarFiltros(ano, e.target.value, vereadorId)}
              className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
            >
              <option value="">Todos os temas</option>
              {painel.temas_disponiveis.map((t) => (
                <option key={t.tema} value={t.tema}>
                  {t.tema} ({t.quantidade})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="bairro-vereador" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Vereador(a) autor(a)
            </label>
            <select
              id="bairro-vereador"
              value={vereadorId}
              onChange={(e) => aplicarFiltros(ano, tema, e.target.value)}
              className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
            >
              <option value="">Todos os vereadores</option>
              {vereadores.map((v) => (
                <option key={v.vereador_id} value={v.vereador_id}>
                  {v.nome_exibicao}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="bairro-busca" className="block text-xs font-semibold text-[var(--ink-muted)] mb-1">
              Filtrar bairro
            </label>
            <input
              id="bairro-busca"
              type="search"
              value={buscaBairro}
              onChange={(e) => setBuscaBairro(e.target.value)}
              placeholder="Ex.: Alegrino, Vila América..."
              className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setMostrarTabela((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
          >
            <Table2 className="w-4 h-4" aria-hidden="true" />
            {mostrarTabela ? "Ocultar tabela completa" : "Ver todos em tabela"}
          </button>
          <button
            type="button"
            onClick={exportarCsvBairros}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            Baixar CSV
          </button>
        </div>
      </div>

      {/* Mapa vetorial local */}
      <MapaBairrosSvg
        bairros={bairrosFiltrados}
        slugSelecionado={detalhe?.bairro.slug || null}
        onSelecionar={selecionarBairro}
      />

      {/* Alternativa completa em tabela HTML acessível */}
      {mostrarTabela && (
        <div
          role="region"
          aria-label="Tabela completa de bairros de Inhumas por volume de proposições"
          tabIndex={0}
          className="overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)]"
        >
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-[var(--surface-alt)] text-xs uppercase text-[var(--ink-muted)]">
              <tr>
                <th scope="col" className="px-4 py-3">Bairro / Localidade</th>
                <th scope="col" className="px-4 py-3">Região</th>
                <th scope="col" className="px-4 py-3 text-right">Proposições</th>
                <th scope="col" className="px-4 py-3">Tema mais frequente</th>
                <th scope="col" className="px-4 py-3">Último registro</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {bairrosFiltrados.map((b) => (
                <tr key={b.slug} className="hover:bg-[var(--surface-alt)]/50">
                  <td className="px-4 py-2.5 font-medium">
                    <button
                      type="button"
                      onClick={() => selecionarBairro(b.slug)}
                      className="text-left text-[var(--primary)] hover:underline font-semibold"
                    >
                      {b.nome_oficial}
                    </button>
                  </td>
                  <td className="px-4 py-2.5 text-[var(--ink-muted)]">{b.regiao}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums font-semibold">
                    {formatarInteiro(b.total_proposicoes)}
                  </td>
                  <td className="px-4 py-2.5">{b.tema_mais_frequente || "—"}</td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--ink-muted)]">
                    {formatarDataBR(b.ultimo_registro)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Lista de bairros + Detalhe do bairro selecionado */}
      <div className="grid gap-6 lg:grid-cols-[320px_1fr] items-start">
        <aside className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 space-y-2 max-h-[620px] overflow-y-auto">
          <h2 className="font-display text-base font-bold text-[var(--ink)] px-1">
            Bairros com menções ({formatarInteiro(bairrosFiltrados.length)})
          </h2>
          <ul className="space-y-1">
            {bairrosFiltrados.map((b) => {
              const ativo = detalhe?.bairro.slug === b.slug;
              return (
                <li key={b.slug}>
                  <button
                    type="button"
                    onClick={() => selecionarBairro(b.slug)}
                    aria-pressed={ativo}
                    className={`w-full flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                      ativo
                        ? "bg-[var(--primary)] text-[var(--primary-ink)] font-semibold"
                        : "hover:bg-[var(--surface-alt)] text-[var(--ink)]"
                    }`}
                  >
                    <span className="truncate">{b.nome_oficial}</span>
                    <span
                      className={`shrink-0 text-xs tabular-nums rounded-full px-2 py-0.5 ${
                        ativo ? "bg-black/20" : "bg-[var(--surface-alt)] text-[var(--ink-muted)]"
                      }`}
                    >
                      {b.total_proposicoes}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <section
          aria-live="polite"
          className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-4"
        >
          {isPending ? (
            <p className="text-sm text-[var(--ink-muted)]">Carregando proposições do bairro...</p>
          ) : detalhe ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-4">
                <div>
                  <p className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
                    <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                    Região {detalhe.bairro.regiao}
                  </p>
                  <h2 className="font-display text-2xl font-bold text-[var(--ink)] mt-0.5">
                    {detalhe.bairro.nome_oficial}
                  </h2>
                  <p className="text-xs text-[var(--ink-muted)] mt-1">
                    {formatarInteiro(detalhe.total)} proposição(ões) parlamentar(es) com citação
                    explícita na ementa oficial.
                  </p>
                </div>

                {detalhe.temas.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {detalhe.temas.slice(0, 4).map((t) => (
                      <span
                        key={t.tema}
                        className="rounded-full bg-[var(--surface-alt)] px-2.5 py-1 text-xs font-medium text-[var(--ink)]"
                      >
                        {t.tema}: <strong className="tabular-nums">{t.quantidade}</strong>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {detalhe.vereadores_autores.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)] mb-2">
                    Vereadores que protocolaram pedidos para esta localidade
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {detalhe.vereadores_autores.map((v) => (
                      <Link
                        key={v.vereador_id}
                        href={`/vereadores/${v.slug}`}
                        className="rounded-full border border-[var(--border)] bg-[var(--bg)] px-3 py-1 text-xs font-medium text-[var(--ink)] hover:border-[var(--primary)] hover:text-[var(--primary)]"
                      >
                        {v.nome_exibicao} ({v.quantidade_proposicoes})
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {vereadorSelecionado && (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[var(--surface-alt)] px-3 py-2 text-xs text-[var(--ink-muted)]">
                  <span>
                    Exibindo proposições de{" "}
                    <strong className="text-[var(--ink)]">{vereadorSelecionado.nome_exibicao}</strong>{" "}
                    para {detalhe.bairro.nome_oficial}.
                  </span>
                  <Link
                    href={`/materias?vereador_id=${encodeURIComponent(vereadorSelecionado.vereador_id)}`}
                    className="font-semibold text-[var(--primary)] hover:underline"
                  >
                    Ver todas no catálogo →
                  </Link>
                </div>
              )}

              <ul className="space-y-3">
                {(vereadorSelecionado
                  ? detalhe.proposicoes.filter((p) =>
                      p.autores_nomes.includes(vereadorSelecionado.nome_exibicao),
                    )
                  : detalhe.proposicoes
                ).map((p) => (
                  <li
                    key={p.proposicao_id}
                    className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-4 space-y-1.5"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="font-semibold text-[var(--primary)]">{p.tema_principal}</span>
                      <span className="text-[var(--ink-muted)] tabular-nums">
                        {formatarDataBR(p.data_publicacao)}
                      </span>
                    </div>
                    <h3 className="font-display text-base font-bold text-[var(--ink)]">
                      <Link
                        href={`/materias/${p.proposicao_id}`}
                        className="hover:text-[var(--primary)] hover:underline"
                      >
                        {p.nome_materia}
                      </Link>
                    </h3>
                    {p.ementa && (
                      <p className="text-sm text-[var(--ink)] leading-relaxed">{p.ementa}</p>
                    )}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 text-xs text-[var(--ink-muted)]">
                      <span>
                        {p.autores_nomes.length > 0
                          ? `Autoria: ${p.autores_nomes.join(", ")}`
                          : "Autoria institucional / não informada"}
                      </span>
                      <a
                        href={p.fonte_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 underline hover:text-[var(--primary)]"
                      >
                        Fonte Nexlegis
                        <ExternalLink className="w-3 h-3" aria-hidden="true" />
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-[var(--ink-muted)]">
              Selecione um bairro para visualizar as proposições protocoladas.
            </p>
          )}
        </section>
      </div>

      {/* Nota metodológica transparente */}
      <aside className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--ink-muted)] leading-relaxed">
        <strong className="text-[var(--ink)]">Como este mapa funciona:</strong>{" "}
        {painel.nota_metodologica}
      </aside>
    </div>
  );
}
