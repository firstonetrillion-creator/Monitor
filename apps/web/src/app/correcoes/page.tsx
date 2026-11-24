import Link from "next/link";
import { CheckCircle2, Mail, ShieldAlert } from "lucide-react";

export const metadata = {
  title: "Canal de Correção e Direito de Resposta",
  description:
    "Como solicitar correções factuais, enviar esclarecimentos oficiais e consultar o histórico público de retificações do Cerrado Aberto.",
};

const EMAIL_CORRECOES = "firstonetrillion@gmail.com";
const MAILTO_HREF = `mailto:${EMAIL_CORRECOES}?subject=${encodeURIComponent(
  "Solicitação de correção — Cerrado Aberto",
)}&body=${encodeURIComponent(
  "1. Página ou endereço (URL) onde o dado aparece:\n\n2. O que está divergente da fonte oficial:\n\n3. Link ou documento oficial de referência:\n\n4. Nome e vínculo do solicitante (opcional):\n",
)}`;

interface RegistroCorrecao {
  data: string;
  escopo: string;
  descricao: string;
  situacao: string;
}

const HISTORICO_CORRECOES: RegistroCorrecao[] = [
  {
    data: "13/11/2026",
    escopo: "Lançamento da versão de homologação (MVP)",
    descricao:
      "Publicação inicial dos dados de 2025–2026 do Nexlegis e do exercício de 2026 do Portal da Transparência CENTI/NúcleoGov. Nenhuma retificação de dado reportada até o momento.",
    situacao: "Base original verificada",
  },
];

export default function CorrecoesPage() {
  return (
    <div className="space-y-8 max-w-4xl">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Compromisso Editorial · Direito de Resposta
        </p>
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Canal de correção e esclarecimentos
        </h1>
        <p className="text-base text-[var(--ink-muted)] leading-relaxed">
          O <strong>Cerrado Aberto</strong> trabalha exclusivamente com dados públicos oficiais. Se
          você encontrou um número desatualizado, erro de transcrição ou deseja enviar um
          esclarecimento documental (como cidadão, servidor ou agente público), utilize o canal
          abaixo.
        </p>
      </header>

      {/* Cartão de envio por e-mail */}
      <section
        aria-labelledby="sec-como-solicitar"
        className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-4"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <h2 id="sec-como-solicitar" className="text-xl font-bold text-[var(--ink)]">
              Enviar solicitação de correção ou nota oficial
            </h2>
            <p className="text-sm text-[var(--ink-muted)]">
              Durante a fase de homologação (beta fechado), as solicitações são recebidas por e-mail
              sem necessidade de cadastro.
            </p>
          </div>
          <a
            href={MAILTO_HREF}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2.5 text-sm font-semibold text-[var(--primary-ink)] hover:opacity-90 transition-opacity"
          >
            <Mail className="w-4 h-4" aria-hidden="true" />
            Escrever para {EMAIL_CORRECOES}
          </a>
        </div>

        <div className="rounded-xl bg-[var(--surface-alt)] p-4 text-sm text-[var(--ink)] space-y-2">
          <p className="font-semibold">O que incluir na mensagem para agilizar a verificação:</p>
          <ol className="list-decimal pl-5 space-y-1 text-[var(--ink-muted)]">
            <li>
              <strong>Endereço da página (URL)</strong> onde o número ou texto aparece no Cerrado
              Aberto;
            </li>
            <li>
              <strong>Descrição objetiva da divergência</strong> (qual valor ou informação está
              diferente do registro oficial);
            </li>
            <li>
              <strong>Fonte ou documento público de comprovação</strong> (link do Portal da
              Transparência, Nexlegis, Diário Oficial ou PDF de portaria/empenho).
            </li>
          </ol>
          <p className="text-xs text-[var(--ink-muted)] pt-1">
            E-mail de atendimento (provisório de homologação):{" "}
            <code className="font-mono font-semibold text-[var(--ink)]">{EMAIL_CORRECOES}</code>
          </p>
        </div>
      </section>

      {/* Protocolo de análise e SLA */}
      <section
        aria-labelledby="sec-protocolo"
        className="grid gap-4 sm:grid-cols-2"
      >
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-2">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase text-[var(--primary)]">
            <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
            Quando há erro nosso ou atualização na fonte
          </p>
          <h2 id="sec-protocolo" className="text-lg font-bold text-[var(--ink)]">
            Retificação com registro público
          </h2>
          <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
            Se houve falha de coleta, classificação ou atualização posterior no portal oficial,
            corrigimos o dado, mantemos o histórico da versão anterior e registramos a retificação
            na tabela pública abaixo.
          </p>
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-2">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase text-[var(--accent)]">
            <ShieldAlert className="w-4 h-4" aria-hidden="true" />
            Quando o dado reflete exatamente a fonte oficial
          </p>
          <h2 className="text-lg font-bold text-[var(--ink)]">
            Direito de esclarecimento e contexto
          </h2>
          <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
            Se o número exibido corresponde ao que foi publicado pela Câmara Municipal, mantemos o
            registro fiel à fonte e anexamos a nota ou esclarecimento enviado pelo agente público ou
            órgão responsável junto ao indicador.
          </p>
        </div>
      </section>

      {/* Registro público de correções */}
      <section
        aria-labelledby="sec-historico-correcoes"
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 space-y-4"
      >
        <div>
          <h2 id="sec-historico-correcoes" className="text-xl font-bold text-[var(--ink)]">
            Registro público de correções realizadas
          </h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Todas as correções materiais aplicadas após a publicação de cada versão ficam listadas
            abaixo com data e descrição.
          </p>
        </div>

        <div
          className="overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Histórico cronológico de correções e retificações aplicadas"
        >
          <table className="w-full text-left text-sm border-collapse min-w-[600px]">
            <caption className="sr-only">
              Histórico cronológico de correções e retificações aplicadas no Cerrado Aberto
            </caption>
            <thead className="sticky top-0 bg-[var(--surface)] z-10">
              <tr className="border-b border-[var(--border)] text-xs uppercase text-[var(--ink-muted)]">
                <th scope="col" className="py-2 pr-4">
                  Data
                </th>
                <th scope="col" className="py-2 pr-4">
                  Página / Escopo
                </th>
                <th scope="col" className="py-2 pr-4">
                  O que foi verificado ou corrigido
                </th>
                <th scope="col" className="py-2">
                  Situação
                </th>
              </tr>
            </thead>
            <tbody>
              {HISTORICO_CORRECOES.map((item, idx) => (
                <tr key={idx} className="border-b border-[var(--border)]/60 align-top">
                  <td className="py-3 pr-4 tabular-nums whitespace-nowrap font-medium">
                    {item.data}
                  </td>
                  <td className="py-3 pr-4 font-semibold text-[var(--ink)]">{item.escopo}</td>
                  <td className="py-3 pr-4 text-[var(--ink-muted)] leading-relaxed">
                    {item.descricao}
                  </td>
                  <td className="py-3 whitespace-nowrap">
                    <span className="inline-block rounded-full bg-[var(--status-ok-bg)] text-[var(--status-ok-ink)] px-2.5 py-0.5 text-xs font-semibold">
                      {item.situacao}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-[var(--ink-muted)]">
          Quer entender a fórmula de algum indicador antes de solicitar revisão? Consulte{" "}
          <Link href="/como-calculamos" className="underline hover:text-[var(--primary)]">
            Como calculamos
          </Link>{" "}
          e{" "}
          <Link href="/cobertura-e-limitacoes" className="underline hover:text-[var(--primary)]">
            Cobertura e limitações
          </Link>
          .
        </p>
      </section>
    </div>
  );
}
