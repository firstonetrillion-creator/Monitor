"use client";

import type { BairroResumoOut } from "@/lib/types";
import { parseDecimal } from "@/lib/format";

interface MapaBairrosSvgProps {
  bairros: BairroResumoOut[];
  slugSelecionado: string | null;
  onSelecionar: (slug: string) => void;
}

const COR_REGIAO: Record<string, string> = {
  Central: "#1F4E3D",
  Norte: "#2B6E57",
  Sul: "#B44B2A",
  Leste: "#C78B12",
  Oeste: "#5A6B5C",
  "Distrito / Rural": "#7C5233",
};

export function MapaBairrosSvg({
  bairros,
  slugSelecionado,
  onSelecionar,
}: MapaBairrosSvgProps) {
  const comCoords = bairros
    .map((b) => ({
      ...b,
      lat: parseDecimal(b.latitude_aprox),
      lon: parseDecimal(b.longitude_aprox),
    }))
    .filter((b): b is BairroResumoOut & { lat: number; lon: number } => b.lat !== null && b.lon !== null);

  if (comCoords.length === 0) {
    return null;
  }

  const lats = comCoords.map((b) => b.lat);
  const lons = comCoords.map((b) => b.lon);
  const minLat = Math.min(...lats) - 0.008;
  const maxLat = Math.max(...lats) + 0.008;
  const minLon = Math.min(...lons) - 0.008;
  const maxLon = Math.max(...lons) + 0.008;
  const maxQtd = Math.max(...comCoords.map((b) => b.total_proposicoes), 1);

  const largura = 720;
  const altura = 440;
  const padX = 56;
  const padY = 44;

  function projX(lon: number): number {
    return padX + ((lon - minLon) / Math.max(0.0001, maxLon - minLon)) * (largura - padX * 2);
  }
  function projY(lat: number): number {
    return padY + ((maxLat - lat) / Math.max(0.0001, maxLat - minLat)) * (altura - padY * 2);
  }

  // Rótulos fixos apenas para os 8 maiores + o selecionado para evitar sobreposição
  const topSlugs = new Set(comCoords.slice(0, 8).map((b) => b.slug));

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-display text-lg font-bold text-[var(--ink)]">
            Distribuição cartográfica aproximada por região e bairro
          </h2>
          <p className="text-xs text-[var(--ink-muted)]">
            Clique ou navegue por teclado em qualquer círculo para abrir as proposições do bairro.
            O tamanho reflete o volume de proposições parlamentares que citam a localidade.
          </p>
        </div>
        <span className="text-xs font-medium rounded-full bg-[var(--surface-alt)] px-3 py-1 text-[var(--ink-muted)]">
          Mapa vetorial local · sem rastreamento externo
        </span>
      </div>

      <div
        role="region"
        aria-label="Mapa vetorial interativo de indicações e requerimentos por bairro de Inhumas"
        tabIndex={0}
        className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--bg)]"
      >
        <svg
          viewBox={`0 0 ${largura} ${altura}`}
          className="w-full min-w-[540px] h-auto block"
          role="group"
          aria-label="Mapa de bolhas dos bairros de Inhumas ordenados por número de proposições parlamentares"
        >
          {/* Grade cartográfica discreta */}
          {[0.25, 0.5, 0.75].map((f) => (
            <g key={f} stroke="var(--border)" strokeDasharray="4 4" strokeWidth="1" opacity="0.7">
              <line x1={padX} y1={padY + f * (altura - padY * 2)} x2={largura - padX} y2={padY + f * (altura - padY * 2)} />
              <line x1={padX + f * (largura - padX * 2)} y1={padY} x2={padX + f * (largura - padX * 2)} y2={altura - padY} />
            </g>
          ))}

          {/* Rosa dos ventos / orientação */}
          <g fill="var(--ink-muted)" fontSize="11" fontWeight="600">
            <text x={largura / 2} y="20" textAnchor="middle">NORTE (saída Itaberaí / Santa Amália)</text>
            <text x={largura / 2} y={altura - 12} textAnchor="middle">SUL (saída Goiânia / GO-070)</text>
            <text x="14" y={altura / 2} textAnchor="start">OESTE</text>
            <text x={largura - 14} y={altura / 2} textAnchor="end">LESTE</text>
          </g>

          {/* Camada 1: Bolhas clicáveis e focáveis (sem texto interno para conformidade WCAG 2.5.3) */}
          {comCoords.map((b) => {
            const cx = projX(b.lon);
            const cy = projY(b.lat);
            const raio = 8 + Math.sqrt(b.total_proposicoes / maxQtd) * 18;
            const ativo = slugSelecionado === b.slug;
            const cor = COR_REGIAO[b.regiao] || "#1F4E3D";

            return (
              <g
                key={b.slug}
                role="button"
                tabIndex={0}
                aria-label={`${b.nome_oficial} (${b.regiao}): ${b.total_proposicoes} proposições`}
                aria-pressed={ativo}
                onClick={() => onSelecionar(b.slug)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelecionar(b.slug);
                  }
                }}
                className="cursor-pointer focus:outline-none"
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={ativo ? raio + 3 : raio}
                  fill={cor}
                  fillOpacity={ativo ? 0.92 : 0.72}
                  stroke={ativo ? "#1F2421" : "#FFFFFF"}
                  strokeWidth={ativo ? 3 : 1.5}
                />
              </g>
            );
          })}

          {/* Camada 2: Números e rótulos desenhados acima de todos os círculos (decorativos para SR) */}
          <g aria-hidden="true" pointerEvents="none">
            {comCoords.map((b) => {
              const cx = projX(b.lon);
              const cy = projY(b.lat);
              const raio = 8 + Math.sqrt(b.total_proposicoes / maxQtd) * 18;
              const ativo = slugSelecionado === b.slug;
              const mostrarRotulo = ativo || topSlugs.has(b.slug);

              return (
                <g key={`lbl-${b.slug}`}>
                  <text
                    x={cx}
                    y={cy + 4}
                    textAnchor="middle"
                    fill="#FFFFFF"
                    fontSize={raio > 16 ? "12" : "10"}
                    fontWeight="700"
                  >
                    {b.total_proposicoes}
                  </text>
                  {mostrarRotulo && (
                    <text
                      x={cx}
                      y={cy - raio - 6}
                      textAnchor="middle"
                      fill="var(--ink)"
                      fontSize="11"
                      fontWeight={ativo ? "700" : "600"}
                    >
                      {b.nome_oficial.replace(/^(Setor|Residencial|Parque|Bairro)\s+/i, "")}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Legenda de regiões */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--ink-muted)]">
        {Object.entries(COR_REGIAO).map(([regiao, cor]) => (
          <span key={regiao} className="inline-flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-full inline-block"
              style={{ backgroundColor: cor }}
              aria-hidden="true"
            />
            {regiao}
          </span>
        ))}
      </div>
    </div>
  );
}
