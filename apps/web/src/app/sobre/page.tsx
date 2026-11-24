import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export const metadata = {
  title: "Sobre o Cerrado Aberto",
  description:
    "Declaração de independência, missão cidadã, princípios editoriais e fontes oficiais monitoradas pelo Cerrado Aberto em Inhumas (GO).",
};

export default function SobrePage() {
  return (
    <div className="space-y-8 max-w-4xl">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Iniciativa Cidadã Independente · Inhumas (GO)
        </p>
        <h1 className="text-3xl font-bold text-[var(--ink)]">Sobre o Cerrado Aberto</h1>
        <p className="text-base text-[var(--ink-muted)] leading-relaxed">
          O <strong>Cerrado Aberto</strong> transforma os dados públicos do Legislativo municipal de
          Inhumas (GO) — originalmente distribuídos em diferentes sistemas técnicos e contábeis — em
          informação clara, contextualizada e verificável para qualquer cidadão, jornalista ou
          pesquisador.
        </p>
      </header>

      {/* Declaração de independência */}
      <section
        aria-labelledby="sec-independencia"
        className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-3"
      >
        <div className="flex items-center gap-2 text-[var(--primary)]">
          <ShieldCheck className="w-5 h-5 shrink-0" aria-hidden="true" />
          <h2 id="sec-independencia" className="text-xl font-bold text-[var(--ink)]">
            Declaração de independência
          </h2>
        </div>
        <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
          O <strong>Cerrado Aberto</strong> é uma iniciativa cidadã independente de monitoramento,
          tradução e interpretação de dados públicos, <strong>sem qualquer vínculo institucional,
          contratual, financeiro ou político-partidário</strong> com a Câmara Municipal de Inhumas,
          com a Prefeitura ou com qualquer agente público.
        </p>
        <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
          Nosso trabalho está amparado pela Constituição Federal (art. 5º, XIV e XXXIII, e art. 37)
          e pela Lei de Acesso à Informação (Lei Federal nº 12.527/2011), utilizando exclusivamente
          dados de interesse coletivo publicados em fontes oficiais.
        </p>
      </section>

      {/* Princípios inegociáveis */}
      <section
        aria-labelledby="sec-principios"
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-4"
      >
        <h2 id="sec-principios" className="text-xl font-bold text-[var(--ink)]">
          Princípios que guiam a plataforma
        </h2>
        <ul className="grid gap-4 sm:grid-cols-2 text-sm text-[var(--ink-muted)]">
          <li className="rounded-lg bg-[var(--surface-alt)] p-4">
            <strong className="block text-[var(--ink)] mb-1">1. Proveniência em tudo</strong>
            Todo número exibe a fonte oficial, a data exata da coleta e o link para o método de
            cálculo.
          </li>
          <li className="rounded-lg bg-[var(--surface-alt)] p-4">
            <strong className="block text-[var(--ink)] mb-1">2. Fatos, não veredictos</strong>
            Apresentamos dados objetivos e contexto metodológico. Não fazemos rankings punitivos nem
            usamos adjetivos opinativos.
          </li>
          <li className="rounded-lg bg-[var(--surface-alt)] p-4">
            <strong className="block text-[var(--ink)] mb-1">
              3. Dado ausente nunca vira zero
            </strong>
            Quando uma informação não está publicada para determinado período ou unidade, exibimos o
            estado real de ausência, sem inventar ou estimar valores.
          </li>
          <li className="rounded-lg bg-[var(--surface-alt)] p-4">
            <strong className="block text-[var(--ink)] mb-1">4. Proteção de dados (LGPD)</strong>
            Não armazenamos nem exibimos CPF completo, endereço residencial ou qualquer dado pessoal
            desnecessário ao controle social.
          </li>
        </ul>
      </section>

      {/* Contato e correções */}
      <section
        aria-labelledby="sec-contato"
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-3"
      >
        <h2 id="sec-contato" className="text-xl font-bold text-[var(--ink)]">
          Contato e canal de correção
        </h2>
        <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
          Para apontar divergências materiais, enviar documentos públicos complementares ou exercer
          direito de esclarecimento, acesse o{" "}
          <Link href="/correcoes" className="underline font-semibold text-[var(--primary)]">
            Canal de correção
          </Link>{" "}
          ou envie mensagem diretamente para{" "}
          <a
            href="mailto:firstonetrillion@gmail.com"
            className="underline font-semibold text-[var(--primary)]"
          >
            firstonetrillion@gmail.com
          </a>
          . Acompanhe também os boletins semanais em{" "}
          <Link href="/boletins" className="underline font-semibold text-[var(--primary)]">
            Boletim da Semana
          </Link>{" "}
          e no{" "}
          <a
            href="https://www.instagram.com/cerradoaberto/"
            target="_blank"
            rel="noopener noreferrer"
            className="underline font-semibold text-[var(--primary)]"
          >
            Instagram Oficial do Cerrado Aberto (@cerradoaberto)
          </a>
          .
        </p>
      </section>
    </div>
  );
}
