/**
 * Gerador client-side de cartões PNG em alta resolução para o Instagram Oficial (@cerradoaberto)
 * e Status do WhatsApp — 100% local via Canvas 2D (sem APIs pagas nem serviços externos).
 */

import type { BoletimSemanalOut, SlideInstagramOut } from "./types";

const PALETA = {
  fundo: "#FAF7F2",
  superficie: "#FFFFFF",
  superficieAlt: "#F2ECE1",
  primaria: "#1F4E3D",
  acento: "#B44B2A",
  destaque: "#D99B16",
  texto: "#1F2421",
  textoSuave: "#4F5B54",
  borda: "#DDD5C7",
};

function truncarPalavras(texto: string, limite: number): string {
  const limpo = texto.replace(/\s+/g, " ").trim();
  if (limpo.length <= limite) {
    return limpo;
  }
  const corteBruto = limpo.slice(0, Math.max(1, limite - 1));
  const ultimoEspaco = corteBruto.lastIndexOf(" ");
  const base = ultimoEspaco > 0 ? corteBruto.slice(0, ultimoEspaco) : corteBruto;
  return `${base.replace(/[.,;:—–\-"'\s]+$/, "")}…`;
}

function quebrarLinhas(
  ctx: CanvasRenderingContext2D,
  texto: string,
  larguraMax: number,
  maxLinhas = 4,
): string[] {
  const palavras = texto.split(/\s+/).filter(Boolean);
  const linhas: string[] = [];
  let atual = "";
  let truncou = false;

  for (let i = 0; i < palavras.length; i += 1) {
    const palavra = palavras[i];
    const tentativa = atual ? `${atual} ${palavra}` : palavra;
    if (ctx.measureText(tentativa).width <= larguraMax) {
      atual = tentativa;
      continue;
    }
    if (linhas.length === maxLinhas - 1) {
      truncou = true;
      break;
    }
    if (atual) {
      linhas.push(atual);
    }
    atual = palavra;
  }
  if (atual && linhas.length < maxLinhas) {
    linhas.push(atual);
  }
  if (truncou && linhas.length > 0) {
    const idx = linhas.length - 1;
    let ultima = linhas[idx].replace(/[.,;:—–\-"'\s]+$/, "");
    while (ultima.length > 1 && ctx.measureText(`${ultima}…`).width > larguraMax) {
      const espaco = ultima.lastIndexOf(" ");
      ultima = espaco > 0 ? ultima.slice(0, espaco) : ultima.slice(0, -1);
    }
    linhas[idx] = `${ultima.replace(/[.,;:—–\-"'\s]+$/, "")}…`;
  }
  return linhas;
}

function desenharRetanguloArredondado(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export function renderizarSlideParaDataUrl(
  slide: SlideInstagramOut,
  totalSlides: number,
  formato: "feed" | "story" = "feed",
): string {
  const largura = 1080;
  const altura = formato === "story" ? 1920 : 1350;
  const canvas = document.createElement("canvas");
  canvas.width = largura;
  canvas.height = altura;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Contexto Canvas 2D indisponível neste navegador.");
  }

  // 1. Fundo off-white quente do cerrado
  ctx.fillStyle = PALETA.fundo;
  ctx.fillRect(0, 0, largura, altura);

  // 2. Faixa superior verde-cerrado (declaração de independência editorial)
  const alturaFaixa = formato === "story" ? 132 : 104;
  ctx.fillStyle = PALETA.primaria;
  ctx.fillRect(0, 0, largura, alturaFaixa);

  ctx.fillStyle = "#FAF7F2";
  ctx.font = "700 30px Georgia, serif";
  ctx.fillText("Cerrado Aberto", 64, formato === "story" ? 68 : 56);

  ctx.fillStyle = "#E5DDD0";
  ctx.font = "500 20px system-ui, -apple-system, sans-serif";
  ctx.fillText(
    "Iniciativa cidadã independente · Inhumas (GO)",
    64,
    formato === "story" ? 104 : 84,
  );

  // Badge numérica do carrossel (ex.: 1/3)
  if (formato === "feed") {
    ctx.fillStyle = "rgba(255,255,255,0.18)";
    desenharRetanguloArredondado(ctx, largura - 170, 28, 106, 48, 24);
    ctx.fill();
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "700 22px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${slide.numero}/${totalSlides}`, largura - 117, 60);
    ctx.textAlign = "left";
  }

  // 3. Linha de destaque amarelo-ipê
  ctx.fillStyle = PALETA.destaque;
  ctx.fillRect(0, alturaFaixa, largura, 10);

  // 4. Etiqueta e Título principal
  let cursorY = alturaFaixa + (formato === "story" ? 120 : 88);
  ctx.fillStyle = slide.numero === 3 ? PALETA.acento : PALETA.primaria;
  ctx.font = "700 24px system-ui, sans-serif";
  ctx.fillText(slide.etiqueta, 64, cursorY);

  cursorY += 68;
  ctx.fillStyle = PALETA.texto;
  ctx.font = formato === "story" ? "700 66px Georgia, serif" : "700 58px Georgia, serif";
  const linhasTitulo = quebrarLinhas(ctx, slide.titulo, largura - 128, 3);
  for (const linha of linhasTitulo) {
    ctx.fillText(linha, 64, cursorY);
    cursorY += formato === "story" ? 78 : 68;
  }

  cursorY += 12;
  ctx.fillStyle = PALETA.textoSuave;
  ctx.font = "400 28px system-ui, sans-serif";
  const linhasSub = quebrarLinhas(ctx, slide.subtitulo, largura - 128, 2);
  for (const linha of linhasSub) {
    ctx.fillText(linha, 64, cursorY);
    cursorY += 38;
  }

  // 5. Cartões dos itens factuais
  cursorY += formato === "story" ? 56 : 36;
  const alturaItem = formato === "story" ? 168 : 132;
  const espacoItem = formato === "story" ? 28 : 22;

  for (const itemTexto of slide.itens.slice(0, 4)) {
    ctx.fillStyle = PALETA.superficie;
    ctx.strokeStyle = PALETA.borda;
    ctx.lineWidth = 2;
    desenharRetanguloArredondado(ctx, 64, cursorY, largura - 128, alturaItem, 20);
    ctx.fill();
    ctx.stroke();

    // Barra lateral colorida
    ctx.fillStyle = slide.numero === 3 ? PALETA.acento : PALETA.primaria;
    desenharRetanguloArredondado(ctx, 64, cursorY, 12, alturaItem, 6);
    ctx.fill();

    ctx.fillStyle = PALETA.texto;
    ctx.font = "600 28px system-ui, sans-serif";
    const linhasItem = quebrarLinhas(ctx, itemTexto, largura - 196, 3);
    let itemTextY = cursorY + (linhasItem.length === 1 ? alturaItem / 2 + 10 : 48);
    for (const l of linhasItem) {
      ctx.fillText(l, 102, itemTextY);
      itemTextY += 36;
    }

    cursorY += alturaItem + espacoItem;
  }

  // 6. Rodapé de transparência, fonte, coleta e @cerradoaberto
  const rodapeY = altura - (formato === "story" ? 210 : 148);
  ctx.fillStyle = PALETA.superficieAlt;
  ctx.fillRect(0, rodapeY, largura, altura - rodapeY);
  ctx.fillStyle = PALETA.borda;
  ctx.fillRect(0, rodapeY, largura, 2);

  ctx.fillStyle = PALETA.texto;
  ctx.font = "700 22px system-ui, sans-serif";
  ctx.fillText(
    "Resumo automático · Sem vínculo com a Câmara Municipal de Inhumas",
    64,
    rodapeY + 48,
  );

  ctx.fillStyle = PALETA.textoSuave;
  ctx.font = "500 21px system-ui, sans-serif";
  const linhasRodape = quebrarLinhas(ctx, slide.rodape_fonte, largura - 128, 2);
  let rY = rodapeY + 88;
  for (const l of linhasRodape) {
    ctx.fillText(l, 64, rY);
    rY += 30;
  }

  return canvas.toDataURL("image/png");
}

export function baixarCardPng(
  slide: SlideInstagramOut,
  totalSlides: number,
  formato: "feed" | "story",
  prefixoArquivo: string,
): void {
  const dataUrl = renderizarSlideParaDataUrl(slide, totalSlides, formato);
  const link = document.createElement("a");
  link.href = dataUrl;
  const sufixo = formato === "story" ? "story-1080x1920" : `slide-${slide.numero}-1080x1350`;
  link.download = `${prefixoArquivo}-${sufixo}.png`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function construirSlideStoryUnico(boletim: BoletimSemanalOut): SlideInstagramOut {
  const s1 = boletim.slides_instagram[0];
  const s3 = boletim.slides_instagram[2];
  return {
    numero: 1,
    etiqueta: "RESUMO DA SEMANA · CERRADO ABERTO",
    titulo: boletim.nome_sessao,
    subtitulo: s1?.subtitulo || "Resumo automático baseado em dados oficiais",
    itens: [
      ...(s1?.itens || []).slice(0, 2),
      boletim.destaques_pauta[0]
        ? `Destaque: ${boletim.destaques_pauta[0].nome_materia} — ${truncarPalavras(boletim.destaques_pauta[0].resumo_cidadao.o_que_propoe, 100)}`
        : "Confira todos os itens da pauta no site",
      s3 ? `Gasto 2026: ${s3.titulo}` : "Transparência verificável em cerradoaberto.org.br",
    ],
    rodape_fonte:
      s1?.rodape_fonte ||
      `Fonte: Nexlegis e Transparência · ${boletim.handle_instagram_oficial} · ${boletim.dominio_oficial}`,
  };
}
