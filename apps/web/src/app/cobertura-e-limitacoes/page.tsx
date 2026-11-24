import Link from "next/link";
import { safeFetchApi } from "@/lib/api";
import type { DeclaracaoTransparenciaOut, HealthOut } from "@/lib/types";
import {
  formatarDataBR,
  formatarDataHoraBR,
  formatarInteiro,
  rotuloFonte,
} from "@/lib/format";
import { EstadoAusente } from "@/components/EstadoAusente";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Cobertura e Limitações dos Dados",
  description:
    "Escopo temporal coberto pelo Cerrado Aberto, lacunas históricas documentadas nas fontes oficiais e status do pedido via Lei de Acesso à Informação.",
};

export default async function CoberturaELimitacoesPage() {
  const [healthRes, declRes] = await Promise.all([
    safeFetchApi<HealthOut>("/health"),
    safeFetchApi<DeclaracaoTransparenciaOut[]>("/transparencia/declaracoes"),
  ]);

  const health = healthRes.data;
  const declaracoes = declRes.data || [];

  return (
    <div className="space-y-8 max-w-4xl">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Transparência sobre o Escopo · Regra NULL ≠ 0
        </p>
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Cobertura atual e limitações documentadas
        </h1>
        <p className="text-base text-[var(--ink-muted)] leading-relaxed">
          O <strong>Cerrado Aberto</strong> mostra com clareza até onde vão os dados disponíveis
          hoje nos portais da Câmara Municipal de Inhumas e quais períodos ainda dependem de
          fornecimento complementar ou nova etapa de coleta. Nunca preenchemos lacunas com zero.
        </p>
      </header>

      {/* Cobertura ativa por fonte */}
      <section
        aria-labelledby="sec-cobertura-fontes"
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-4"
      >
        <h2 id="sec-cobertura-fontes" className="text-xl font-bold text-[var(--ink)]">
          1. O que já está disponível nesta versão
        </h2>

        <div
          className="overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Resumo da cobertura temporal e volume de registros por fonte oficial"
        >
          <table className="w-full text-left text-sm border-collapse min-w-[640px]">
            <caption className="sr-only">
              Resumo da cobertura temporal e volume de registros por fonte oficial
            </caption>
            <thead className="sticky top-0 bg-[var(--surface)] z-10">
              <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                <th scope="col" className="py-2 pr-4">
                  Fonte oficial
                </th>
                <th scope="col" className="py-2 pr-4">
                  Período ativo no MVP
                </th>
                <th scope="col" className="py-2 pr-4">
                  Conteúdo coberto
                </th>
                <th scope="col" className="py-2">
                  Última coleta
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[var(--border)]/60 align-top">
                <td className="py-3 pr-4 font-semibold text-[var(--ink)]">
                  Sistema Legislativo Nexlegis
                </td>
                <td className="py-3 pr-4 whitespace-nowrap tabular-nums">2025–2026</td>
                <td className="py-3 pr-4 text-[var(--ink-muted)]">
                  Vereadores ({formatarInteiro(health?.contagens_persistidas.vereador)}), sessões
                  plenárias ({formatarInteiro(health?.contagens_persistidas.sessao)}), presenças,
                  pautas ({formatarInteiro(health?.contagens_persistidas.pauta_item)}), votações (
                  {formatarInteiro(health?.contagens_persistidas.votacao)}) e proposições (
                  {formatarInteiro(health?.contagens_persistidas.proposicao)}).
                </td>
                <td className="py-3 tabular-nums text-xs text-[var(--ink-muted)] whitespace-nowrap">
                  {formatarDataHoraBR(
                    health?.ultima_coleta_por_fonte.find((f) => f.fonte_id === "nexlegis")
                      ?.ultima_coleta_em,
                  )}
                </td>
              </tr>
              <tr className="border-b border-[var(--border)]/60 align-top">
                <td className="py-3 pr-4 font-semibold text-[var(--ink)]">
                  Portal da Transparência (CENTI / NúcleoGov)
                </td>
                <td className="py-3 pr-4 whitespace-nowrap tabular-nums">
                  Exercício de 2026 (jan–out)
                </td>
                <td className="py-3 pr-4 text-[var(--ink-muted)]">
                  Repasses e devoluções de duodécimo, empenhos, liquidações, pagamentos, diárias do
                  Elemento 14, folha de pagamento com lotação por gabinete e declarações oficiais.
                </td>
                <td className="py-3 tabular-nums text-xs text-[var(--ink-muted)] whitespace-nowrap">
                  {formatarDataHoraBR(
                    health?.ultima_coleta_por_fonte.find(
                      (f) => f.fonte_id === "transparencia_centi",
                    )?.ultima_coleta_em,
                  )}
                </td>
              </tr>
              <tr className="border-b border-[var(--border)]/60 align-top">
                <td className="py-3 pr-4 font-semibold text-[var(--ink)]">
                  Portal de Legislação Municipal (NúcleoGov)
                </td>
                <td className="py-3 pr-4 whitespace-nowrap tabular-nums">1990–2026</td>
                <td className="py-3 pr-4 text-[var(--ink-muted)]">
                  Metadados e ementas oficiais de{" "}
                  {formatarInteiro(health?.contagens_persistidas.norma)} normas municipais (Lei
                  Orgânica, Leis Ordinárias, Complementares, LDO, LOA e Códigos), com link
                  permanente para o portal oficial. PDFs digitalizados aguardam etapa de OCR em lote
                  (ADR-004).
                </td>
                <td className="py-3 tabular-nums text-xs text-[var(--ink-muted)] whitespace-nowrap">
                  {formatarDataHoraBR(
                    health?.ultima_coleta_por_fonte.find(
                      (f) => f.fonte_id === "legislacao_nucleogov",
                    )?.ultima_coleta_em,
                  )}
                </td>
              </tr>
              <tr className="border-b border-[var(--border)]/60 align-top">
                <td className="py-3 pr-4 font-semibold text-[var(--ink)]">
                  SICONFI — Secretaria do Tesouro Nacional
                </td>
                <td className="py-3 pr-4 whitespace-nowrap tabular-nums">2024 e 2025 (DCA)</td>
                <td className="py-3 pr-4 text-[var(--ink-muted)]">
                  Anexo I-E (Função 01 - Legislativa) de Inhumas e 7 municípios goianos de porte
                  semelhante ({formatarInteiro(health?.contagens_persistidas.comparativo_legislativo_siconfi)}{" "}
                  registros consolidados).
                </td>
                <td className="py-3 tabular-nums text-xs text-[var(--ink-muted)] whitespace-nowrap">
                  {formatarDataHoraBR(
                    health?.ultima_coleta_por_fonte.find((f) => f.fonte_id === "siconfi_stn")
                      ?.ultima_coleta_em,
                  )}
                </td>
              </tr>
              <tr className="border-b border-[var(--border)]/60 align-top">
                <td className="py-3 pr-4 font-semibold text-[var(--ink)]">
                  IBGE — Demografia Municipal
                </td>
                <td className="py-3 pr-4 whitespace-nowrap tabular-nums">
                  Censo 2022 e Estimativa 2026
                </td>
                <td className="py-3 pr-4 text-[var(--ink-muted)]">
                  População oficial de Inhumas/GO (código IBGE 5210000):{" "}
                  <strong>54.133 habitantes</strong> na Estimativa 2026 e{" "}
                  <strong>52.204 habitantes</strong> no Censo Demográfico 2022.
                </td>
                <td className="py-3 tabular-nums text-xs text-[var(--ink-muted)] whitespace-nowrap">
                  Base anual oficial
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Lacunas históricas documentadas no banco */}
      <section aria-labelledby="sec-lacunas-banco" className="space-y-3">
        <h2 id="sec-lacunas-banco" className="text-xl font-bold text-[var(--ink)]">
          2. Lacunas históricas e técnicas documentadas
        </h2>
        <p className="text-sm text-[var(--ink-muted)]">
          As limitações abaixo decorrem da disponibilidade atual nas fontes públicas ou de recortes
          técnicos registrados no banco de dados:
        </p>

        {health?.lacunas_historicas_documentadas.map((lacuna) => (
          <EstadoAusente
            key={lacuna.lacuna_id}
            tom="aviso"
            titulo={`${rotuloFonte(lacuna.fonte_id)} (${formatarDataBR(lacuna.data_inicio_lacuna)} a ${formatarDataBR(lacuna.data_fim_lacuna)})`}
            descricao={`${lacuna.motivo_oficial}${
              lacuna.pedido_lai_previsto
                ? " Há minuta de pedido via Lei de Acesso à Informação (LAI) preparada para solicitar a base histórica em formato aberto."
                : ""
            }`}
          />
        ))}

        <EstadoAusente
          tom="aviso"
          titulo="Lotação da Presidência da Câmara (LACUNA_PARCIAL_LOTACAO)"
          descricao="Na folha de pagamento de 2026, a unidade PRESIDENCIA reúne servidores de apoio administrativo e institucional da Casa sem separação de gabinete individual para o Presidente. Para não atribuir estrutura institucional da Câmara a um único mandato nem subestimar o indicador com R$ 0,00, a folha de gabinete e o total do Custo da Estrutura do Mandato do Presidente permanecem como Não apurado (NULL)."
        />

        <EstadoAusente
          tom="neutro"
          titulo="Competências de novembro e dezembro de 2026 (ABERTA_SEM_PUBLICACAO)"
          descricao="No momento da última coleta verificada (12/11/2026), as folhas de pagamento de 11/2026 e 12/2026 ainda não haviam sido fechadas e publicadas no Portal da Transparência."
        />

        <EstadoAusente
          tom="neutro"
          titulo="Histórico legislativo anterior a 2025 no Nexlegis (Lote 3: 2020–2024)"
          descricao="O MVP público prioriza a legislatura atual (2025–2028, anos de 2025 e 2026). A carga retroativa de sessões e proposições de 2020 a 2024 (Lote 3) está mapeada para etapa posterior."
        />
      </section>

      {/* Declarações oficiais */}
      {declaracoes.length > 0 && (
        <section aria-labelledby="sec-declaracoes" className="space-y-3">
          <h2 id="sec-declaracoes" className="text-xl font-bold text-[var(--ink)]">
            3. Declarações oficiais emitidas pelo Portal da Transparência
          </h2>
          {declaracoes.map((d) => (
            <EstadoAusente
              key={d.declaracao_id}
              titulo={`${d.titulo_oficial} (${formatarDataBR(d.data_inicio_cobertura)} a ${formatarDataBR(d.data_fim_cobertura)})`}
              descricao={d.observacao_cruzamento || d.texto_integral}
            />
          ))}
        </section>
      )}

      <p className="text-sm text-[var(--ink-muted)]">
        Identificou algum documento público que complemente essas lacunas? Envie pelo{" "}
        <Link href="/correcoes" className="underline font-semibold text-[var(--primary)]">
          Canal de correção
        </Link>
        .
      </p>
    </div>
  );
}
