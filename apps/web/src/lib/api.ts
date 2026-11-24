import type {
  BairroDetalheOut,
  BairrosPainelOut,
  BoletimSemanalOut,
  BuscaUnificadaOut,
  ComparativoSiconfiOut,
  CustoMandatoMensalOut,
  DeclaracaoTransparenciaOut,
  DespesaEmpenhoOut,
  DespesasResumoOut,
  DiariaOut,
  DuodecimoOut,
  HealthOut,
  MateriaDetalheOut,
  MateriaResumoOut,
  NormaDetalheOut,
  NormasListagemOut,
  PaginacaoOut,
  SessaoDetalheOut,
  SessaoResumoOut,
  VereadorDetalheOut,
  VereadorResumoOut,
} from "./types";

export class ApiFetchError extends Error {
  status: number;

  constructor(message: string, status = 502) {
    super(message);
    this.name = "ApiFetchError";
    this.status = status;
  }
}

export type QueryValue = string | number | boolean | null | undefined;

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const isServer = typeof window === "undefined";
  const base = isServer
    ? (process.env.CERRADO_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "")
    : "";
  const urlPath = `${base}/api/v1${path.startsWith("/") ? path : `/${path}`}`;

  if (!params) {
    return urlPath;
  }
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `${urlPath}?${qs}` : urlPath;
}

export async function fetchApi<T>(
  path: string,
  params?: Record<string, QueryValue>,
): Promise<T> {
  const url = buildUrl(path, params);
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch {
    throw new ApiFetchError(
      "Não foi possível conectar ao serviço de dados do Cerrado Aberto.",
      502,
    );
  }

  if (!response.ok) {
    let detail = `Erro ao consultar a API (HTTP ${response.status}).`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      // mantém mensagem padrão
    }
    throw new ApiFetchError(detail, response.status);
  }

  return (await response.json()) as T;
}

export async function safeFetchApi<T>(
  path: string,
  params?: Record<string, QueryValue>,
): Promise<{ data: T | null; error: string | null; status: number | null }> {
  try {
    const data = await fetchApi<T>(path, params);
    return { data, error: null, status: 200 };
  } catch (err) {
    if (err instanceof ApiFetchError) {
      return { data: null, error: err.message, status: err.status };
    }
    return {
      data: null,
      error: "Erro inesperado ao carregar os dados.",
      status: 500,
    };
  }
}

export const api = {
  health: () => fetchApi<HealthOut>("/health"),
  vereadores: (params?: {
    page?: number;
    per_page?: number;
    q?: string;
    partido?: string;
    condicao?: string;
    apenas_legislatura_atual?: boolean;
  }) => fetchApi<PaginacaoOut<VereadorResumoOut>>("/vereadores", params),
  vereador: (id: string) =>
    fetchApi<VereadorDetalheOut>(`/vereadores/${encodeURIComponent(id)}`),
  sessoes: (params?: {
    page?: number;
    per_page?: number;
    ano?: number;
    tipo_id?: number;
    data_inicio?: string;
    data_fim?: string;
    q?: string;
  }) => fetchApi<PaginacaoOut<SessaoResumoOut>>("/sessoes", params),
  sessao: (id: string) =>
    fetchApi<SessaoDetalheOut>(`/sessoes/${encodeURIComponent(id)}`),
  materias: (params?: {
    page?: number;
    per_page?: number;
    ano?: number;
    tipo_id?: number;
    eh_proposicao_parlamentar?: boolean;
    vereador_id?: string;
    q?: string;
  }) => fetchApi<PaginacaoOut<MateriaResumoOut>>("/materias", params),
  materia: (id: string) =>
    fetchApi<MateriaDetalheOut>(`/materias/${encodeURIComponent(id)}`),
  custoMandato: (params?: {
    page?: number;
    per_page?: number;
    ano?: number;
    mes?: number;
    vereador_id?: string;
    status_competencia?: string;
  }) => fetchApi<PaginacaoOut<CustoMandatoMensalOut>>("/transparencia/custo-mandato", params),
  despesas: (params?: {
    page?: number;
    per_page?: number;
    ano?: number;
    mes?: number;
    eh_diaria?: boolean;
    q?: string;
    data_inicio?: string;
    data_fim?: string;
    fornecedor_id?: string;
    elemento_despesa?: string;
  }) => fetchApi<PaginacaoOut<DespesaEmpenhoOut>>("/transparencia/despesas", params),
  despesasResumo: (params?: {
    ano?: number;
    mes?: number;
    eh_diaria?: boolean;
    q?: string;
    data_inicio?: string;
    data_fim?: string;
    fornecedor_id?: string;
    elemento_despesa?: string;
  }) => fetchApi<DespesasResumoOut>("/transparencia/despesas/resumo", params),
  diarias: (params?: {
    page?: number;
    per_page?: number;
    ano?: number;
    vereador_id?: string;
  }) => fetchApi<PaginacaoOut<DiariaOut>>("/transparencia/diarias", params),
  duodecimo: (params?: { page?: number; per_page?: number; ano?: number }) =>
    fetchApi<PaginacaoOut<DuodecimoOut>>("/transparencia/duodecimo", params),
  declaracoes: () =>
    fetchApi<DeclaracaoTransparenciaOut[]>("/transparencia/declaracoes"),
  boletimSemanal: (params?: { sessao_id?: string }) =>
    fetchApi<BoletimSemanalOut>("/boletins/resumo-semanal", params),
  busca: (params: {
    q: string;
    categoria?: string;
    ano?: number;
    page?: number;
    per_page?: number;
  }) => fetchApi<BuscaUnificadaOut>("/busca", params),
  bairros: (params?: { ano?: number; tema?: string; vereador_id?: string }) =>
    fetchApi<BairrosPainelOut>("/bairros", params),
  bairro: (
    slug: string,
    params?: { ano?: number; tema?: string; page?: number; per_page?: number },
  ) => fetchApi<BairroDetalheOut>(`/bairros/${encodeURIComponent(slug)}`, params),
  legislacao: (params?: {
    q?: string;
    ano?: number;
    categoria?: string;
    page?: number;
    per_page?: number;
  }) => fetchApi<NormasListagemOut>("/legislacao", params),
  norma: (id: string) =>
    fetchApi<NormaDetalheOut>(`/legislacao/${encodeURIComponent(id)}`),
  comparativo: (params?: { ano?: number }) =>
    fetchApi<ComparativoSiconfiOut>("/comparativo", params),
};
