"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import * as Plot from "@observablehq/plot";
import { Download } from "lucide-react";
import { baixarCsvNoNavegador } from "@/lib/csv";
import type { CustoMandatoMensalOut, DeclaracaoTransparenciaOut } from "@/lib/types";
import {
  formatarBRL,
  formatarDataBR,
  nomeMesLongo,
  parseDecimal,
  rotuloCompetenciaStatus,
} from "@/lib/format";
import { EstadoAusente } from "@/components/EstadoAusente";
import { GlossarioTooltip } from "@/components/GlossarioTooltip";
import { PlotChart } from "@/components/PlotChart";

interface CustoMandatoClientProps {
  registros: CustoMandatoMensalOut[];
  declaracaoCeap: DeclaracaoTransparenciaOut | null;
}

export function CustoMandatoClient({
  registros,
  declaracaoCeap,
}: CustoMandatoClientProps) {
  const [mesSelecionado, setMesSelecionado] = useState<number>(10);
  const [statusFiltro, setStatusFiltro] = useState<string>("");

  const filtrados = useMemo(() => {
    return registros
      .filter((r) => (mesSelecionado === 0 ? true : r.mes === mesSelecionado))
      .filter((r) => (statusFiltro ? r.competencia_status === statusFiltro : true))
      .sort((a, b) =>
        (a.nome_exibicao || a.vereador_id).localeCompare(
          b.nome_exibicao || b.vereador_id,
          "pt-BR",
        ),
      );
  }, [registros, mesSelecionado, statusFiltro]);

  // Para o gráfico, mostramos apenas quando um mês específico está selecionado e há competências fechadas
  const dadosGrafico = useMemo(() => {
    const base = mesSelecionado === 0 ? registros.filter((r) => r.mes === 10) : filtrados;
    return base.flatMap((r) => {
      const nome = r.nome_exibicao || r.vereador_id;
      const itens: { nome: string; componente: string; valor: number }[] = [];
      const sub = parseDecimal(r.subsidio_bruto_vereador);
      const gab = parseDecimal(r.folha_bruta_gabinete);
      const dia = parseDecimal(r.diarias_atribuiveis_pagas);
      if (sub !== null) itens.push({ nome, componente: "Subsídio bruto", valor: sub });
      if (gab !== null) itens.push({ nome, componente: "Folha do gabinete", valor: gab });
      if (dia !== null && dia > 0) itens.push({ nome, componente: "Diárias pagas", valor: dia });
      return itens;
    });
  }, [filtrados, registros, mesSelecionado]);

  const mesParaGrafico = mesSelecionado === 0 ? 10 : mesSelecionado;

  const linhasTabelaGrafico = useMemo(() => {
    const base = mesSelecionado === 0 ? registros.filter((r) => r.mes === 10) : filtrados;
    return [...base]
      .sort((a, b) =>
        (a.nome_exibicao || a.vereador_id).localeCompare(
          b.nome_exibicao || b.vereador_id,
          "pt-BR",
        ),
      )
      .map((r) => ({
        celulas: [
          r.nome_exibicao || r.vereador_id,
          formatarBRL(r.subsidio_bruto_vereador, "Sem publicação"),
          formatarBRL(r.folha_bruta_gabinete, "Não publicado (NULL)"),
          formatarBRL(r.diarias_atribuiveis_pagas, "Sem publicação"),
          formatarBRL(r.custo_estrutura_mandato_total, "Não apurado (NULL)"),
        ],
      }));
  }, [filtrados, registros, mesSelecionado]);

  return (
    <div className="space-y-6">
      {/* Nota oficial CEAP e lacunas */}
      <div className="grid gap-4 lg:grid-cols-2">
        <EstadoAusente
          titulo="Cota parlamentar (CEAP): inexistente"
          descricao={
            declaracaoCeap
              ? `${declaracaoCeap.observacao_cruzamento || declaracaoCeap.texto_integral} Cobertura oficial: ${formatarDataBR(declaracaoCeap.data_inicio_cobertura)} a ${formatarDataBR(declaracaoCeap.data_fim_cobertura)}.`
              : "A Câmara Municipal de Inhumas declarou oficialmente que não possui cota para exercício da atividade parlamentar (CEAP) nem verbas indenizatórias."
          }
        />
        <EstadoAusente
          tom="aviso"
          titulo="Limitações conhecidas e preservação de NULL"
          descricao="1) Competências 11/2026 e 12/2026 ainda não possuem folha publicada (status ABERTA_SEM_PUBLICACAO). 2) Na unidade PRESIDENCIA, a folha mistura assessoria institucional da Presidência sem lotação apartada de gabinete; por isso, a folha de gabinete e o total do Presidente permanecem NULL (LACUNA_PARCIAL_LOTACAO)."
        />
      </div>

      {/* Filtros */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label
            htmlFor="filtro-mes-custo"
            className="block text-xs font-semibold text-[var(--ink-muted)] mb-1"
          >
            Competência (2026)
          </label>
          <select
            id="filtro-mes-custo"
            value={mesSelecionado}
            onChange={(e) => setMesSelecionado(Number(e.target.value))}
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
          >
            <option value={0}>Todos os meses (180 registros)</option>
            {Array.from({ length: 12 }, (_, idx) => idx + 1).map((m) => (
              <option key={m} value={m}>
                {nomeMesLongo(m)} de 2026 {m >= 11 ? "(em aberto)" : ""}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="filtro-status-custo"
            className="block text-xs font-semibold text-[var(--ink-muted)] mb-1"
          >
            Situação da competência
          </label>
          <select
            id="filtro-status-custo"
            value={statusFiltro}
            onChange={(e) => setStatusFiltro(e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
          >
            <option value="">Todas</option>
            <option value="FECHADA">Competência fechada</option>
            <option value="LACUNA_PARCIAL_LOTACAO">Lacuna parcial de lotação</option>
            <option value="ABERTA_SEM_PUBLICACAO">Em aberto / sem folha</option>
          </select>
        </div>
      </div>

      {/* Gráfico Observable Plot */}
      {dadosGrafico.length > 0 && (
        <PlotChart
          titulo={`Composição do Custo da Estrutura do Mandato — ${nomeMesLongo(mesParaGrafico)}/2026`}
          descricao="Ordem alfabética dos vereadores. Barras mostram apenas os componentes publicados na competência."
          legenda={[
            "Subsídio bruto do vereador",
            "Folha bruta do gabinete",
            "Diárias atribuíveis pagas",
          ]}
          colunasTabela={[
            "Vereador",
            "Subsídio bruto",
            "Folha gabinete",
            "Diárias pagas",
            "Total",
          ]}
          linhasTabela={linhasTabelaGrafico}
          renderPlot={(width) =>
            Plot.plot({
              width,
              height: Math.max(380, linhasTabelaGrafico.length * 28 + 60),
              marginLeft: 170,
              marginBottom: 40,
              color: {
                domain: ["Subsídio bruto", "Folha do gabinete", "Diárias pagas"],
                range: ["#1f4e3d", "#d99b16", "#b44b2a"],
                legend: true,
              },
              x: { label: "Valor bruto (R$)", grid: true },
              y: { label: null },
              marks: [
                Plot.barX(dadosGrafico, {
                  y: "nome",
                  x: "valor",
                  fill: "componente",
                  tip: true,
                }),
                Plot.ruleX([0]),
              ],
            })
          }
        />
      )}

      {/* Tabela detalhada */}
      <div
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 overflow-x-auto"
        tabIndex={0}
        role="region"
        aria-label="Registros apurados do Custo da Estrutura do Mandato"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-xl font-bold text-[var(--ink)]">
              Registros apurados ({filtrados.length})
            </h2>
            <p className="text-xs text-[var(--ink-muted)]">
              Ordem alfabética por vereador ·{" "}
              <GlossarioTooltip termo="ceap" label="Sem CEAP em Inhumas" /> ·{" "}
              <Link href="/como-calculamos" className="underline hover:text-[var(--primary)]">
                Como calculamos
              </Link>
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              baixarCsvNoNavegador(
                "custo-estrutura-mandato-2026.csv",
                [
                  "Vereador",
                  "Mês/Ano",
                  "Situação",
                  "Subsídio Bruto (R$)",
                  "Folha Gabinete (R$)",
                  "Servidores",
                  "Diárias Pagas (R$)",
                  "Total (R$)",
                  "Fonte URL",
                ],
                filtrados.map((r) => [
                  r.nome_exibicao || r.vereador_id,
                  `${String(r.mes).padStart(2, "0")}/${r.ano}`,
                  r.competencia_status,
                  r.subsidio_bruto_vereador,
                  r.folha_bruta_gabinete,
                  r.quantidade_servidores_gabinete,
                  r.diarias_atribuiveis_pagas,
                  r.custo_estrutura_mandato_total,
                  r.proveniencia.fonte_url,
                ]),
              )
            }
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
          >
            <Download className="w-3.5 h-3.5" aria-hidden="true" />
            Baixar CSV dos registros
          </button>
        </div>

        <table className="w-full text-left text-sm border-collapse min-w-[780px]">
          <thead className="sticky top-0 bg-[var(--surface)] z-10">
            <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
              <th className="py-2 pr-3">Vereador</th>
              <th className="py-2 pr-3">Mês</th>
              <th className="py-2 pr-3">Situação</th>
              <th className="py-2 pr-3 text-right">Subsídio bruto</th>
              <th className="py-2 pr-3 text-right">Folha gabinete</th>
              <th className="py-2 pr-3 text-right">Servidores</th>
              <th className="py-2 pr-3 text-right">Diárias pagas</th>
              <th className="py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {filtrados.map((r) => {
              const st = rotuloCompetenciaStatus(r.competencia_status);
              return (
                <tr key={r.custo_mensal_id} className="border-b border-[var(--border)]/60">
                  <td className="py-2.5 pr-3 font-semibold">
                    <Link
                      href={`/vereadores/${r.vereador_id}`}
                      className="text-[var(--primary)] hover:underline"
                    >
                      {r.nome_exibicao || r.vereador_id}
                    </Link>
                  </td>
                  <td className="py-2.5 pr-3 tabular-nums">
                    {String(r.mes).padStart(2, "0")}/{r.ano}
                  </td>
                  <td className="py-2.5 pr-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        st.tom === "ok"
                          ? "bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)]"
                          : st.tom === "aviso"
                            ? "bg-[var(--status-warn-bg)] text-[var(--status-warn-ink)]"
                            : "bg-[var(--status-null-bg)] text-[var(--status-null-ink)]"
                      }`}
                    >
                      {st.texto}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">
                    {formatarBRL(r.subsidio_bruto_vereador, "Sem publicação")}
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">
                    {formatarBRL(r.folha_bruta_gabinete, "Não publicado (NULL)")}
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">
                    {r.quantidade_servidores_gabinete ?? "—"}
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">
                    {formatarBRL(r.diarias_atribuiveis_pagas, "Sem publicação")}
                  </td>
                  <td className="py-2.5 text-right font-bold tabular-nums">
                    {formatarBRL(r.custo_estrutura_mandato_total, "Não apurado")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
