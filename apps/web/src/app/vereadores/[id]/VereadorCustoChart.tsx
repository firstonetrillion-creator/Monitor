"use client";

import * as Plot from "@observablehq/plot";
import type { CustoMandatoMensalOut } from "@/lib/types";
import { formatarBRL, nomeMesCurto, parseDecimal, rotuloCompetenciaStatus } from "@/lib/format";
import { PlotChart } from "@/components/PlotChart";

interface VereadorCustoChartProps {
  series: CustoMandatoMensalOut[];
  nomeVereador: string;
}

export function VereadorCustoChart({ series, nomeVereador }: VereadorCustoChartProps) {
  const registrosLongo = series.flatMap((m) => {
    const mesLabel = `${nomeMesCurto(m.mes)}/${m.ano}`;
    const itens: { mes: string; ordem: number; componente: string; valor: number }[] = [];
    const sub = parseDecimal(m.subsidio_bruto_vereador);
    const gab = parseDecimal(m.folha_bruta_gabinete);
    const dia = parseDecimal(m.diarias_atribuiveis_pagas);
    if (sub !== null) {
      itens.push({ mes: mesLabel, ordem: m.mes, componente: "Subsídio bruto", valor: sub });
    }
    if (gab !== null) {
      itens.push({ mes: mesLabel, ordem: m.mes, componente: "Folha do gabinete", valor: gab });
    }
    if (dia !== null && dia > 0) {
      itens.push({ mes: mesLabel, ordem: m.mes, componente: "Diárias atribuíveis", valor: dia });
    }
    return itens;
  });

  const colunasTabela = [
    "Competência",
    "Situação",
    "Subsídio bruto",
    "Folha do gabinete",
    "Diárias pagas",
    "Total apurado",
  ];

  const linhasTabela = series.map((m) => ({
    celulas: [
      `${nomeMesCurto(m.mes)}/${m.ano}`,
      rotuloCompetenciaStatus(m.competencia_status).texto,
      formatarBRL(m.subsidio_bruto_vereador, "Sem publicação"),
      formatarBRL(m.folha_bruta_gabinete, "Não publicado / NULL"),
      formatarBRL(m.diarias_atribuiveis_pagas, "Sem publicação"),
      formatarBRL(m.custo_estrutura_mandato_total, "Não apurado (NULL)"),
    ],
  }));

  return (
    <PlotChart
      titulo={`Evolução mensal do Custo da Estrutura do Mandato (2026) — ${nomeVereador}`}
      descricao="Barras empilhadas com os componentes disponíveis em cada mês. Competências em aberto ou com lacuna de lotação não recebem valor zero."
      legenda={[
        "Subsídio bruto do vereador",
        "Folha bruta do gabinete",
        "Diárias atribuíveis pagas",
      ]}
      colunasTabela={colunasTabela}
      linhasTabela={linhasTabela}
      renderPlot={(width) =>
        Plot.plot({
          width,
          height: 300,
          marginLeft: 70,
          marginBottom: 42,
          color: {
            domain: ["Subsídio bruto", "Folha do gabinete", "Diárias atribuíveis"],
            range: ["#1f4e3d", "#d99b16", "#b44b2a"],
            legend: true,
          },
          x: {
            label: "Competência (2026)",
            domain: series.map((s) => `${nomeMesCurto(s.mes)}/${s.ano}`),
          },
          y: {
            label: "Valor bruto (R$)",
            grid: true,
          },
          marks: [
            Plot.barY(registrosLongo, {
              x: "mes",
              y: "valor",
              fill: "componente",
              tip: true,
            }),
            Plot.ruleY([0]),
          ],
        })
      }
    />
  );
}
