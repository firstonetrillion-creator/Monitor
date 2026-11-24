/**
 * Utilitário de geração e download de CSV (UTF-8 com BOM para compatibilidade com planilhas em PT-BR).
 * Preserva valores ausentes (null/undefined) como texto explícito ("NULL"), nunca convertendo em zero.
 */

export function escaparCelulaCsv(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined) {
    return '"NULL"';
  }
  const texto = String(valor).replace(/"/g, '""');
  return `"${texto}"`;
}

export function gerarConteudoCsv(
  cabecalhos: readonly string[],
  linhas: ReadonlyArray<ReadonlyArray<string | number | null | undefined>>,
): string {
  const linhaCabecalho = cabecalhos.map((c) => escaparCelulaCsv(c)).join(";");
  const linhasCorpo = linhas.map((linha) =>
    linha.map((celula) => escaparCelulaCsv(celula)).join(";"),
  );
  return `\uFEFF${[linhaCabecalho, ...linhasCorpo].join("\r\n")}\r\n`;
}

export function baixarCsvNoNavegador(
  nomeArquivo: string,
  cabecalhos: readonly string[],
  linhas: ReadonlyArray<ReadonlyArray<string | number | null | undefined>>,
): void {
  if (typeof window === "undefined") {
    return;
  }
  const conteudo = gerarConteudoCsv(cabecalhos, linhas);
  const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo.endsWith(".csv") ? nomeArquivo : `${nomeArquivo}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
