"use client";

import * as Plot from "@observablehq/plot";
import type { DespesasResumoOut } from "@/lib/types";
import {
  formatarBRL,
  formatarDocumentoFavorecido,
  parseDecimal,
} from "@/lib/format";
import { PlotChart } from "@/components/PlotChart";

interface DespesasGraficosSectionProps {
  resumo: DespesasResumoOut;
}

export function DespesasGraficosSection({ resumo }: DespesasGraficosSectionProps) {
  const dadosElementoGrafico = resumo.por_elemento
    .map((e) => {
      const texto = e.elemento_despesa || "Não classificado";
      return {
        elemento: texto.length > 36 ? `${texto.slice(0, 35)}…` : texto,
        pago: parseDecimal(e.valor_pago) ?? 0,
        empenhadoLiquido: parseDecimal(e.valor_empenhado_liquido) ?? 0,
      };
    })
    .sort((a, b) => b.pago - a.pago);

  const favorecidosPj = resumo.favorecidos
    .filter((f) => f.tipo_pessoa_favorecido === "PESSOA_JURIDICA")
    .sort((a, b) => {
      const diff = (parseDecimal(b.valor_pago) ?? 0) - (parseDecimal(a.valor_pago) ?? 0);
      return diff !== 0 ? diff : a.favorecido_nome.localeCompare(b.favorecido_nome, "pt-BR");
    });

  const dadosFavorecidosPjGrafico = favorecidosPj.slice(0, 15).map((f) => {
    const nome = f.favorecido_nome;
    return {
      favorecido: nome.length > 36 ? `${nome.slice(0, 35)}…` : nome,
      pago: parseDecimal(f.valor_pago) ?? 0,
      empenhadoLiquido: parseDecimal(f.valor_empenhado_liquido) ?? 0,
    };
  });

  return (
    <div className="space-y-8">
      {dadosElementoGrafico.length > 0 && (
        <PlotChart
          titulo="Valores pagos por classificação (Elemento de Despesa)"
          descricao="Distribuição do total pago no recorte atual por elemento contábil."
          nomeArquivoCsv="despesas-2026-por-elemento.csv"
          colunasTabela={["Elemento de Despesa", "Empenhos", "Empenhado Líquido", "Pago"]}
          linhasTabela={resumo.por_elemento.map((e) => ({
            celulas: [
              e.elemento_despesa || "Não classificado",
              String(e.quantidade_empenhos),
              formatarBRL(e.valor_empenhado_liquido),
              formatarBRL(e.valor_pago),
            ],
          }))}
          renderPlot={(width) =>
            Plot.plot({
              width,
              height: Math.max(280, dadosElementoGrafico.length * 28 + 50),
              marginLeft: Math.min(280, Math.round(width * 0.42)),
              marginBottom: 40,
              x: { label: "Valor pago (R$)", grid: true },
              y: { label: null },
              marks: [
                Plot.barX(dadosElementoGrafico, {
                  y: "elemento",
                  x: "pago",
                  sort: { y: "-x" },
                  fill: "#1f4e3d",
                  tip: true,
                }),
                Plot.ruleX([0]),
              ],
            })
          }
        />
      )}

      {favorecidosPj.length > 0 && (
        <PlotChart
          titulo={`Despesas por favorecido Pessoa Jurídica (${favorecidosPj.length} fornecedores PJ no recorte)`}
          descricao="O gráfico exibe os 15 maiores recebedores PJ por valor pago no recorte atual. Use 'Ver dados em tabela' ou 'Baixar CSV' para consultar todos os fornecedores PJ com CNPJ."
          nomeArquivoCsv="despesas-2026-por-favorecido-pj.csv"
          colunasTabela={[
            "Favorecido (Pessoa Jurídica)",
            "CNPJ",
            "Empenhos",
            "Empenhado Líquido",
            "Liquidado",
            "Pago",
          ]}
          linhasTabela={favorecidosPj.map((f) => ({
            celulas: [
              f.favorecido_nome,
              formatarDocumentoFavorecido(f.documento_favorecido, f.tipo_pessoa_favorecido),
              String(f.quantidade_empenhos),
              formatarBRL(f.valor_empenhado_liquido),
              formatarBRL(f.valor_liquidado),
              formatarBRL(f.valor_pago),
            ],
          }))}
          renderPlot={(width) =>
            Plot.plot({
              width,
              height: Math.max(300, dadosFavorecidosPjGrafico.length * 28 + 50),
              marginLeft: Math.min(280, Math.round(width * 0.42)),
              marginBottom: 40,
              x: { label: "Valor pago (R$)", grid: true },
              y: { label: null },
              marks: [
                Plot.barX(dadosFavorecidosPjGrafico, {
                  y: "favorecido",
                  x: "pago",
                  sort: { y: "-x" },
                  fill: "#b44b2a",
                  tip: true,
                }),
                Plot.ruleX([0]),
              ],
            })
          }
        />
      )}
    </div>
  );
}
