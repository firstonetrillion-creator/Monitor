import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, FileWarning } from "lucide-react";
import { safeFetchApi } from "@/lib/api";
import type { NormaDetalheOut } from "@/lib/types";
import { formatarDataBR } from "@/lib/format";
import { ResumoCidadaoBox } from "@/components/ResumoCidadaoBox";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";

export const metadata: Metadata = {
  title: "Detalhe da Norma Municipal | Cerrado Aberto",
};

export const dynamic = "force-dynamic";

export default async function NormaDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { data: norma, status } = await safeFetchApi<NormaDetalheOut>(
    `/legislacao/${encodeURIComponent(id)}`,
  );

  if (status === 404 || !norma) {
    notFound();
  }

  const titulo = `${norma.categoria_descricao} nº ${norma.numero}${norma.ano ? `/${norma.ano}` : ""}`;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-10 space-y-6">
      <Link
        href="/legislacao"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--primary)] hover:underline"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        Voltar para o catálogo de legislação
      </Link>

      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-[var(--primary)]/10 text-[var(--primary)] px-2.5 py-0.5 font-semibold">
            {norma.categoria_descricao}
          </span>
          <span className="text-[var(--ink-muted)] tabular-nums">
            Publicação oficial: {formatarDataBR(norma.data_publicacao)}
          </span>
          {norma.data_publicacao_portal && (
            <span className="text-[var(--ink-muted)] tabular-nums">
              · Cadastrada no portal em {formatarDataBR(norma.data_publicacao_portal)}
            </span>
          )}
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-[var(--ink)]">{titulo}</h1>
        <div className="pt-1">
          <a
            href={norma.fonte_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--primary)] text-[var(--primary-ink)] px-4 py-2 text-sm font-semibold hover:opacity-95"
          >
            Abrir lei e PDF oficial na Câmara
            <ExternalLink className="w-4 h-4" aria-hidden="true" />
          </a>
        </div>
      </header>

      <ResumoCidadaoBox
        resumo={norma.resumo_cidadao}
        titulo={`Resumo em linguagem simples — ${titulo}`}
      />

      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-2">
        <h2 className="font-display text-lg font-bold text-[var(--ink)]">
          Ementa oficial publicada
        </h2>
        <p className="text-sm text-[var(--ink)] leading-relaxed">{norma.ementa}</p>
      </section>

      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-3">
        <h2 className="font-display text-lg font-bold text-[var(--ink)]">
          Texto integral e transparência de extração (PDF / OCR)
        </h2>
        {norma.texto_extraido ? (
          <div className="space-y-2">
            {norma.extraido_por_ocr && (
              <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--accent)]">
                <FileWarning className="w-4 h-4 shrink-0" aria-hidden="true" />
                {norma.motivo_revisao_humana ||
                  "Texto extraído automaticamente por OCR — confira sempre o PDF oficial."}
              </p>
            )}
            <pre className="whitespace-pre-wrap font-sans text-sm text-[var(--ink)] bg-[var(--bg)] rounded-xl p-4 border border-[var(--border)] leading-relaxed">
              {norma.texto_extraido}
            </pre>
          </div>
        ) : (
          <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
            Esta norma possui{" "}
            <strong className="text-[var(--ink)]">{norma.total_anexos} anexo(s)</strong> no portal
            oficial (em geral PDF digitalizado em imagem, conforme documentado em{" "}
            <Link href="/cobertura-e-limitacoes" className="underline text-[var(--primary)]">
              Cobertura e Limitações
            </Link>
            ). Para consultar a íntegra com assinatura e carimbos originais, utilize o botão{" "}
            <strong>&ldquo;Abrir lei e PDF oficial na Câmara&rdquo;</strong> acima.
          </p>
        )}
      </section>

      <ProvenienciaBox proveniencia={norma.proveniencia} />
    </div>
  );
}
