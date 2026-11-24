/**
 * Coletor educado de metadados das Leis Municipais de Inhumas (NúcleoGov — ADR-004 / Fase 5 D2).
 *
 * Regras inegociáveis:
 * - Usa sessão normal de navegador Playwright (conforme ADR-001 e docs/fontes/transparencia.md) apenas
 *   na página pública sem login e sem CAPTCHA (`cidadao/legislacao/leis`).
 * - Se encontrar qualquer desafio CAPTCHA ou erro HTTP, interrompe imediatamente sem tentar contornar.
 * - Respeita `Crawl-Delay >= 5,0s` (5.200 ms entre páginas), concorrência = 1, ~9 páginas de 50 registros.
 * - Salva o JSON bruto imutável em `data/raw/inhumas-go/legislacao/leis/pagina_XXX.json`.
 */

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(
  path.resolve(process.cwd(), "apps/web/node_modules/playwright"),
);

const URL_PAGINA = "https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis";
const OUT_DIR = path.resolve(process.cwd(), "data/raw/inhumas-go/legislacao/leis");
const PAGE_SIZE = 50;
const CRAWL_DELAY_MS = 5200;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    locale: "pt-BR",
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 CerradoAberto/0.1",
  });
  const page = await context.newPage();

  let acaoBase = null;
  page.on("response", async (res) => {
    if (res.url().endsWith("/api") && res.request().method() === "POST" && !acaoBase) {
      try {
        const text = await res.text();
        const json = JSON.parse(text);
        const pd = res.request().postData() || "";
        const paramsRaw = new URLSearchParams(pd).get("params");
        if (!paramsRaw) return;
        const paramsObj = JSON.parse(paramsRaw);
        for (const [k, val] of Object.entries(json)) {
          if (val && Array.isArray(val.dados) && val.dados.length > 0 && "ementa" in val.dados[0] && "numero" in val.dados[0]) {
            acaoBase = paramsObj[k] || Object.values(paramsObj)[0];
            console.log(`[Legislacao] Ação de leis confirmada pela resposta (${val.total} itens): ${JSON.stringify(acaoBase)}`);
            break;
          }
        }
      } catch {
        // ignora
      }
    }
  });

  try {
    console.log(`[Legislacao] Abrindo ${URL_PAGINA} ...`);
    const resp = await page.goto(URL_PAGINA, { waitUntil: "networkidle", timeout: 45000 });
    const status = resp ? resp.status() : 0;
    const html = await page.content();

    if (
      status >= 400 ||
      /cf-turnstile|challenges\.cloudflare\.com|verify you are human|captcha/i.test(html)
    ) {
      throw new Error(
        `BLOQUEADO: página retornou status=${status} ou desafio anti-bot/CAPTCHA. Abortando conforme regras éticas.`,
      );
    }

    // Aguarda o XHR real de listagem de leis (excluindo configuracoes/pegaIndices)
    for (let i = 0; i < 25 && !acaoBase; i += 1) {
      await sleep(400);
    }

    if (!acaoBase) {
      throw new Error("Não foi possível capturar a ação de listagem de leis em POST /api.");
    }
    console.log(`[Legislacao] Ação oficial detectada: ${acaoBase.acao} (${JSON.stringify(acaoBase)})`);

    let offset = 0;
    let totalDeclarado = null;
    let paginaNum = 1;
    const maxPaginasSeguranca = 20;

    while (paginaNum <= maxPaginasSeguranca) {
      if (paginaNum > 1) {
        await sleep(CRAWL_DELAY_MS);
      }

      const reqPayload = {
        "0-leis": {
          ...acaoBase,
          limit: `${offset}, ${PAGE_SIZE}`,
        },
      };

      const resultado = await page.evaluate(async (payloadObj) => {
        const body = new URLSearchParams({
          multi_request: "true",
          params: JSON.stringify(payloadObj),
        });
        const r = await fetch("/api", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
          },
          body: body.toString(),
        });
        const text = await r.text();
        return { status: r.status, text };
      }, reqPayload);

      if (resultado.status !== 200) {
        throw new Error(`Erro HTTP ${resultado.status} na página ${paginaNum} (offset=${offset}).`);
      }

      const parsed = JSON.parse(resultado.text);
      const bloco = parsed["0-leis"] || Object.values(parsed).find((v) => v && Array.isArray(v.dados));
      if (!bloco || !Array.isArray(bloco.dados)) {
        throw new Error(`Resposta inesperada na página ${paginaNum}: ${resultado.text.slice(0, 200)}`);
      }

      if (totalDeclarado === null) {
        totalDeclarado = Number(bloco.total || bloco.dados.length);
      }

      const nomeArq = `pagina_${String(paginaNum).padStart(3, "0")}.json`;
      fs.writeFileSync(path.join(OUT_DIR, nomeArq), resultado.text, "utf-8");
      console.log(
        `[Legislacao] Salvo ${nomeArq}: ${bloco.dados.length} registros (offset=${offset}, total=${totalDeclarado}).`,
      );

      if (bloco.dados.length === 0 || offset + bloco.dados.length >= totalDeclarado) {
        break;
      }

      offset += PAGE_SIZE;
      paginaNum += 1;
    }

    console.log(`[Legislacao] Coleta concluída com sucesso (${paginaNum} página(s), total=${totalDeclarado}).`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("[Legislacao] ERRO:", err.message || err);
  process.exit(1);
});
