import Link from "next/link";
import { safeFetchApi } from "@/lib/api";
import type {
  DeclaracaoTransparenciaOut,
  DiariaOut,
  PaginacaoOut,
} from "@/lib/types";
import {
  formatarBRL,
  formatarDataBR,
  formatarDocumentoFavorecido,
  rotuloFonte,
} from "@/lib/format";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { GlossarioTooltip } from "@/components/GlossarioTooltip";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Diárias",
  description:
    "Registros contábeis de diárias (Elemento 14) na Câmara Municipal de Inhumas em 2026 e explicação sobre a diferença com o módulo cntdiarias.",
};

export default async function DiariasPage() {
  const [diariasRes, declRes] = await Promise.all([
    safeFetchApi<PaginacaoOut<DiariaOut>>("/transparencia/diarias", {
      ano: 2026,
      per_page: 50,
    }),
    safeFetchApi<DeclaracaoTransparenciaOut[]>("/transparencia/declaracoes"),
  ]);

  const diarias = diariasRes.data?.items || [];
  const declDiarias = (declRes.data || []).find(
    (d) => d.tipo_declaracao === "NAO_CONCESSAO_DIARIAS",
  );

  const totalPago = diarias.reduce((acc, d) => acc + Number(d.valor_pago || 0), 0);
  const totalVereadores = diarias
    .filter((d) => d.vereador_id_verificado !== null)
    .reduce((acc, d) => acc + Number(d.valor_pago || 0), 0);

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
        <>
          {/* Cards de resumo */}
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
              <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                Registros encontrados (Elemento 14)
              </p>
              <p className="mt-1.5 text-2xl font-bold tabular-nums">{diarias.length}</p>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
              <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                Valor total pago em diárias (2026)
              </p>
              <p className="mt-1.5 text-2xl font-bold tabular-nums text-[var(--accent)]">
                {formatarBRL(totalPago)}
              </p>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
              <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                Atribuídas diretamente a vereadores
              </p>
              <p className="mt-1.5 text-2xl font-bold tabular-nums text-[var(--primary)]">
                {formatarBRL(totalVereadores)}
              </p>
              <p className="mt-1 text-xs text-[var(--ink-muted)]">
                {diarias.filter((d) => d.vereador_id_verificado !== null).length} empenhos em
                jan–fev/2026
              </p>
            </div>
          </div>

          {/* Tabela de diárias */}
          <div
            className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Detalhamento dos 14 empenhos de diárias em 2026"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
              <h2 className="text-xl font-bold text-[var(--ink)]">
                Detalhamento dos 14 empenhos de diárias em 2026
              </h2>
              <Link
                href="/como-calculamos"
                className="text-xs underline text-[var(--ink-muted)] hover:text-[var(--primary)]"
              >
                Como calculamos
              </Link>
            </div>
            <table className="w-full text-left text-sm border-collapse min-w-[820px]">
              <thead className="sticky top-0 bg-[var(--surface)] z-10">
                <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                  <th className="py-2 pr-3">Data</th>
                  <th className="py-2 pr-3">Empenho</th>
                  <th className="py-2 pr-3">Beneficiário</th>
                  <th className="py-2 pr-3">Vínculo / Cargo</th>
                  <th className="py-2 pr-3 text-right">Valor pago</th>
                  <th className="py-2">Finalidade publicada no empenho</th>
                </tr>
              </thead>
              <tbody>
                {diarias.map((d) => (
                  <tr key={d.diaria_id} className="border-b border-[var(--border)]/60 align-top">
                    <td className="py-3 pr-3 tabular-nums whitespace-nowrap">
                      {formatarDataBR(d.data_concessao)}
                    </td>
                    <td className="py-3 pr-3 font-mono text-xs whitespace-nowrap">
                      #{d.numero_empenho}
                    </td>
                    <td className="py-3 pr-3">
                      {d.vereador_id_verificado ? (
                        <Link
                          href={`/vereadores/${d.vereador_id_verificado}`}
                          className="font-semibold text-[var(--primary)] hover:underline"
                        >
                          {d.beneficiario_nome}
                        </Link>
                      ) : (
                        <span className="font-semibold text-[var(--ink)]">
                          {d.beneficiario_nome}
                        </span>
                      )}
                      <p className="text-[11px] text-[var(--ink-muted)]">
                        {formatarDocumentoFavorecido(d.cpf_mascarado, "PESSOA_FISICA")}
                      </p>
                    </td>
                    <td className="py-3 pr-3 text-xs">
                      <span className="inline-block rounded-full bg-[var(--surface-alt)] px-2 py-0.5 font-medium text-[var(--ink)]">
                        {d.tipo_beneficiario === "VEREADOR" ? "Vereador(a)" : "Servidor(a)"}
                      </span>
                      {d.cargo_beneficiario && (
                        <p className="mt-1 text-[var(--ink-muted)]">{d.cargo_beneficiario}</p>
                      )}
                    </td>
                    <td className="py-3 pr-3 text-right font-bold tabular-nums whitespace-nowrap">
                      {formatarBRL(d.valor_pago)}
                    </td>
                    <td className="py-3 text-xs text-[var(--ink-muted)] leading-relaxed max-w-md">
                      {d.destino_ou_finalidade}
                      <p className="mt-1 text-[11px] opacity-80">
                        Origem: {rotuloFonte(d.proveniencia.fonte_id)} · {d.origem_registro}
                      </p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {diarias[0] && <ProvenienciaBox proveniencia={diarias[0].proveniencia} />}
        </>
      )}
    </div>
  );
}
