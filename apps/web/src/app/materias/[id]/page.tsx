import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { safeFetchApi } from "@/lib/api";
import type { MateriaDetalheOut } from "@/lib/types";
import { formatarDataBR } from "@/lib/format";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";
import { ResumoCidadaoBox } from "@/components/ResumoCidadaoBox";

export const dynamic = "force-dynamic";

export default async function MateriaDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const res = await safeFetchApi<MateriaDetalheOut>(`/materias/${encodeURIComponent(id)}`);

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
          titulo={res.status === 404 ? "Matéria não encontrada" : "Erro ao carregar matéria"}
          mensagem={res.error || "Registro indisponível."}
        />
      </div>
    );
  }

  const m = res.data;

  return (
    <div className="space-y-8">
      <Link
        href="/sessoes"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        Voltar para sessões
      </Link>

      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8 space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-[var(--surface-alt)] px-3 py-1 font-semibold text-[var(--ink-muted)]">
            {m.tipo_descricao_origem}
          </span>
          <span className="rounded-full bg-[var(--surface-alt)] px-3 py-1 font-semibold text-[var(--ink)]">
            {m.situacao_atual || "Situação não informada"}
          </span>
          {m.data_publicacao && (
            <span className="tabular-nums text-[var(--ink-muted)]">
              Publicação: {formatarDataBR(m.data_publicacao)}
            </span>
          )}
        </div>

        <h1 className="text-3xl font-bold text-[var(--ink)]">{m.nome_materia}</h1>
        <p className="text-base text-[var(--ink)] leading-relaxed">{m.ementa}</p>

        <div className="pt-3 border-t border-[var(--border)] flex flex-wrap gap-3 text-sm">
          <span className="text-[var(--ink-muted)] font-medium">Autoria:</span>
          {m.autores.length === 0 ? (
            <span className="text-[var(--ink-muted)] italic">Não informada na fonte</span>
          ) : (
            m.autores.map((a) =>
              a.vereador_id ? (
                <Link
                  key={a.autoria_id}
                  href={`/vereadores/${a.vereador_id}`}
                  className="font-semibold text-[var(--primary)] hover:underline"
                >
                  {a.nome_exibicao || a.nome_politico}
                </Link>
              ) : (
                <span key={a.autoria_id} className="font-semibold text-[var(--ink)]">
                  {a.autor_institucional || a.tipo_autor}
                </span>
              ),
            )
          )}
        </div>

        {m.anexo_principal_url && (
          <a
            href={m.anexo_principal_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--primary)] hover:underline"
          >
            Abrir documento anexo ({m.anexo_principal_nome || "PDF"}){" "}
            <ExternalLink className="w-4 h-4" aria-hidden="true" />
          </a>
        )}
      </section>

      {m.resumo_cidadao && (
        <ResumoCidadaoBox
          resumo={m.resumo_cidadao}
          titulo="Resumo automático desta proposição em linguagem simples"
        />
      )}

      {/* Deliberações em sessão */}
      {m.deliberacoes_em_sessao.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-2xl font-bold text-[var(--ink)]">Deliberações em plenário</h2>
          <div className="space-y-3">
            {m.deliberacoes_em_sessao.map((d, idx) => (
              <article
                key={`${d.sessao_id}-${idx}`}
                className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 flex flex-wrap items-center justify-between gap-3"
              >
                <div>
                  <Link
                    href={`/sessoes/${d.sessao_id}`}
                    className="font-bold text-[var(--primary)] hover:underline"
                  >
                    {d.nome_sessao}
                  </Link>
                  <p className="text-xs text-[var(--ink-muted)] tabular-nums">
                    {formatarDataBR(d.data_sessao)} · Ordem {d.ordem} · Turno {d.turno}
                  </p>
                </div>
                <div className="flex gap-2 text-xs tabular-nums font-semibold">
                  <span className="rounded bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)] px-2 py-1">
                    Favoráveis: {d.placar_favoravel}
                  </span>
                  <span className="rounded bg-[var(--status-warn-bg)] text-[var(--status-warn-ink)] px-2 py-1">
                    Contrários: {d.placar_contrario}
                  </span>
                  <span className="rounded bg-[var(--surface-alt)] px-2 py-1">
                    Abstenções: {d.placar_abstencao}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* Tramitações */}
      {m.tramitacoes.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-2xl font-bold text-[var(--ink)]">Histórico de tramitação</h2>
          <ol className="rounded-xl border border-[var(--border)] bg-[var(--surface)] divide-y divide-[var(--border)]">
            {m.tramitacoes.map((t) => (
              <li key={t.tramitacao_id} className="p-4 text-sm">
                <p className="font-semibold tabular-nums text-[var(--ink)]">
                  {formatarDataBR(t.data_tramitacao)} — {t.situacao_descricao || "Movimentação"}
                </p>
                <p className="mt-0.5 text-xs text-[var(--ink-muted)]">
                  {t.local_origem || "Origem não informada"} →{" "}
                  {t.local_destino || "Destino não informado"}
                </p>
              </li>
            ))}
          </ol>
        </section>
      )}

      <ProvenienciaBox proveniencia={m.proveniencia} />
    </div>
  );
}
