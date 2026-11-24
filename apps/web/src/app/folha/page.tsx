import type { Metadata } from "next";
import { safeFetchApi } from "@/lib/api";
import type { FolhaPagamentoOut, PaginacaoOut, VereadorResumoOut } from "@/lib/types";
import { EstadoAusente, EstadoErroAPI } from "@/components/EstadoAusente";
import { FolhaClient } from "./FolhaClient";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Folha de Pagamento e Lotação",
  description:
    "Consulta nominal da folha de pagamento, subsídios e lotação por gabinete ou setor da Câmara Municipal de Inhumas (2026), com proteção LGPD.",
};

interface FolhaSearchParams {
  mes?: string;
  gabinete_vereador_id?: string;
  vereador_id?: string;
  apenas_vereadores?: string;
  q?: string;
  page?: string;
}

export default async function FolhaPage({
  searchParams,
}: {
  searchParams: Promise<FolhaSearchParams>;
}) {
  const sp = await searchParams;
  const mesParam = sp.mes !== undefined ? Number(sp.mes) : 10;
  const mesInicial = Number.isFinite(mesParam) && mesParam >= 1 && mesParam <= 12 ? mesParam : undefined;
  const mesSelecionadoInicial = sp.mes === "0" ? 0 : (mesInicial ?? 10);
  const pageInicial = sp.page && Number(sp.page) >= 1 ? Number(sp.page) : 1;
  const apenasVereadoresInicial = sp.apenas_vereadores === "true";

  const [folhaRes, vereadoresRes] = await Promise.all([
    safeFetchApi<PaginacaoOut<FolhaPagamentoOut>>("/transparencia/folha", {
      ano: 2026,
      mes: mesSelecionadoInicial === 0 ? undefined : mesSelecionadoInicial,
      gabinete_vereador_id: sp.gabinete_vereador_id || undefined,
      vereador_id: sp.vereador_id || undefined,
      apenas_vereadores: apenasVereadoresInicial ? true : undefined,
      q: sp.q?.trim() || undefined,
      page: pageInicial,
      per_page: 20,
    }),
    safeFetchApi<PaginacaoOut<VereadorResumoOut>>("/vereadores", {
      apenas_legislatura_atual: true,
      per_page: 50,
    }),
  ]);

  const vereadoresOrdenados = [...(vereadoresRes.data?.items || [])].sort((a, b) =>
    a.nome_exibicao.localeCompare(b.nome_exibicao, "pt-BR"),
  );

  return (
    <div className="space-y-6">
      <header className="max-w-3xl space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
          Transparência de Pessoal · Exercício 2026
        </p>
        <h1 className="text-3xl font-bold text-[var(--ink)]">
          Folha de Pagamento e Lotação (2026)
        </h1>
        <p className="text-base text-[var(--ink-muted)] leading-relaxed">
          Registros nominais mensais da Câmara Municipal de Inhumas (vereadores, comissionados e
          efetivos) publicados no Portal da Transparência CENTI/NúcleoGov, com vínculo por gabinete
          ou unidade administrativa.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <EstadoAusente
          titulo="Proteção de dados pessoais (LGPD) e escopo contábil"
          descricao="Nenhum CPF completo é armazenado ou exibido (sempre mascarado como ***.***.***-**). Os valores referem-se à remuneração bruta publicada na folha (proventos), que não se confunde com custo patronal total."
        />
        <EstadoAusente
          tom="aviso"
          titulo="Competências em aberto e lotação da Presidência"
          descricao="As competências 11/2026 e 12/2026 ainda não possuem folha publicada (permanecem NULL). Servidores da unidade PRESIDENCIA reúnem assessoria institucional e administrativa sem lotação separada por gabinete."
        />
      </div>

      {folhaRes.error || !folhaRes.data ? (
        <EstadoErroAPI
          mensagem={folhaRes.error || "Não foi possível carregar os registros da folha de pagamento."}
        />
      ) : (
        <FolhaClient
          initialData={folhaRes.data}
          vereadores={vereadoresOrdenados}
          initialFilters={{
            mes: mesSelecionadoInicial,
            gabineteVereadorId: sp.gabinete_vereador_id || "",
            apenasVereadores: apenasVereadoresInicial,
            q: sp.q || "",
          }}
        />
      )}
    </div>
  );
}
