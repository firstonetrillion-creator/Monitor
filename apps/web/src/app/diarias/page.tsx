import { safeFetchApi } from "@/lib/api";
import type {
  DeclaracaoTransparenciaOut,
  DiariaOut,
  PaginacaoOut,
  VereadorResumoOut,
} from "@/lib/types";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { GlossarioTooltip } from "@/components/GlossarioTooltip";
import { DiariasClient } from "./DiariasClient";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Diárias",
  description:
    "Registros contábeis de diárias (Elemento 14) na Câmara Municipal de Inhumas em 2026 e explicação sobre a diferença com o módulo cntdiarias.",
};

export default async function DiariasPage() {
  const [diariasRes, declRes, vereadoresRes] = await Promise.all([
    safeFetchApi<PaginacaoOut<DiariaOut>>("/transparencia/diarias", {
      ano: 2026,
      per_page: 50,
    }),
    safeFetchApi<DeclaracaoTransparenciaOut[]>("/transparencia/declaracoes"),
    safeFetchApi<PaginacaoOut<VereadorResumoOut>>("/vereadores", {
      apenas_legislatura_atual: true,
      per_page: 50,
    }),
  ]);

  const declDiarias = (declRes.data || []).find(
    (d) => d.tipo_declaracao === "NAO_CONCESSAO_DIARIAS",
  );
  const vereadoresOrdenados = [...(vereadoresRes.data?.items || [])].sort((a, b) =>
    a.nome_exibicao.localeCompare(b.nome_exibicao, "pt-BR"),
  );

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-bold text-[var(--ink)]">Diárias (2026)</h1>
        <p className="mt-2 text-base text-[var(--ink-muted)]">
          Cruzamento entre o módulo específico de diárias (<code>cntdiarias</code>) e os empenhos
          contábeis do{" "}
          <GlossarioTooltip termo="elemento14" label="Elemento 14 – Diárias – Civil" /> no Portal
          da Transparência.
        </p>
      </header>

      {/* Explicação obrigatória da diferença entre cntdiarias e Elemento 14 */}
      <EstadoAusente
        tom="aviso"
        titulo="Diferença entre o módulo de diárias (cntdiarias) e os registros contábeis do Elemento 14"
        descricao={
          declDiarias?.observacao_cruzamento ||
          "Embora o módulo específico cntdiarias retorne 0 registros em 2026 e haja declaração de não concessão para 01/03/2026–14/04/2026 e 01/05/2026–22/10/2026, os empenhos contábeis do Elemento 14 registram 14 pagamentos de diárias em 2026 (incluindo lançamentos em janeiro e fevereiro, fora da janela declarada, e pagamentos a servidores em 2026). Apresentamos os fatos com referência documental, sem fazer juízo de valor."
        }
      />

      {diariasRes.error || !diariasRes.data ? (
        <EstadoErroAPI
          mensagem={diariasRes.error || "Não foi possível carregar os registros de diárias."}
        />
      ) : (
        <DiariasClient
          initialItems={diariasRes.data.items}
          vereadores={vereadoresOrdenados}
        />
      )}
    </div>
  );
}
