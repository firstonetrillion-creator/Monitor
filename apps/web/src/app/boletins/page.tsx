import { safeFetchApi } from "@/lib/api";
import type { BoletimSemanalOut } from "@/lib/types";
import { EstadoErroAPI } from "@/components/EstadoAusente";
import { BoletinsClient } from "./BoletinsClient";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Boletim da Semana e Cartões",
  description:
    "Resumos em linguagem simples das sessões da Câmara Municipal de Inhumas, alertas prontos para WhatsApp e cartões PNG para o Instagram Oficial @cerradoaberto.",
};

export default async function BoletinsPage({
  searchParams,
}: {
  searchParams: Promise<{ sessao?: string }>;
}) {
  const { sessao } = await searchParams;
  const res = await safeFetchApi<BoletimSemanalOut>(
    "/boletins/resumo-semanal",
    sessao ? { sessao_id: sessao } : undefined,
  );

  return (
    <div className="space-y-8">
      <header className="max-w-3xl space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Distribuição Cidadã · WhatsApp e Instagram Oficial (@cerradoaberto)
        </p>
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Boletim da Semana e Cartões Compartilháveis
        </h1>
        <p className="text-base text-[var(--ink-muted)] leading-relaxed">
          Resumos em linguagem simples das sessões mais recentes, prontos para encaminhar no{" "}
          <strong>WhatsApp</strong> ou publicar no{" "}
          <strong>Instagram Oficial do Cerrado Aberto (@cerradoaberto)</strong>, sempre com selo de{" "}
          <em>Resumo automático</em>, fonte verificável e data da coleta.
        </p>
      </header>

      {res.error || !res.data ? (
        <EstadoErroAPI
          titulo="Não foi possível montar o boletim da semana"
          mensagem={res.error || "Boletim indisponível no momento."}
        />
      ) : (
        <BoletinsClient initialBoletim={res.data} />
      )}
    </div>
  );
}
