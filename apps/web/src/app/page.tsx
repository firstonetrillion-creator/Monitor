import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Calendar,
  Code2,
  FileText,
  Landmark,
  MapPin,
  Scale,
  Search,
  Users,
} from "lucide-react";
import { safeFetchApi } from "@/lib/api";
import type {
  DespesasResumoOut,
  DuodecimoOut,
  HealthOut,
  PaginacaoOut,
  SessaoResumoOut,
  VereadorResumoOut,
} from "@/lib/types";
import {
  DEMOGRAFIA_MUNICIPIOS,
  formatarBRL,
  formatarDataBR,
  formatarDataHoraBR,
  formatarInteiro,
   parseDecimal,
  rotuloFonte,
} from "@/lib/format";
import { DadoComFonte } from "@/components/DadoComFonte";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { GlossarioTooltip } from "@/components/GlossarioTooltip";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [healthRes, vereadoresAtuaisRes, despesasRes, sessoesRes, duodecimoRes] =
    await Promise.all([
      safeFetchApi<HealthOut>("/health"),
      safeFetchApi<PaginacaoOut<VereadorResumoOut>>("/vereadores", {
        apenas_legislatura_atual: true,
        per_page: 1,
      }),
      safeFetchApi<DespesasResumoOut>("/transparencia/despesas/resumo", { ano: 2026 }),
      safeFetchApi<PaginacaoOut<SessaoResumoOut>>("/sessoes", { per_page: 3 }),
      safeFetchApi<PaginacaoOut<DuodecimoOut>>("/transparencia/duodecimo", {
        ano: 2026,
        per_page: 50,
      }),
    ]);

  const health = healthRes.data;
  const despesas = despesasRes.data;
  const sessoes = sessoesRes.data;
  const erroCritico = !health && healthRes.error;

  const coletaNexlegis = health?.ultima_coleta_por_fonte.find(
    (c) => c.fonte_id === "nexlegis",
  )?.ultima_coleta_em;
  const coletaCenti = health?.ultima_coleta_por_fonte.find(
    (c) => c.fonte_id === "transparencia_centi",
  )?.ultima_coleta_em;

  const repassesDuodecimo = (duodecimoRes.data?.items || []).filter(
    (d) => d.tipo_natureza === "RECEITA_REPASSE",
  );
  const totalRepasseDuodecimo = repassesDuodecimo.reduce(
    (acc, cur) => acc + Number(cur.valor || 0),
    0,
  );
  const demografia = DEMOGRAFIA_MUNICIPIOS["inhumas-go"];
  const valorPagoNumerico = parseDecimal(despesas?.totais.valor_pago);
  const despesaPorHabitanteAno =
    valorPagoNumerico !== null && demografia
      ? valorPagoNumerico / demografia.populacaoEstimada2026
      : null;
  const mesesDistintosDuodecimo = new Set(repassesDuodecimo.map((d) => d.mes)).size;
  const mesesApurados = mesesDistintosDuodecimo > 0 ? mesesDistintosDuodecimo : 10;
  const despesaPorHabitanteMes =
    despesaPorHabitanteAno !== null ? despesaPorHabitanteAno / mesesApurados : null;

  return (
    <div className="space-y-10">
      {/* Apresentação do Cerrado Aberto */}
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
            Transparência Legislativa Independente · Inhumas (GO)
          </p>
          <h1 className="mt-2 text-3xl sm:text-4xl font-bold text-[var(--ink)] leading-tight">
            Os dados públicos da Câmara Municipal de Inhumas, explicados com clareza.
          </h1>
          <p className="mt-4 text-base text-[var(--ink-muted)] leading-relaxed">
            O <strong>Cerrado Aberto</strong> organiza e cruza informações oficiais do sistema
            legislativo (Nexlegis) e do Portal da Transparência (CENTI/NúcleoGov). Todo número
            apresentado aqui mostra sua fonte original, a data de coleta e o método de cálculo, sem
            estimativas nem juízo de valor.
          </p>

          {/* Barra de busca rápida cidadã (form nativo GET — IME-safe sem JS extra) */}
          <form
            action="/busca"
            method="GET"
            role="search"
            aria-label="Busca rápida em todo o portal"
            className="mt-5 flex flex-col sm:flex-row gap-2.5 max-w-2xl"
          >
            <label htmlFor="home-busca-rapida" className="sr-only">
              Buscar por assunto, bairro, vereador ou lei
            </label>
            <div className="relative flex-1">
              <Search
                className="w-4 h-4 text-[var(--ink-muted)] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
                aria-hidden="true"
              />
              <input
                id="home-busca-rapida"
                name="q"
                type="search"
                minLength={2}
                required
                placeholder="Busque por assunto, bairro, vereador ou lei (ex.: asfalto, Parque São Jorge, 3577)..."
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] pl-10 pr-4 py-2.5 text-sm text-[var(--ink)] placeholder:text-[var(--ink-muted)]"
              />
            </div>
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--primary)] text-[var(--primary-ink)] px-5 py-2.5 text-sm font-semibold hover:opacity-95 transition-opacity shrink-0"
            >
              <Search className="w-4 h-4" aria-hidden="true" />
              Pesquisar
            </button>
          </form>
        </div>

        {/* Três perguntas do cidadão */}
        <div className="mt-7 grid gap-4 md:grid-cols-3">
          <Link
            href="/vereadores"
            className="group rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 hover:border-[var(--primary)] transition-colors flex flex-col justify-between"
          >
            <div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--primary)]">
                <Users className="w-4 h-4" aria-hidden="true" />
                Representação
              </span>
              <h2 className="mt-2 text-lg font-bold text-[var(--ink)]">
                Quem me representa e o que fez?
              </h2>
              <p className="mt-1 text-sm text-[var(--ink-muted)]">
                Presença em sessões, proposições apresentadas, votos nominais e custo da estrutura
                do mandato.
              </p>
            </div>
            <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] group-hover:underline">
              Ver vereadores <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
          </Link>

          <Link
            href="/despesas"
            className="group rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 hover:border-[var(--primary)] transition-colors flex flex-col justify-between"
          >
            <div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--accent)]">
                <Landmark className="w-4 h-4" aria-hidden="true" />
                Dinheiro público
              </span>
              <h2 className="mt-2 text-lg font-bold text-[var(--ink)]">
                Para onde vai o dinheiro?
              </h2>
              <p className="mt-1 text-sm text-[var(--ink-muted)]">
                Empenhos, liquidações, pagamentos, diárias e repasses do duodécimo em 2026.
              </p>
            </div>
            <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent)] group-hover:underline">
              Explorar despesas <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
          </Link>

          <Link
            href="/sessoes"
            className="group rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 hover:border-[var(--primary)] transition-colors flex flex-col justify-between"
          >
            <div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--primary)]">
                <Calendar className="w-4 h-4" aria-hidden="true" />
                Plenário
              </span>
              <h2 className="mt-2 text-lg font-bold text-[var(--ink)]">
                O que foi discutido e votado?
              </h2>
              <p className="mt-1 text-sm text-[var(--ink-muted)]">
                Sessões plenárias de 2025 e 2026, pautas, lista de presença e placares nominais.
              </p>
            </div>
            <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] group-hover:underline">
              Ver sessões <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
          </Link>
        </div>
      </section>

      {erroCritico && (
        <EstadoErroAPI
          titulo="Serviço de dados temporariamente indisponível"
          mensagem={erroCritico}
        />
      )}

      {/* Indicadores gerais da Câmara */}
      {health && (
        <section aria-labelledby="sec-indicadores" className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="sec-indicadores" className="text-2xl font-bold text-[var(--ink)]">
              Panorama da Câmara Municipal
            </h2>
            <p className="text-xs text-[var(--ink-muted)]">
              Escopo ativo: {health.escopo_dados_ativo}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <DadoComFonte
              titulo="Vereadores (legislatura 2025–2028)"
              valor={
                vereadoresAtuaisRes.data
                  ? formatarInteiro(vereadoresAtuaisRes.data.total)
                  : "Indisponível"
              }
              subtitulo={`${formatarInteiro(health.contagens_persistidas.vereador)} registros históricos catalogados ao todo.`}
              fonteId="nexlegis"
              fonteUrl="https://inhumas.nexlegis.com.br/"
              coletadoEm={coletaNexlegis}
              destaque="primario"
              ausente={!vereadoresAtuaisRes.data}
            />

            <DadoComFonte
              titulo="Sessões realizadas (2025–2026)"
              valor={formatarInteiro(health.contagens_persistidas.sessao)}
              subtitulo={`${formatarInteiro(health.contagens_persistidas.votacao)} votações e ${formatarInteiro(health.contagens_persistidas.pauta_item)} itens de pauta.`}
              fonteId="nexlegis"
              fonteUrl="https://inhumas.nexlegis.com.br/"
              coletadoEm={coletaNexlegis}
            />

            <DadoComFonte
              titulo="Proposições registradas (2025–2026)"
              valor={formatarInteiro(health.contagens_persistidas.proposicao)}
              subtitulo="Inclui projetos, requerimentos, indicações, moções e atas. Atas são excluídas da contagem parlamentar individual."
              fonteId="nexlegis"
              fonteUrl="https://inhumas.nexlegis.com.br/"
              coletadoEm={coletaNexlegis}
            />

            <DadoComFonte
              titulo="Despesas pagas em 2026"
              valor={
                despesas ? formatarBRL(despesas.totais.valor_pago) : "Indisponível"
              }
              subtitulo={
                despesas
                  ? `Empenhado líquido: ${formatarBRL(despesas.totais.valor_empenhado_liquido)} (${despesas.totais.quantidade_empenhos} empenhos).`
                  : "Não foi possível consultar o resumo financeiro."
              }
              fonteId="transparencia_centi"
              fonteUrl={despesas?.fonte_url || "https://acessoainformacao.inhumas.go.leg.br/"}
              coletadoEm={despesas?.ultima_coleta_em || coletaCenti}
              destaque="acento"
              ausente={!despesas}
            />
          </div>

          {/* Barra de transparência financeira complementar */}
          {despesas && (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  <GlossarioTooltip termo="empenho" label="Empenhado líquido (2026)" />
                </p>
                <p className="mt-1 text-lg font-bold tabular-nums">
                  {formatarBRL(despesas.totais.valor_empenhado_liquido)}
                </p>
                <p className="text-xs text-[var(--ink-muted)]">
                  Bruto {formatarBRL(despesas.totais.valor_empenhado_bruto)} − Anulações{" "}
                  {formatarBRL(despesas.totais.valor_anulacao)}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  <GlossarioTooltip termo="liquidacao" label="Liquidado (2026)" />
                </p>
                <p className="mt-1 text-lg font-bold tabular-nums">
                  {formatarBRL(despesas.totais.valor_liquidado)}
                </p>
                <p className="text-xs text-[var(--ink-muted)]">
                  Período de {formatarDataBR(despesas.data_primeiro_empenho)} a{" "}
                  {formatarDataBR(despesas.data_ultimo_empenho)}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  <GlossarioTooltip termo="duodecimo" label="Duodécimo recebido (2026)" />
                </p>
                <p className="mt-1 text-lg font-bold tabular-nums">
                  {repassesDuodecimo.length > 0
                    ? formatarBRL(totalRepasseDuodecimo)
                    : "Não apurado"}
                </p>
                <p className="text-xs text-[var(--ink-muted)]">
                  {repassesDuodecimo.length} repasses mensais registrados no Portal da Transparência
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">
                  Despesa paga por habitante (2026)
                </p>
                <p className="mt-1 text-lg font-bold tabular-nums text-[var(--primary)]">
                  {despesaPorHabitanteMes !== null
                    ? `${formatarBRL(despesaPorHabitanteMes)} / hab. / mês`
                    : "Não apurado"}
                </p>
                <p className="text-xs text-[var(--ink-muted)]">
                  {despesaPorHabitanteAno !== null
                    ? `${formatarBRL(despesaPorHabitanteAno)} por hab. em ${mesesApurados} meses · População IBGE 2026: ${formatarInteiro(demografia.populacaoEstimada2026)} hab.`
                    : "Base demográfica IBGE"}
                </p>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Ferramentas de aprofundamento (Fase 5) */}
      <section aria-labelledby="sec-aprofundamento" className="space-y-4">
        <h2 id="sec-aprofundamento" className="text-2xl font-bold text-[var(--ink)]">
          Explore por bairro, leis, comparativo e dados abertos
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Link
            href="/bairros"
            className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 hover:border-[var(--primary)] transition-colors flex flex-col justify-between"
          >
            <div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--primary)]">
                <MapPin className="w-4 h-4" aria-hidden="true" />
                Território
              </span>
              <h3 className="mt-1.5 text-base font-bold text-[var(--ink)]">Mapa por bairros</h3>
              <p className="mt-1 text-xs text-[var(--ink-muted)] leading-relaxed">
                Veja os pedidos dos vereadores para cada setor, vila ou distrito de Inhumas.
              </p>
            </div>
            <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] group-hover:underline">
              Abrir mapa <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
          </Link>

          <Link
            href="/legislacao"
            className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 hover:border-[var(--primary)] transition-colors flex flex-col justify-between"
          >
            <div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--primary)]">
                <BookOpen className="w-4 h-4" aria-hidden="true" />
                Acervo normativo
              </span>
              <h3 className="mt-1.5 text-base font-bold text-[var(--ink)]">
                Legislação pesquisável
              </h3>
              <p className="mt-1 text-xs text-[var(--ink-muted)] leading-relaxed">
                Pesquise nas leis municipais cadastradas desde 1990 com resumo e link oficial.
              </p>
            </div>
            <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] group-hover:underline">
              Consultar leis <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
          </Link>

          <Link
            href="/comparativo"
            className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 hover:border-[var(--primary)] transition-colors flex flex-col justify-between"
          >
            <div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--primary)]">
                <Scale className="w-4 h-4" aria-hidden="true" />
                SICONFI / Goiás
              </span>
              <h3 className="mt-1.5 text-base font-bold text-[var(--ink)]">
                Comparativo regional
              </h3>
              <p className="mt-1 text-xs text-[var(--ink-muted)] leading-relaxed">
                Inhumas ao lado de 7 municípios goianos de porte semelhante (Tesouro Nacional).
              </p>
            </div>
            <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] group-hover:underline">
              Ver comparativo <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
          </Link>

          <Link
            href="/dados-abertos"
            className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 hover:border-[var(--primary)] transition-colors flex flex-col justify-between"
          >
            <div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--primary)]">
                <Code2 className="w-4 h-4" aria-hidden="true" />
                API &amp; CSV
              </span>
              <h3 className="mt-1.5 text-base font-bold text-[var(--ink)]">API Pública</h3>
              <p className="mt-1 text-xs text-[var(--ink-muted)] leading-relaxed">
                Endpoints JSON abertos, exemplos cURL/Python e planilhas CSV para pesquisa.
              </p>
            </div>
            <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] group-hover:underline">
              Acessar dados <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
          </Link>
        </div>
      </section>

      {/* Últimas sessões disponíveis */}
      {sessoes && sessoes.items.length > 0 && (
        <section aria-labelledby="sec-ultimas-sessoes" className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="sec-ultimas-sessoes" className="text-2xl font-bold text-[var(--ink)]">
              Sessões mais recentes disponíveis
            </h2>
            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/boletins"
                className="text-sm font-semibold text-[var(--accent)] hover:underline inline-flex items-center gap-1"
              >
                Boletim da semana (WhatsApp / Instagram){" "}
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
              <Link
                href="/sessoes"
                className="text-sm font-semibold text-[var(--primary)] hover:underline inline-flex items-center gap-1"
              >
                Ver todas as sessões <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {sessoes.items.map((sessao) => (
              <Link
                key={sessao.sessao_id}
                href={`/sessoes/${sessao.sessao_id}`}
                className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 hover:border-[var(--primary)] transition-colors flex flex-col justify-between gap-3"
              >
                <div>
                  <span className="inline-block rounded-full bg-[var(--surface-alt)] px-2.5 py-0.5 text-xs font-medium text-[var(--ink-muted)]">
                    {sessao.tipo_descricao}
                  </span>
                  <h3 className="mt-2 text-lg font-bold text-[var(--ink)]">
                    {sessao.nome_sessao}
                  </h3>
                  <p className="mt-1 text-sm text-[var(--ink-muted)] tabular-nums">
                    Data: {formatarDataBR(sessao.data_abertura)}
                  </p>
                </div>
                <div className="pt-3 border-t border-[var(--border)] flex flex-wrap gap-3 text-xs text-[var(--ink-muted)] tabular-nums">
                  <span>{sessao.total_presentes} presentes</span>
                  <span>{sessao.total_itens_pauta} itens na pauta</span>
                  <span>{sessao.total_votacoes} votações</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Data da última atualização por fonte e lacunas documentadas */}
      {health && (
        <section aria-labelledby="sec-atualizacao" className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-3">
            <h2 id="sec-atualizacao" className="text-xl font-bold text-[var(--ink)] flex items-center gap-2">
              <FileText className="w-5 h-5 text-[var(--primary)]" aria-hidden="true" />
              Data da última atualização dos dados
            </h2>
            <p className="text-sm text-[var(--ink-muted)]">
              Cada módulo exibe exatamente o momento da última coleta verificada na fonte oficial:
            </p>
            <ul className="divide-y divide-[var(--border)] text-sm">
              {health.ultima_coleta_por_fonte.map((item) => (
                <li
                  key={item.fonte_id}
                  className="py-2.5 flex flex-wrap items-center justify-between gap-2"
                >
                  <span className="font-medium text-[var(--ink)]">
                    {rotuloFonte(item.fonte_id)}
                  </span>
                  <span className="text-xs text-[var(--ink-muted)] tabular-nums">
                    {formatarDataHoraBR(item.ultima_coleta_em)} ({item.documentos_brutos} docs)
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-3">
            <h2 className="text-xl font-bold text-[var(--ink)]">
              Lacunas históricas documentadas
            </h2>
            {health.lacunas_historicas_documentadas.map((lacuna) => (
              <EstadoAusente
                key={lacuna.lacuna_id}
                tom="aviso"
                titulo={`${rotuloFonte(lacuna.fonte_id)} (${formatarDataBR(lacuna.data_inicio_lacuna)} a ${formatarDataBR(lacuna.data_fim_lacuna)})`}
                descricao={`${lacuna.motivo_oficial}${lacuna.pedido_lai_previsto ? " Pedido formal via Lei de Acesso à Informação (LAI) previsto." : ""}`}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
