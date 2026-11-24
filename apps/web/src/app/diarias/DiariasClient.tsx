"use client";

import { useState } from "react";
import Link from "next/link";
import { Download } from "lucide-react";
import { api } from "@/lib/api";
import { baixarCsvNoNavegador } from "@/lib/csv";
import type { DiariaOut, VereadorResumoOut } from "@/lib/types";
import {
  formatarBRL,
  formatarDataBR,
  formatarDocumentoFavorecido,
  rotuloFonte,
} from "@/lib/format";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";

interface DiariasClientProps {
  initialItems: DiariaOut[];
  vereadores: VereadorResumoOut[];
}

export function DiariasClient({ initialItems, vereadores }: DiariasClientProps) {
  const [diarias, setDiarias] = useState<DiariaOut[]>(initialItems);
  const [vereadorId, setVereadorId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filtrarPorVereador = async (novoVereadorId: string) => {
    setVereadorId(novoVereadorId);
    setLoading(true);
    setError(null);
    try {
      const res = await api.diarias({
        ano: 2026,
        per_page: 50,
        vereador_id: novoVereadorId || undefined,
      });
      setDiarias(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao filtrar diárias.");
    } finally {
      setLoading(false);
    }
  };

  const exportarCsv = () => {
    baixarCsvNoNavegador(
      "cerrado-aberto-diarias-2026.csv",
      [
        "Data",
        "Número Empenho",
        "Beneficiário",
        "CPF Mascarado",
        "Tipo",
        "Cargo",
        "Empenhado Líquido (R$)",
        "Liquidado (R$)",
        "Valor Pago (R$)",
        "Finalidade",
        "Origem",
        "Fonte URL",
      ],
      diarias.map((d) => [
        formatarDataBR(d.data_concessao),
        d.numero_empenho,
        d.beneficiario_nome,
        formatarDocumentoFavorecido(d.cpf_mascarado, "PESSOA_FISICA"),
        d.tipo_beneficiario,
        d.cargo_beneficiario,
        d.valor_empenhado_liquido,
        d.valor_liquidado,
        d.valor_pago,
        d.destino_ou_finalidade,
        d.origem_registro,
        d.proveniencia.fonte_url,
      ]),
    );
  };

  const totalPago = diarias.reduce((acc, d) => acc + Number(d.valor_pago || 0), 0);
  const totalVereadores = diarias
    .filter((d) => d.vereador_id_verificado !== null)
    .reduce((acc, d) => acc + Number(d.valor_pago || 0), 0);

  return (
    <div className="space-y-6">
      {/* Filtro por vereador e exportação CSV */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <label
            htmlFor="diarias-vereador"
            className="block text-xs font-semibold text-[var(--ink-muted)] mb-1"
          >
            Filtrar por vereador(a)
          </label>
          <select
            id="diarias-vereador"
            value={vereadorId}
            disabled={loading}
            onChange={(e) => void filtrarPorVereador(e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
          >
            <option value="">Todos (vereadores e servidores)</option>
            {vereadores.map((v) => (
              <option key={v.vereador_id} value={v.vereador_id}>
                {v.nome_exibicao}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={exportarCsv}
          disabled={diarias.length === 0}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3.5 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)] disabled:opacity-50"
        >
          <Download className="w-3.5 h-3.5" aria-hidden="true" />
          Baixar CSV
        </button>
      </div>

      {error && (
        <EstadoErroAPI
          mensagem={error}
          onTentarNovamente={() => void filtrarPorVereador(vereadorId)}
        />
      )}

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
      {diarias.length === 0 ? (
        <EstadoAusente
          titulo="Nenhuma diária atribuível encontrada neste filtro"
          descricao="Este parlamentar não possui empenhos de diárias atribuíveis no Elemento 14 em 2026."
        />
      ) : (
        <div
          className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label={`Detalhamento dos ${diarias.length} empenhos de diárias em 2026`}
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
            <h2 className="text-xl font-bold text-[var(--ink)]">
              Detalhamento dos {diarias.length} empenhos de diárias em 2026
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
      )}

      {diarias[0] && <ProvenienciaBox proveniencia={diarias[0].proveniencia} />}
    </div>
  );
}
