import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { safeFetchApi } from "@/lib/api";
import type { SessaoDetalheOut } from "@/lib/types";
import { formatarDataBR } from "@/lib/format";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";
import { ResumoCidadaoBox } from "@/components/ResumoCidadaoBox";

export const dynamic = "force-dynamic";

export default async function SessaoDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const res = await safeFetchApi<SessaoDetalheOut>(`/sessoes/${encodeURIComponent(id)}`);

  if (res.error || !res.data) {
    return (
      <div className="space-y-4">
        <Link
          href="/sessoes"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Voltar para sessões
        </Link>
        <EstadoErroAPI
          titulo={res.status === 404 ? "Sessão não encontrada" : "Erro ao carregar sessão"}
          mensagem={res.error || "Registro indisponível."}
        />
      </div>
    );
  }

  const s = res.data;

  return (
    <div className="space-y-8">
      <Link
        href="/sessoes"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        Voltar para a lista de sessões
      </Link>

      {/* Cabeçalho */}
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8 space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-[var(--surface-alt)] px-3 py-1 font-semibold text-[var(--ink-muted)]">
            {s.tipo_descricao}
          </span>
          <span className="tabular-nums text-[var(--ink-muted)]">
            Abertura: {formatarDataBR(s.data_abertura)}
            {s.horario_abertura ? ` às ${s.horario_abertura}` : ""}
          </span>
          {s.quorum !== null && (
            <span className="tabular-nums text-[var(--ink-muted)]">
              · Quórum registrado: {s.quorum}
            </span>
          )}
        </div>
        <h1 className="text-3xl font-bold text-[var(--ink)]">{s.nome_sessao}</h1>
        <div className="flex flex-wrap items-center gap-4">
          {s.ata_pdf_url && (
            <a
              href={s.ata_pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline"
            >
              Abrir ata oficial em PDF <ExternalLink className="w-4 h-4" aria-hidden="true" />
            </a>
          )}
          <Link
            href={`/boletins?sessao=${encodeURIComponent(s.sessao_id)}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
          >
            Gerar alerta WhatsApp e cards Instagram desta sessão
          </Link>
        </div>
      </section>

      {s.resumo_cidadao && (
        <ResumoCidadaoBox
          resumo={s.resumo_cidadao}
          titulo="Resumo automático da sessão em linguagem simples"
        />
      )}

      {/* Lista de Presença */}
      <section aria-labelledby="sec-presencas-sessao" className="space-y-3">
        <h2 id="sec-presencas-sessao" className="text-2xl font-bold text-[var(--ink)]">
          Presenças registradas ({s.presencas.length})
        </h2>
        {s.presencas.length === 0 ? (
          <p className="text-sm text-[var(--ink-muted)] italic">
            Sem lista de presença publicada para esta sessão.
          </p>
        ) : (
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {s.presencas.map((p) => {
              const presente = p.status_normalizado === "PRESENTE";
              return (
                <Link
                  key={p.presenca_id}
                  href={`/vereadores/${p.vereador_id}`}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 flex items-center justify-between gap-2 hover:border-[var(--primary)]"
                >
                  <span className="font-semibold text-sm text-[var(--ink)]">
                    {p.nome_exibicao}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      presente
                        ? "bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)]"
                        : "bg-[var(--status-warn-bg)] text-[var(--status-warn-ink)]"
                    }`}
                  >
                    {p.situacao_descricao}
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      {/* Pauta da Sessão */}
      <section aria-labelledby="sec-pauta-sessao" className="space-y-3">
        <h2 id="sec-pauta-sessao" className="text-2xl font-bold text-[var(--ink)]">
          Pauta e proposições discutidas ({s.pauta_itens.length})
        </h2>
        {s.pauta_itens.length === 0 ? (
          <p className="text-sm text-[var(--ink-muted)] italic">
            Nenhum item de pauta registrado para esta sessão.
          </p>
        ) : (
          <div className="space-y-3">
            {s.pauta_itens.map((item) => (
              <article
                key={item.pauta_item_id}
                className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--ink-muted)]">
                  <span className="font-semibold tabular-nums">Item {item.ordem}</span>
                  <span>· {item.tipo_descricao_origem}</span>
                  {item.tipo_pauta_descricao && <span>· {item.tipo_pauta_descricao}</span>}
                </div>
                <Link
                  href={`/materias/${item.proposicao_id}`}
                  className="mt-1 block font-bold text-base text-[var(--primary)] hover:underline"
                >
                  {item.nome_materia}
                </Link>
                <p className="mt-1 text-sm text-[var(--ink-muted)]">{item.ementa}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Votações e Votos Nominais */}
      <section aria-labelledby="sec-votacoes-sessao" className="space-y-4">
        <h2 id="sec-votacoes-sessao" className="text-2xl font-bold text-[var(--ink)]">
          Resultados das votações ({s.votacoes.length})
        </h2>
        {s.votacoes.length === 0 ? (
          <p className="text-sm text-[var(--ink-muted)] italic">
            Nenhuma votação registrada nesta sessão.
          </p>
        ) : (
          <div className="space-y-4">
            {s.votacoes.map((v) => (
              <article
                key={v.votacao_id}
                className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <Link
                      href={`/materias/${v.proposicao_id}`}
                      className="text-lg font-bold text-[var(--primary)] hover:underline"
                    >
                      {v.nome_materia}
                    </Link>
                    {v.unanime_flag_api && (
                      <p className="text-xs text-[var(--ink-muted)] mt-0.5">
                        Marcada na fonte oficial como votação unânime.
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2 text-xs tabular-nums font-semibold">
                    <span className="rounded-lg bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)] px-2.5 py-1">
                      Favoráveis: {v.placar_favoravel}
                    </span>
                    <span className="rounded-lg bg-[var(--status-warn-bg)] text-[var(--status-warn-ink)] px-2.5 py-1">
                      Contrários: {v.placar_contrario}
                    </span>
                    <span className="rounded-lg bg-[var(--surface-alt)] px-2.5 py-1">
                      Abstenções: {v.placar_abstencao}
                    </span>
                    <span className="rounded-lg bg-[var(--surface-alt)] px-2.5 py-1">
                      Ausentes: {v.placar_ausente}
                    </span>
                  </div>
                </div>

                {v.votos_nominais.length > 0 ? (
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 pt-3 border-t border-[var(--border)]">
                    {v.votos_nominais.map((vn) => (
                      <div
                        key={vn.voto_id}
                        className="flex items-center justify-between gap-2 rounded-lg bg-[var(--surface-alt)] px-3 py-2 text-xs"
                      >
                        <Link
                          href={`/vereadores/${vn.vereador_id}`}
                          className="font-semibold text-[var(--ink)] hover:underline"
                        >
                          {vn.nome_exibicao}
                        </Link>
                        <span className="font-medium text-[var(--ink-muted)]">
                          {vn.voto_descricao}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[var(--ink-muted)] italic">
                    Votos nominais individuais não publicados nesta votação.
                  </p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <ProvenienciaBox proveniencia={s.proveniencia} />
    </div>
  );
}
