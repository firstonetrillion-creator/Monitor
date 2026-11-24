"use client";

import { useState, useTransition } from "react";
import * as Plot from "@observablehq/plot";
import { ExternalLink, Scale } from "lucide-react";
import type { ComparativoSiconfiOut } from "@/lib/types";
import { api } from "@/lib/api";
import { formatarBRL, formatarDataBR, formatarInteiro, parseDecimal } from "@/lib/format";
import { PlotChart } from "@/components/PlotChart";

interface ComparativoClientProps {
  inicial: ComparativoSiconfiOut;
}

export function ComparativoClient({ inicial }: ComparativoClientProps) {
  const [dados, setDados] = useState<ComparativoSiconfiOut>(inicial);
  const [isPending, startTransition] = useTransition();

  function trocarAno(novoAno: number) {
    startTransition(async () => {
      const res = await api.comparativo({ ano: novoAno });
      setDados(res);
    });
  }

  const inhumas = dados.municipios.find((m) => m.eh_municipio_foco) || dados.municipios[0];
  const linhasGrafico = dados.municipios.map((m) => ({
    municipio: m.eh_municipio_foco ? `${m.ente_nome} (foco)` : m.ente_nome,
    perCapitaAno: parseDecimal(m.despesa_paga_per_capita_ano) ?? 0,
    ehFoco: m.eh_municipio_foco,
  }));

  return (
    <div className="space-y-6">
      {/* Seletor de exercício fiscal */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
            Exercício consolidado no Tesouro Nacional ({dados.anexo_siconfi})
          </p>
          <p className="text-sm text-[var(--ink)] font-medium mt-0.5">
            Função analisada: <strong>{dados.funcao_descricao}</strong> · {dados.municipios.length}{" "}
            municípios goianos de porte semelhante
          </p>
        </div>

        <div className="flex items-center gap-2" role="group" aria-label="Selecionar ano do comparativo">
          {dados.anos_disponiveis.map((a) => {
            const ativo = a === dados.ano_selecionado;
            return (
              <button
                key={a}
                type="button"
                aria-pressed={ativo}
                disabled={isPending}
                onClick={() => trocarAno(a)}
                className={`rounded-xl px-4 py-2 text-sm font-semibold tabular-nums transition-colors ${
                  ativo
                    ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                    : "border border-[var(--border)] bg-[var(--bg)] text-[var(--ink)] hover:bg-[var(--surface-alt)]"
                }`}
              >
                {a}
              </button>
            );
          })}
        </div>
      </div>

      {/* Cartões âncora neutros */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border-2 border-[var(--primary)]/40 bg-[var(--surface)] p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
            Inhumas ({dados.ano_selecionado}) — per capita/ano
          </p>
          <p className="mt-1 font-display text-3xl font-bold text-[var(--ink)] tabular-nums">
            {formatarBRL(inhumas?.despesa_paga_per_capita_ano)}
          </p>
          <p className="mt-1 text-xs text-[var(--ink-muted)] tabular-nums">
            {formatarBRL(inhumas?.despesa_paga_per_capita_mes)} / habitante / mês · Total pago:{" "}
            {formatarBRL(inhumas?.despesa_paga)}
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
            Mediana do grupo ({dados.municipios.length} cidades GO)
          </p>
          <p className="mt-1 font-display text-3xl font-bold text-[var(--ink)] tabular-nums">
            {formatarBRL(dados.mediana_per_capita_ano_grupo)}
          </p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            valor central entre os municípios comparados
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]">
            Média do grupo ({dados.ano_selecionado})
          </p>
          <p className="mt-1 font-display text-3xl font-bold text-[var(--ink)] tabular-nums">
            {formatarBRL(dados.media_per_capita_ano_grupo)}
          </p>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            média aritmética da Função 01 - Legislativa
          </p>
        </div>
      </div>

      {/* Gráfico Observable Plot acessível (com tabela alternativa + CSV) */}
      <PlotChart
        titulo={`Despesa Legislativa paga por habitante/ano (${dados.ano_selecionado}) — SICONFI/STN`}
        descricao="Municípios goianos de porte semelhante ordenados por população (ordem neutra). Destaque em verde-cerrado para Inhumas."
        nomeArquivoCsv={`cerrado-aberto-comparativo-siconfi-${dados.ano_selecionado}`}
        legenda={["Verde-cerrado: Inhumas (município foco)", "Areia/oliva: municípios goianos pares"]}
        colunasTabela={[
          "Município (UF)",
          "Código IBGE",
          "População SICONFI",
          `Despesa Paga ${dados.ano_selecionado} (R$)`,
          "Por Habitante/Ano (R$)",
          "Por Habitante/Mês (R$)",
        ]}
        linhasTabela={dados.municipios.map((m) => ({
          celulas: [
            `${m.ente_nome}/${m.uf}`,
            m.codigo_ibge,
            formatarInteiro(m.populacao_siconfi),
            formatarBRL(m.despesa_paga),
            formatarBRL(m.despesa_paga_per_capita_ano),
            formatarBRL(m.despesa_paga_per_capita_mes),
          ],
        }))}
        renderPlot={(width) =>
          Plot.plot({
            width: Math.max(320, width),
            height: Math.max(260, linhasGrafico.length * 42 + 40),
            marginLeft: 145,
            marginRight: 78,
            x: { label: "R$ por habitante / ano", grid: true },
            y: { label: null, domain: linhasGrafico.map((d) => d.municipio) },
            marks: [
              Plot.barX(linhasGrafico, {
                x: "perCapitaAno",
                y: "municipio",
                fill: (d) => (d.ehFoco ? "#1F4E3D" : "#9CA89E"),
                rx: 4,
              }),
              Plot.text(linhasGrafico, {
                x: "perCapitaAno",
                y: "municipio",
                text: (d) => `R$ ${d.perCapitaAno.toFixed(2).replace(".", ",")}`,
                dx: 6,
                textAnchor: "start",
                fontSize: 12,
                fontWeight: 600,
                fill: "currentColor",
              }),
            ],
          })
        }
      />

      {/* Tabela completa com variação interanual e links individuais SICONFI */}
      <div
        role="region"
        aria-label={`Tabela comparativa oficial SICONFI ${dados.ano_selecionado}`}
        tabIndex={0}
        className="overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)]"
      >
        <table className="w-full text-sm text-left border-collapse">
          <thead className="bg-[var(--surface-alt)] text-xs uppercase text-[var(--ink-muted)]">
            <tr>
              <th scope="col" className="px-4 py-3">Município</th>
              <th scope="col" className="px-4 py-3 text-right">População (SICONFI)</th>
              <th scope="col" className="px-4 py-3 text-right">Despesa Paga ({dados.ano_selecionado})</th>
              <th scope="col" className="px-4 py-3 text-right">Por Hab. / Ano</th>
              <th scope="col" className="px-4 py-3 text-right">Por Hab. / Mês</th>
              <th scope="col" className="px-4 py-3 text-right">Variação vs. {dados.ano_selecionado - 1}</th>
              <th scope="col" className="px-4 py-3">Fonte</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {dados.municipios.map((m) => (
              <tr
                key={m.comparativo_id}
                className={
                  m.eh_municipio_foco ? "bg-[var(--primary)]/8 font-semibold" : "hover:bg-[var(--surface-alt)]/40"
                }
              >
                <td className="px-4 py-3">
                  {m.ente_nome}/{m.uf}
                  {m.eh_municipio_foco && (
                    <span className="ml-2 inline-flex rounded-full bg-[var(--primary)] text-[var(--primary-ink)] px-2 py-0.5 text-[11px] font-semibold">
                      Foco
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatarInteiro(m.populacao_siconfi)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">{formatarBRL(m.despesa_paga)}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatarBRL(m.despesa_paga_per_capita_ano)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatarBRL(m.despesa_paga_per_capita_mes)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {m.variacao_pct_ano_anterior !== null
                    ? `${Number(m.variacao_pct_ano_anterior) >= 0 ? "+" : ""}${Number(m.variacao_pct_ano_anterior).toFixed(1).replace(".", ",")}%`
                    : "Não apurado"}
                </td>
                <td className="px-4 py-3 text-xs">
                  <a
                    href={m.fonte_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 underline text-[var(--primary)]"
                  >
                    JSON STN
                    <ExternalLink className="w-3 h-3" aria-hidden="true" />
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Nota metodológica neutra */}
      <aside className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-5 space-y-2 text-xs text-[var(--ink-muted)] leading-relaxed">
        <p className="inline-flex items-center gap-1.5 font-semibold text-[var(--ink)] text-sm">
          <Scale className="w-4 h-4 text-[var(--primary)]" aria-hidden="true" />
          Nota metodológica e leitura neutra
        </p>
        <p>{dados.nota_metodologica}</p>
        <p>
          <strong>Fonte:</strong> {dados.fonte_oficial} · Coleta registrada em{" "}
          {formatarDataBR(inhumas?.coletado_em)}.
        </p>
      </aside>
    </div>
  );
}
