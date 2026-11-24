"use client";

import { useEffect, useRef, useState } from "react";
import * as Plot from "@observablehq/plot";
import { Download, Table } from "lucide-react";
import { baixarCsvNoNavegador } from "@/lib/csv";

export interface TabelaAlternativaLinha {
  celulas: string[];
}

interface PlotChartProps {
  titulo: string;
  descricao: string;
  legenda?: string[];
  colunasTabela: string[];
  linhasTabela: TabelaAlternativaLinha[];
  nomeArquivoCsv?: string;
  renderPlot: (width: number) => SVGSVGElement | HTMLElement;
}

/**
 * Invólucro acessível para gráficos Observable Plot.
 * Sempre oferece alternativa em tabela HTML para leitores de tela, conferência exata e exportação CSV a um clique.
 */
export function PlotChart({
  titulo,
  descricao,
  legenda,
  colunasTabela,
  linhasTabela,
  nomeArquivoCsv,
  renderPlot,
}: PlotChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [mostrarTabela, setMostrarTabela] = useState(false);

  const handleExportarCsv = () => {
    const slug =
      nomeArquivoCsv ||
      titulo
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "");
    baixarCsvNoNavegador(
      `${slug || "dados-grafico"}.csv`,
      colunasTabela,
      linhasTabela.map((l) => l.celulas),
    );
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el || mostrarTabela) {
      return;
    }

    const draw = () => {
      const width = Math.max(320, el.clientWidth || 640);
      el.innerHTML = "";
      const node = renderPlot(width);
      // Observable Plot gera <g aria-label="tip"> sem role válido; ocultamos a árvore interna do SVG
      // porque o contêiner externo role="img" já fornece aria-label e existe tabela alternativa.
      node.querySelectorAll?.("g[aria-label]").forEach((g) => {
        g.removeAttribute("aria-label");
      });
      if (node instanceof Element) {
        node.setAttribute("aria-hidden", "true");
      }
      el.appendChild(node);
    };

    draw();
    const observer = new ResizeObserver(() => draw());
    observer.observe(el);
    return () => observer.disconnect();
  }, [renderPlot, mostrarTabela]);

  return (
    <section
      aria-label={titulo}
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-[var(--ink)]">{titulo}</h3>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">{descricao}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setMostrarTabela((prev) => !prev)}
            aria-expanded={mostrarTabela}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
          >
            <Table className="w-3.5 h-3.5" aria-hidden="true" />
            {mostrarTabela ? "Ver gráfico" : "Ver dados em tabela"}
          </button>

          <button
            type="button"
            onClick={handleExportarCsv}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
          >
            <Download className="w-3.5 h-3.5" aria-hidden="true" />
            Baixar CSV
          </button>
        </div>
      </div>

      {legenda && legenda.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--ink-muted)]">
          {legenda.map((item) => (
            <li key={item} className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[var(--primary)]" aria-hidden="true" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}

      {!mostrarTabela ? (
        <div
          ref={containerRef}
          tabIndex={0}
          className="plot-chart-canvas mt-4 w-full overflow-x-auto text-xs [&_svg]:max-w-full [&_svg]:h-auto"
          role="img"
          aria-label={`${titulo}. ${descricao}. Use o botão 'Ver dados em tabela' para ler os valores exatos.`}
        />
      ) : (
        <div
          className="mt-4 overflow-x-auto max-h-[480px]"
          tabIndex={0}
          role="region"
          aria-label={`Tabela de dados: ${titulo}`}
        >
          <table className="w-full text-left text-sm border-collapse">
            <thead className="sticky top-0 bg-[var(--surface)] z-10">
              <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                {colunasTabela.map((col) => (
                  <th key={col} scope="col" className="py-2 pr-4 font-semibold">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {linhasTabela.map((linha, idx) => (
                <tr key={idx} className="border-b border-[var(--border)]/60">
                  {linha.celulas.map((cel, cIdx) => (
                    <td
                      key={cIdx}
                      className={`py-2 pr-4 ${cIdx > 0 ? "tabular-nums" : "font-medium"}`}
                    >
                      {cel}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export { Plot };
