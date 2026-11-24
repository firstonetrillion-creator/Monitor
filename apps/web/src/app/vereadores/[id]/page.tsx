import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { safeFetchApi } from "@/lib/api";
import type { FolhaPagamentoOut, PaginacaoOut, VereadorDetalheOut } from "@/lib/types";
import {
  formatarBRL,
  formatarDataBR,
  formatarInteiro,
  nomeMesCurto,
  rotuloCompetenciaStatus,
} from "@/lib/format";
import { AvatarVereador } from "@/components/AvatarVereador";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { GlossarioTooltip } from "@/components/GlossarioTooltip";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";
import { VereadorCustoChart } from "./VereadorCustoChart";

export const dynamic = "force-dynamic";

export default async function VereadorDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const res = await safeFetchApi<VereadorDetalheOut>(
    `/vereadores/${encodeURIComponent(id)}`,
  );

  if (res.error || !res.data) {
    return (
      <div className="space-y-4">
        <Link
          href="/vereadores"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Voltar para vereadores
        </Link>
        <EstadoErroAPI
          titulo={
            res.status === 404
              ? "Vereador não encontrado"
              : "Erro ao carregar perfil do vereador"
          }
          mensagem={res.error || "Registro indisponível."}
        />
      </div>
    );
  }

  const v = res.data;
  const custo = v.custo_estrutura_mandato_2026;
  const mandatoAtual = v.mandatos[0];
  const folhaGabineteRes = custo
    ? await safeFetchApi<PaginacaoOut<FolhaPagamentoOut>>("/transparencia/folha", {
        ano: 2026,
        mes: 10,
        gabinete_vereador_id: v.vereador_id,
        per_page: 50,
      })
    : null;
  const servidoresGabinete = (folhaGabineteRes?.data?.items || []).filter(
    (item) => !item.eh_vereador,
  );

  return (
    <div className="space-y-8">
      <Link
        href="/vereadores"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        Voltar para a lista de vereadores
      </Link>

      {/* Cabeçalho do perfil */}
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8">
        <div className="flex flex-wrap items-start gap-5">
          <AvatarVereador nome={v.nome_exibicao} tamanho="lg" />
          <div className="flex-1 min-w-[240px]">
            <h1 className="text-3xl font-bold text-[var(--ink)]">{v.nome_exibicao}</h1>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">
              Nome civil: {v.nome_civil || "Não publicado na fonte"} · Nome parlamentar:{" "}
              {v.nome_politico}
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full bg-[var(--surface-alt)] px-3 py-1 font-semibold text-[var(--ink)]">
                Mandato: {mandatoAtual?.condicao || "Sem mandato ativo registrado"}
              </span>
              <span className="rounded-full bg-[var(--surface-alt)] px-3 py-1 font-semibold text-[var(--ink)]">
                Partido: {mandatoAtual?.partido_id || "Não informado na fonte"}
              </span>
              {mandatoAtual?.cargo_mesa && (
                <span className="rounded-full bg-[var(--status-ok-bg)] px-3 py-1 font-semibold text-[var(--status-ok-ink)]">
                  Mesa Diretora: {mandatoAtual.cargo_mesa}
                </span>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Presenças e ausências (2025 e 2026) */}
      <section aria-labelledby="sec-presenca" className="space-y-4">
        <h2 id="sec-presenca" className="text-2xl font-bold text-[var(--ink)]">
          Presenças e ausências em plenário
        </h2>
        <p className="text-sm text-[var(--ink-muted)]">
          Faltas justificadas e licenças são exibidas separadamente das ausências sem justificativa.
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          {[
            { ano: 2026, resumo: v.resumo_presenca_2026 },
            { ano: 2025, resumo: v.resumo_presenca_2025 },
          ].map(({ ano, resumo }) => (
            <article
              key={ano}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
            >
              <h3 className="text-lg font-bold text-[var(--ink)]">Exercício {ano}</h3>
              {!resumo || resumo.total_sessoes_registradas === 0 ? (
                <p className="mt-2 text-sm text-[var(--ink-muted)] italic">
                  Sem registros de presença neste ano.
                </p>
              ) : (
                <dl className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div>
                    <dt className="text-xs text-[var(--ink-muted)]">Presentes</dt>
                    <dd className="font-bold text-lg tabular-nums text-[var(--primary)]">
                      {formatarInteiro(resumo.presentes)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-[var(--ink-muted)]">Justificadas</dt>
                    <dd className="font-bold text-lg tabular-nums">
                      {formatarInteiro(resumo.faltas_justificadas)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-[var(--ink-muted)]">Ausentes</dt>
                    <dd className="font-bold text-lg tabular-nums text-[var(--accent)]">
                      {formatarInteiro(resumo.ausentes)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-[var(--ink-muted)]">Licenças</dt>
                    <dd className="font-bold text-lg tabular-nums">
                      {formatarInteiro(resumo.licencas)}
                    </dd>
                  </div>
                </dl>
              )}
            </article>
          ))}
        </div>
      </section>

      {/* Custo da Estrutura do Mandato (2026) */}
      <section aria-labelledby="sec-custo" className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="sec-custo" className="text-2xl font-bold text-[var(--ink)]">
            Custo da Estrutura do Mandato (2026)
          </h2>
          <Link
            href="/custo-mandato"
            className="text-sm font-semibold text-[var(--primary)] hover:underline"
          >
            Comparar estrutura dos mandatos
          </Link>
        </div>

        {!custo ? (
          <EstadoAusente
            titulo="Indicador não calculável para este registro"
            descricao="Este parlamentar não possui competências apuradas na folha/lotação do exercício de 2026 (ex.: suplente sem exercício ou legislatura anterior). Valores ausentes não são convertidos em zero."
          />
        ) : (
          <div className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  <GlossarioTooltip termo="subsidio" label="Subsídio bruto acumulado" />
                </p>
                <p className="mt-1.5 text-xl font-bold tabular-nums">
                  {formatarBRL(custo.subsidio_bruto_acumulado)}
                </p>
              </div>
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  Folha bruta do gabinete
                </p>
                <p className="mt-1.5 text-xl font-bold tabular-nums">
                  {formatarBRL(
                    custo.folha_bruta_gabinete_acumulada,
                    "Não apurado (lacuna de lotação)",
                  )}
                </p>
              </div>
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  Diárias atribuíveis pagas
                </p>
                <p className="mt-1.5 text-xl font-bold tabular-nums">
                  {formatarBRL(custo.diarias_atribuiveis_pagas_acumuladas)}
                </p>
              </div>
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  Total das competências fechadas ({custo.competencias_fechadas}/12)
                </p>
                <p
                  className={`mt-1.5 text-xl font-bold tabular-nums ${
                    custo.custo_estrutura_mandato_acumulado
                      ? "text-[var(--primary)]"
                      : "text-[var(--ink-muted)] italic text-base"
                  }`}
                >
                  {formatarBRL(
                    custo.custo_estrutura_mandato_acumulado,
                    "Não apurado no total (há lacuna parcial)",
                  )}
                </p>
              </div>
            </div>

            <EstadoAusente
              tom={custo.competencias_lacuna_parcial > 0 ? "aviso" : "neutro"}
              titulo={custo.nota_cota_parlamentar}
              descricao={`${custo.metodologia_resumo} ${custo.limitacoes_gerais}`}
            />

            <VereadorCustoChart series={custo.series_mensais} nomeVereador={v.nome_exibicao} />

            {/* Tabela mensal detalhada */}
            <div
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 overflow-x-auto"
              tabIndex={0}
              role="region"
              aria-label="Detalhamento mensal do Custo da Estrutura do Mandato em 2026"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
                <h3 className="text-lg font-bold text-[var(--ink)]">
                  Detalhamento mensal (2026)
                </h3>
                <Link
                  href="/como-calculamos"
                  className="text-xs underline text-[var(--ink-muted)] hover:text-[var(--primary)]"
                >
                  Como calculamos
                </Link>
              </div>
              <table className="w-full text-left text-sm border-collapse min-w-[680px]">
                <thead className="sticky top-0 bg-[var(--surface)] z-10">
                  <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                    <th className="py-2 pr-3">Mês</th>
                    <th className="py-2 pr-3">Situação</th>
                    <th className="py-2 pr-3 text-right">Subsídio</th>
                    <th className="py-2 pr-3 text-right">Folha gabinete</th>
                    <th className="py-2 pr-3 text-right">Servidores</th>
                    <th className="py-2 pr-3 text-right">Diárias pagas</th>
                    <th className="py-2 text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {custo.series_mensais.map((m) => {
                    const st = rotuloCompetenciaStatus(m.competencia_status);
                    return (
                      <tr key={m.custo_mensal_id} className="border-b border-[var(--border)]/60">
                        <td className="py-2.5 pr-3 font-semibold tabular-nums">
                          {nomeMesCurto(m.mes)}/{m.ano}
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
                          {formatarBRL(m.subsidio_bruto_vereador, "—")}
                        </td>
                        <td className="py-2.5 pr-3 text-right tabular-nums">
                          {formatarBRL(m.folha_bruta_gabinete, "NULL")}
                        </td>
                        <td className="py-2.5 pr-3 text-right tabular-nums">
                          {m.quantidade_servidores_gabinete ?? "—"}
                        </td>
                        <td className="py-2.5 pr-3 text-right tabular-nums">
                          {formatarBRL(m.diarias_atribuiveis_pagas, "—")}
                        </td>
                        <td className="py-2.5 text-right font-semibold tabular-nums">
                          {formatarBRL(m.custo_estrutura_mandato_total, "Não apurado")}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pessoal lotado no gabinete (Outubro/2026) */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <h3 className="text-lg font-bold text-[var(--ink)]">
                    Pessoal lotado no gabinete (Outubro/2026)
                  </h3>
                  <p className="text-xs text-[var(--ink-muted)]">
                    Registros nominais da folha de pagamento (sem CPF completo, LGPD).
                  </p>
                </div>
                <Link
                  href={`/folha?gabinete_vereador_id=${encodeURIComponent(v.vereador_id)}`}
                  className="text-xs font-semibold text-[var(--primary)] hover:underline"
                >
                  Ver histórico na Folha de Pagamento →
                </Link>
              </div>

              {servidoresGabinete.length > 0 ? (
                <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Servidores lotados no gabinete">
                  <table className="w-full text-left text-sm border-collapse min-w-[600px]">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                        <th className="py-2 pr-3">Servidor(a)</th>
                        <th className="py-2 pr-3">Cargo</th>
                        <th className="py-2 pr-3">Vínculo / Folha</th>
                        <th className="py-2 pr-3 text-right">Bruto</th>
                        <th className="py-2 text-right">Líquido</th>
                      </tr>
                    </thead>
                    <tbody>
                      {servidoresGabinete.map((s) => (
                        <tr key={s.folha_id} className="border-b border-[var(--border)]/60">
                          <td className="py-2.5 pr-3 font-medium text-[var(--ink)]">{s.nome_servidor}</td>
                          <td className="py-2.5 pr-3 text-xs text-[var(--ink-muted)]">{s.cargo}</td>
                          <td className="py-2.5 pr-3 text-xs text-[var(--ink-muted)]">
                            {s.tipo_admissao || "—"} · {s.tipo_folha}
                          </td>
                          <td className="py-2.5 pr-3 text-right tabular-nums">
                            {formatarBRL(s.remuneracao_bruta, "—")}
                          </td>
                          <td className="py-2.5 text-right font-semibold tabular-nums">
                            {formatarBRL(s.remuneracao_liquida, "—")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : custo.competencias_lacuna_parcial > 0 ? (
                <EstadoAusente
                  tom="aviso"
                  titulo="Lotação de gabinete indisponível separadamente (Presidência)"
                  descricao="Na folha publicada, os assessores vinculados à Presidência constam na unidade institucional PRESIDENCIA, sem separação de gabinete parlamentar."
                />
              ) : (
                <p className="text-sm text-[var(--ink-muted)] italic">
                  Nenhum assessor vinculado a este gabinete na competência de Outubro/2026.
                </p>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Proposições e Votos */}
      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <h2 className="text-xl font-bold text-[var(--ink)]">
                Proposições apresentadas
              </h2>
              <p className="mt-1 text-xs text-[var(--ink-muted)]">
                2026: <strong>{v.total_proposicoes_parlamentares_2026}</strong> · 2025:{" "}
                <strong>{v.total_proposicoes_parlamentares_2025}</strong>.{" "}
                {v.nota_metodologica_producao}
              </p>
            </div>
            <Link
              href={`/materias?vereador_id=${encodeURIComponent(v.vereador_id)}`}
              className="text-xs font-semibold text-[var(--primary)] hover:underline"
            >
              Ver todas as proposições →
            </Link>
          </div>

          {v.proposicoes_recentes.length === 0 ? (
            <p className="text-sm text-[var(--ink-muted)] italic">
              Nenhuma proposição parlamentar recente vinculada.
            </p>
          ) : (
            <ul className="divide-y divide-[var(--border)]">
              {v.proposicoes_recentes.slice(0, 10).map((p) => (
                <li key={p.proposicao_id} className="py-3">
                  <Link
                    href={`/materias/${p.proposicao_id}`}
                    className="font-semibold text-sm text-[var(--primary)] hover:underline"
                  >
                    {p.nome_materia}
                  </Link>
                  <p className="mt-1 text-xs text-[var(--ink-muted)] line-clamp-2">{p.ementa}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-4">
          <div>
            <h2 className="text-xl font-bold text-[var(--ink)]">
              Participação em votações nominais
            </h2>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">
              Registros recentes em sessões de 2026 e 2025.
            </p>
          </div>

          {v.votos_recentes_2026.length === 0 && v.votos_recentes_2025.length === 0 ? (
            <p className="text-sm text-[var(--ink-muted)] italic">
              Nenhum voto nominal recente registrado.
            </p>
          ) : (
            <ul className="divide-y divide-[var(--border)]">
              {[...v.votos_recentes_2026, ...v.votos_recentes_2025]
                .slice(0, 10)
                .map((voto) => (
                  <li key={voto.voto_id} className="py-3 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        href={`/sessoes/${voto.sessao_id}`}
                        className="text-xs font-semibold text-[var(--primary)] hover:underline"
                      >
                        {voto.nome_sessao} ({formatarDataBR(voto.data_sessao)})
                      </Link>
                      <p className="text-sm text-[var(--ink)] truncate">{voto.nome_materia}</p>
                    </div>
                    <span className="shrink-0 rounded-full bg-[var(--surface-alt)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]">
                      {voto.voto_descricao}
                    </span>
                  </li>
                ))}
            </ul>
          )}
        </div>
      </section>

      <ProvenienciaBox proveniencia={v.proveniencia} />
    </div>
  );
}
