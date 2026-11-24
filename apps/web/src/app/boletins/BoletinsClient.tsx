"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Camera,
  Download,
  ExternalLink,
  MessageCircle,
  Smartphone,
} from "lucide-react";
import { api } from "@/lib/api";
import { baixarCardPng, construirSlideStoryUnico } from "@/lib/cardCanvas";
import type { BoletimSemanalOut } from "@/lib/types";
import { formatarBRL, formatarDataBR, formatarDataHoraBR } from "@/lib/format";
import { BotaoCopiar } from "@/components/BotaoCopiar";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { ProvenienciaBox } from "@/components/ProvenienciaBox";
import { ResumoCidadaoBox } from "@/components/ResumoCidadaoBox";

interface BoletinsClientProps {
  initialBoletim: BoletimSemanalOut;
}

export function BoletinsClient({ initialBoletim }: BoletinsClientProps) {
  const [boletim, setBoletim] = useState<BoletimSemanalOut>(initialBoletim);
  const [sessaoSelecionada, setSessaoSelecionada] = useState<string>(initialBoletim.sessao_id);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trocarSessao = async (novoId: string) => {
    setSessaoSelecionada(novoId);
    setLoading(true);
    setError(null);
    try {
      const novo = await api.boletimSemanal({ sessao_id: novoId });
      setBoletim(novo);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Não foi possível carregar o boletim desta sessão.",
      );
    } finally {
      setLoading(false);
    }
  };

  const prefixoArquivo = `cerrado-aberto-${boletim.sessao_id}`;
  const linkWhatsapp = `https://wa.me/?text=${encodeURIComponent(boletim.alerta_whatsapp)}`;
  const storySlide = construirSlideStoryUnico(boletim);

  const baixarCarrosselCompleto = () => {
    boletim.slides_instagram.forEach((slide, idx) => {
      setTimeout(() => {
        baixarCardPng(slide, boletim.slides_instagram.length, "feed", prefixoArquivo);
      }, idx * 180);
    });
  };

  return (
    <div className="space-y-8">
      {/* Seletor de sessão */}
      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 flex flex-wrap items-end justify-between gap-4">
        <div className="flex-1 min-w-[260px]">
          <label
            htmlFor="seletor-sessao-boletim"
            className="block text-xs font-semibold uppercase text-[var(--ink-muted)] mb-1.5"
          >
            Escolher sessão plenária para o boletim
          </label>
          <select
            id="seletor-sessao-boletim"
            value={sessaoSelecionada}
            disabled={loading}
            onChange={(e) => void trocarSessao(e.target.value)}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm font-medium text-[var(--ink)]"
          >
            {boletim.sessoes_disponiveis.map((op) => (
              <option key={op.sessao_id} value={op.sessao_id}>
                {formatarDataBR(op.data_abertura)} — {op.nome_sessao}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/sessoes/${boletim.sessao_id}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3.5 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
          >
            Ver página completa da sessão
          </Link>
          <a
            href="https://www.instagram.com/cerradoaberto/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-3.5 py-2 text-xs font-semibold hover:opacity-90"
          >
            <Camera className="w-3.5 h-3.5" aria-hidden="true" />
            Instagram Oficial ({boletim.handle_instagram_oficial})
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
          </a>
        </div>
      </section>

      {error && (
        <EstadoErroAPI
          mensagem={error}
          onTentarNovamente={() => void trocarSessao(sessaoSelecionada)}
        />
      )}

      {/* Resumo em linguagem simples da sessão */}
      <ResumoCidadaoBox
        resumo={boletim.resumo_sessao}
        titulo={`Resumo em linguagem simples — ${boletim.nome_sessao}`}
      />

      {/* Bloco 1: Alerta WhatsApp e Legenda Instagram */}
      <section
        aria-labelledby="sec-textos-prontos"
        className="grid gap-6 lg:grid-cols-2"
      >
        {/* Alerta WhatsApp */}
        <article className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 flex flex-col justify-between gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2
                id="sec-textos-prontos"
                className="text-lg font-bold text-[var(--ink)] flex items-center gap-2"
              >
                <MessageCircle className="w-5 h-5 text-[var(--primary)]" aria-hidden="true" />
                Alerta curto para WhatsApp
              </h2>
              <span className="rounded-full bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)] px-2.5 py-0.5 text-xs font-semibold tabular-nums">
                {boletim.alerta_whatsapp.length}/400 caracteres
              </span>
            </div>
            <p className="text-xs text-[var(--ink-muted)]">
              Formato objetivo (máximo 400 caracteres), com fonte oficial, link de conferência e
              opção clara de descadastro.
            </p>
            <pre
              id="texto-alerta-whatsapp"
              className="whitespace-pre-wrap rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3.5 text-xs text-[var(--ink)] font-sans leading-relaxed"
            >
              {boletim.alerta_whatsapp}
            </pre>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-[var(--border)]">
            <BotaoCopiar
              targetId="texto-alerta-whatsapp"
              textoFallback={boletim.alerta_whatsapp}
              rotulo="Copiar alerta WhatsApp"
            />
            <a
              href={linkWhatsapp}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-3.5 py-1.5 text-xs font-semibold hover:opacity-90"
            >
              <MessageCircle className="w-3.5 h-3.5" aria-hidden="true" />
              Compartilhar no WhatsApp
            </a>
          </div>
        </article>

        {/* Legenda Instagram Oficial */}
        <article className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 flex flex-col justify-between gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-bold text-[var(--ink)] flex items-center gap-2">
                <Camera className="w-5 h-5 text-[var(--accent)]" aria-hidden="true" />
                Legenda para o Instagram Oficial ({boletim.handle_instagram_oficial})
              </h2>
              <span className="rounded-full bg-[var(--surface-alt)] text-[var(--ink-muted)] px-2.5 py-0.5 text-xs font-semibold">
                Pronta para postar
              </span>
            </div>
            <p className="text-xs text-[var(--ink-muted)]">
              Texto editorial neutro com marcação de resumo automático, panorama financeiro 2026 e
              declaração de independência.
            </p>
            <pre
              id="texto-legenda-instagram"
              className="whitespace-pre-wrap max-h-56 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3.5 text-xs text-[var(--ink)] font-sans leading-relaxed"
              tabIndex={0}
            >
              {boletim.legenda_instagram}
            </pre>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-[var(--border)]">
            <BotaoCopiar
              targetId="texto-legenda-instagram"
              textoFallback={boletim.legenda_instagram}
              rotulo="Copiar legenda Instagram"
            />
          </div>
        </article>
      </section>

      {/* Bloco 2: Cartões PNG (Instagram Oficial 1080x1350 e Stories/Status 1080x1920) */}
      <section aria-labelledby="sec-cards-png" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="sec-cards-png" className="text-2xl font-bold text-[var(--ink)]">
              Cartões prontos para o Instagram Oficial ({boletim.handle_instagram_oficial}) e Status
            </h2>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">
              Imagens geradas localmente em alta resolução (PNG) com nossa paleta, fonte oficial e
              data da coleta.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={baixarCarrosselCompleto}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] text-[var(--primary-ink)] px-4 py-2 text-xs font-semibold hover:opacity-90"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Baixar carrossel completo (3 PNGs)
            </button>
            <button
              type="button"
              onClick={() => baixarCardPng(storySlide, 1, "story", prefixoArquivo)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
            >
              <Smartphone className="w-3.5 h-3.5" aria-hidden="true" />
              Baixar Story / Status (1080×1920)
            </button>
          </div>
        </div>

        {/* Pré-visualização dos 3 slides do carrossel */}
        <div className="grid gap-5 md:grid-cols-3">
          {boletim.slides_instagram.map((slide) => (
            <article
              key={slide.numero}
              className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] overflow-hidden flex flex-col justify-between shadow-sm"
            >
              <div>
                {/* Faixa superior do card */}
                <div className="bg-[var(--primary)] text-[var(--primary-ink)] px-4 py-3 flex items-center justify-between gap-2">
                  <div>
                    <p className="font-display text-sm font-bold leading-none">Cerrado Aberto</p>
                    <p className="text-[10px] opacity-85 mt-0.5">
                      Iniciativa cidadã independente
                    </p>
                  </div>
                  <span className="rounded-full bg-black/20 px-2 py-0.5 text-[11px] font-bold tabular-nums">
                    {slide.numero}/{boletim.slides_instagram.length}
                  </span>
                </div>
                <div className="h-1 bg-[#D99B16]" aria-hidden="true" />

                <div className="p-4 space-y-3">
                  <p
                    className={`text-[10px] font-bold uppercase tracking-wider ${
                      slide.numero === 3 ? "text-[var(--accent)]" : "text-[var(--primary)]"
                    }`}
                  >
                    {slide.etiqueta}
                  </p>
                  <h3 className="font-display text-xl font-bold text-[var(--ink)] leading-tight">
                    {slide.titulo}
                  </h3>
                  <p className="text-xs text-[var(--ink-muted)]">{slide.subtitulo}</p>

                  <ul className="space-y-2 pt-1">
                    {slide.itens.map((item, idx) => (
                      <li
                        key={idx}
                        className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs font-medium text-[var(--ink)] border-l-4 border-l-[var(--primary)]"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="bg-[var(--surface-alt)] border-t border-[var(--border)] p-3.5 space-y-2.5">
                <p className="text-[10px] text-[var(--ink-muted)] leading-snug">
                  {slide.rodape_fonte}
                </p>
                <button
                  type="button"
                  onClick={() =>
                    baixarCardPng(
                      slide,
                      boletim.slides_instagram.length,
                      "feed",
                      prefixoArquivo,
                    )
                  }
                  className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--ink)] hover:border-[var(--primary)]"
                >
                  <Download className="w-3.5 h-3.5" aria-hidden="true" />
                  Baixar Slide {slide.numero} (1080×1350)
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Bloco 3: Destaques da pauta em linguagem simples */}
      {boletim.destaques_pauta.length > 0 && (
        <section aria-labelledby="sec-pauta-simples" className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="sec-pauta-simples" className="text-2xl font-bold text-[var(--ink)]">
              Proposições da sessão em linguagem simples ({boletim.destaques_pauta.length})
            </h2>
            <p className="text-xs text-[var(--ink-muted)]">
              Panorama financeiro 2026:{" "}
              <strong>{formatarBRL(boletim.panorama_financeiro_2026.despesa_paga_acumulada)}</strong>{" "}
              pagos (coleta{" "}
              {formatarDataHoraBR(boletim.panorama_financeiro_2026.ultima_coleta_transparencia)})
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {boletim.destaques_pauta.map((item) => (
              <article
                key={item.proposicao_id}
                className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 flex flex-col justify-between gap-3"
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span className="rounded-full bg-[var(--surface-alt)] px-2.5 py-0.5 font-semibold text-[var(--ink-muted)]">
                      {item.tipo_descricao_origem}
                    </span>
                    <span className="rounded-full bg-[var(--status-null-bg)] text-[var(--status-null-ink)] px-2 py-0.5 font-semibold">
                      Resumo automático
                    </span>
                  </div>

                  <Link
                    href={`/materias/${item.proposicao_id}`}
                    className="block text-base font-bold text-[var(--primary)] hover:underline"
                  >
                    {item.nome_materia}
                  </Link>
                  <p className="text-sm text-[var(--ink)] leading-relaxed">
                    {item.resumo_cidadao.o_que_propoe}
                  </p>
                  <p className="text-xs text-[var(--ink-muted)]">
                    {item.resumo_cidadao.situacao_e_resultado}
                  </p>
                </div>

                <div className="pt-2 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="font-medium text-[var(--ink)]">{item.placar_resumo}</span>
                  <a
                    href={item.resumo_cidadao.fonte_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 underline text-[var(--primary)]"
                  >
                    Documento original <ExternalLink className="w-3 h-3" aria-hidden="true" />
                  </a>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      <ProvenienciaBox proveniencia={boletim.proveniencia} />
    </div>
  );
}
