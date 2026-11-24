/** Utilitários de formatação PT-BR sem jamais converter dado ausente (null/undefined) em zero. */

const brlFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const intFormatter = new Intl.NumberFormat("pt-BR");

const MESES_CURTOS = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

const MESES_LONGOS = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

export function parseDecimal(valor: string | number | null | undefined): number | null {
  if (valor === null || valor === undefined || valor === "") {
    return null;
  }
  const n = typeof valor === "number" ? valor : Number(valor);
  return Number.isFinite(n) ? n : null;
}

export function formatarBRL(
  valor: string | number | null | undefined,
  rotuloAusente = "Não apurado",
): string {
  const num = parseDecimal(valor);
  if (num === null) {
    return rotuloAusente;
  }
  return brlFormatter.format(num);
}

export function formatarInteiro(
  valor: number | null | undefined,
  rotuloAusente = "Não informado",
): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return rotuloAusente;
  }
  return intFormatter.format(valor);
}

export function formatarDataBR(iso: string | null | undefined, rotuloAusente = "—"): string {
  if (!iso) {
    return rotuloAusente;
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (match) {
    return `${match[3]}/${match[2]}/${match[1]}`;
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export function formatarDataHoraBR(iso: string | null | undefined, rotuloAusente = "—"): string {
  if (!iso) {
    return rotuloAusente;
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function nomeMesCurto(mes: number): string {
  return MESES_CURTOS[mes - 1] || String(mes);
}

export function nomeMesLongo(mes: number): string {
  return MESES_LONGOS[mes - 1] || String(mes);
}

export function formatarDocumentoFavorecido(
  documento: string | null | undefined,
  tipoPessoa: string | null | undefined,
): string {
  if (!documento) {
    return "Não informado";
  }
  if (tipoPessoa === "PESSOA_FISICA" || documento.includes("*")) {
    return "***.***.***-** (CPF protegido pela LGPD)";
  }
  const digits = documento.replace(/\D/g, "");
  if (digits.length === 14) {
    return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
  }
  return documento;
}

export function obterIniciais(nome: string): string {
  const partes = nome
    .replace(/\b(DR\.?|DRA\.?|PROF\.?|PR\.?)\b/gi, "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (partes.length === 0) {
    return "CA";
  }
  if (partes.length === 1) {
    return partes[0].slice(0, 2).toUpperCase();
  }
  return `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

export interface ConfigDemograficaMunicipio {
  municipioId: string;
  nomeMunicipio: string;
  uf: string;
  codigoIbge: string;
  populacaoEstimada2026: number;
  populacaoCenso2022: number;
  fonteUrl: string;
}

export const DEMOGRAFIA_MUNICIPIOS: Record<string, ConfigDemograficaMunicipio> = {
  "inhumas-go": {
    municipioId: "inhumas-go",
    nomeMunicipio: "Inhumas",
    uf: "GO",
    codigoIbge: "5210000",
    populacaoEstimada2026: 54133,
    populacaoCenso2022: 52204,
    fonteUrl: "https://cidades.ibge.gov.br/brasil/go/inhumas/panorama",
  },
};

export function rotuloFonte(fonteId: string): string {
  const mapa: Record<string, string> = {
    nexlegis: "Sistema Legislativo Nexlegis (Câmara de Inhumas)",
    transparencia_centi: "Portal da Transparência CENTI (Câmara de Inhumas)",
    transparencia_nucleogov: "Portal da Transparência NúcleoGov (Câmara de Inhumas)",
    legislacao_nucleogov: "Portal de Legislação NúcleoGov (Câmara de Inhumas)",
    siconfi_stn: "SICONFI — Secretaria do Tesouro Nacional (Ministério da Fazenda)",
    ibge_cidades: "IBGE Cidades (Estimativa Populacional 2026 / Censo 2022)",
  };
  return mapa[fonteId] || fonteId;
}

export function rotuloCompetenciaStatus(status: string): {
  texto: string;
  tom: "ok" | "aviso" | "neutro";
} {
  if (status === "FECHADA") {
    return { texto: "Competência fechada", tom: "ok" };
  }
  if (status === "LACUNA_PARCIAL_LOTACAO") {
    return { texto: "Lacuna parcial de lotação (Presidência)", tom: "aviso" };
  }
  if (status === "ABERTA_SEM_PUBLICACAO") {
    return { texto: "Em aberto / sem folha publicada", tom: "neutro" };
  }
  return { texto: status, tom: "neutro" };
}
