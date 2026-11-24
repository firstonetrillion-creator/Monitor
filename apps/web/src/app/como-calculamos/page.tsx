import { safeFetchApi } from "@/lib/api";
import type { DeclaracaoTransparenciaOut, HealthOut } from "@/lib/types";
import { formatarDataBR, formatarDataHoraBR, rotuloFonte } from "@/lib/format";
import { EstadoAusente } from "@/components/EstadoAusente";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Como Calculamos",
  description:
    "Metodologia, regras de negócio, proteção LGPD e limitações conhecidas do Cerrado Aberto.",
};

export default async function ComoCalculamosPage() {
  const [healthRes, declRes] = await Promise.all([
    safeFetchApi<HealthOut>("/health"),
    safeFetchApi<DeclaracaoTransparenciaOut[]>("/transparencia/declaracoes"),
  ]);

  const health = healthRes.data;
  const declaracoes = declRes.data || [];

  return (
    <div className="space-y-8 max-w-4xl">
      <header>
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Como calculamos e limitações dos dados
        </h1>
        <p className="mt-2 text-base text-[var(--ink-muted)]">
          Toda regra de cálculo é executada no backend (Python/PostgreSQL) e documentada de forma
          aberta. Não estimamos valores ausentes nem os transformamos em zero.
        </p>
      </header>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-3">
        <h2 className="text-xl font-bold text-[var(--ink)]">
          1. Custo da Estrutura do Mandato (ADR-005)
        </h2>
        <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
          <strong>Fórmula:</strong>{" "}
          <code>Subsídio bruto do vereador + Folha bruta do gabinete + Diárias atribuíveis</code>.
        </p>
        <ul className="list-disc pl-5 text-sm text-[var(--ink-muted)] space-y-1.5">
          <li>
            <strong>Cota parlamentar (CEAP):</strong> inexistente na Câmara Municipal de Inhumas
            conforme declaração oficial (2020–2026).
          </li>
          <li>
            <strong>Lotação da Presidência:</strong> a unidade <code>PRESIDENCIA</code> agrupa
            cargos de assessoria institucional sem lotação apartada de gabinete para o Presidente;
            por isso, a folha do gabinete e o total permanecem <code>NULL</code> (
            <code>LACUNA_PARCIAL_LOTACAO</code>).
          </li>
          <li>
            <strong>Competências em aberto:</strong> meses sem folha publicada (11/2026 e 12/2026)
            permanecem como <code>ABERTA_SEM_PUBLICACAO</code> (<code>NULL</code>).
          </li>
        </ul>
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-3">
        <h2 className="text-xl font-bold text-[var(--ink)]">
          2. Produção legislativa e presença
        </h2>
        <ul className="list-disc pl-5 text-sm text-[var(--ink-muted)] space-y-1.5">
          <li>
            A contagem de proposições parlamentares exclui Atas de Sessão (<code>tipo_id</code> 144
            e 145), Julgamentos de Contas (211), Balanços Gerais (213) e atos exclusivos do
            Executivo.
          </li>
          <li>
            Faltas justificadas e licenças são exibidas separadamente de ausências sem
            justificativa.
          </li>
          <li>
            Todos os vereadores são exibidos em ordem alfabética e com o mesmo tratamento visual,
            sem rankings de desempenho.
          </li>
        </ul>
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-3">
        <h2 className="text-xl font-bold text-[var(--ink)]">
          3. Indicador por habitante — Demografia Oficial IBGE (ADR-006)
        </h2>
        <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
          Para facilitar a compreensão da escala dos gastos legislativos, dividimos a{" "}
          <strong>despesa paga acumulada</strong> em 2026 pela população estimada oficial do{" "}
          <strong>IBGE</strong> para Inhumas/GO (código IBGE <code>5210000</code>):{" "}
          <strong>54.133 habitantes</strong> na Estimativa Populacional 2026 (e{" "}
          <strong>52.204 habitantes</strong> no Censo Demográfico 2022). O valor mensal considera os
          10 meses com execução publicada no exercício (janeiro a outubro de 2026).
        </p>
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-3">
        <h2 className="text-xl font-bold text-[var(--ink)]">
          4. Privacidade e proteção de dados (LGPD)
        </h2>
        <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
          Nenhum CPF completo é armazenado no banco de dados ou retornado pela API. Documentos de
          pessoas físicas (servidores, vereadores e fornecedores PF) são mascarados como{" "}
          <code>***.***.***-**</code> antes da persistência e auditados por testes automatizados.
        </p>
      </section>

      {declaracoes.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-[var(--ink)]">
            4. Declarações oficiais registradas
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

      {health && (
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-3">
          <h2 className="text-xl font-bold text-[var(--ink)]">
            5. Fontes ativas e última coleta verificada
          </h2>
          <ul className="divide-y divide-[var(--border)] text-sm">
            {health.ultima_coleta_por_fonte.map((f) => (
              <li key={f.fonte_id} className="py-2 flex justify-between gap-2">
                <span>{rotuloFonte(f.fonte_id)}</span>
                <span className="tabular-nums text-[var(--ink-muted)]">
                  {formatarDataHoraBR(f.ultima_coleta_em)} ({f.documentos_brutos} documentos)
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
