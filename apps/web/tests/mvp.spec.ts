import fs from "node:fs";
import path from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR || "";

const REGEX_CPF_FORMATADO = /\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/;
const PALAVRAS_PROIBIDAS = [
  "fraude",
  "desvio",
  "esquema",
  "irregular",
  "suspeito",
  "escândalo",
  "absurdo",
  "farra",
  "mamata",
];

async function auditarPagina(
  page: import("@playwright/test").Page,
  nomeCaptura?: string,
) {
  const bodyText = await page.locator("body").innerText();
  const bodyLower = bodyText.toLowerCase();

  // 1. Auditoria LGPD: nenhum CPF completo exposto
  expect(bodyText).not.toMatch(REGEX_CPF_FORMATADO);

  // 2. Auditoria de neutralidade editorial (skill texto-cidadao)
  for (const palavra of PALAVRAS_PROIBIDAS) {
    // Evitar falso positivo se a página explicar explicitamente a regra (ex.: "/como-calculamos")
    expect(bodyLower).not.toContain(palavra);
  }

  // 3. Responsividade: sem rolagem horizontal na página
  const overflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
  });
  expect(overflow).toBe(false);

  // 4. Acessibilidade (axe-core WCAG 2.0/2.1 A e AA — 0 violações graves/críticas)
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const graves = axe.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious",
  );
  expect(graves, JSON.stringify(graves, null, 2)).toEqual([]);

  // 5. Captura de tela opcional para revisão humana
  if (SCREENSHOT_DIR && nomeCaptura) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, `${nomeCaptura}.png`),
      fullPage: true,
    });
  }
}

test.describe("Cerrado Aberto — MVP Público (Homologação)", () => {
  test("A. Página inicial exibe indicadores reais e última atualização", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Os dados públicos da Câmara Municipal de Inhumas/i }),
    ).toBeVisible();

    // Totais reais do PostgreSQL 16 (incluindo coleta incremental até 17/11/2026) e indicador per capita (IBGE 2026)
    await expect(page.getByText("134", { exact: true })).toBeVisible();
    await expect(page.getByText("1.311", { exact: true })).toBeVisible();
    await expect(page.getByText(/8\.873\.608,80/).first()).toBeVisible();
    await expect(page.getByText(/9\.878\.324,86/).first()).toBeVisible();
    await expect(page.getByText(/9\.111\.797,89/).first()).toBeVisible();
    await expect(page.getByText(/54\.133 hab\./i).first()).toBeVisible();
    await expect(page.getByText(/Data da última atualização dos dados/i)).toBeVisible();

    await auditarPagina(page, isMobile ? "01-home-mobile" : "01-home-desktop");
  });

  test("B. Vereadores (ordem alfabética, filtro e perfil com preservação de NULL)", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/vereadores");
    await expect(page.getByRole("heading", { name: "Vereadores" })).toBeVisible();

    // Filtro por nome
    await page.getByLabel("Buscar por nome").fill("Kelvy");
    await page.getByRole("button", { name: "Filtrar" }).click();
    await expect(page.getByText(/Kelvy Fernandes/i)).toBeVisible();
    await auditarPagina(
      page,
      isMobile ? "02-vereadores-mobile" : "02-vereadores-desktop",
    );

    // Perfil individual (Prof. Kelvy Fernandes)
    await page.getByRole("link", { name: /Kelvy Fernandes/i }).first().click();
    await expect(
      page.getByRole("heading", { name: "Custo da Estrutura do Mandato (2026)", exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/inexistente/i).first()).toBeVisible();
    await auditarPagina(
      page,
      isMobile ? "03-vereador-perfil-mobile" : "03-vereador-perfil-desktop",
    );

    // Presidente da Câmara (Hugo Pessoni): lacuna parcial preserva NULL, nunca zero
    await page.goto("/vereadores/inhumas-go-ver-81");
    await expect(page.getByText(/Hugo/i).first()).toBeVisible();
    await expect(page.getByText(/Não apurado/i).first()).toBeVisible();
    await auditarPagina(page);
  });

  test("C. Custo da Estrutura do Mandato exibe componentes separados e nota CEAP", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/custo-mandato");
    await expect(
      page.getByRole("heading", { name: /Custo da Estrutura do Mandato \(2026\)/i }),
    ).toBeVisible();
    await expect(page.getByText(/Cota parlamentar \(CEAP\): inexistente/i)).toBeVisible();
    await expect(page.getByText(/12\.796,93/).first()).toBeVisible();

    // Alternar gráfico para tabela acessível
    await page.getByRole("button", { name: /Ver dados em tabela/i }).first().click();
    await expect(page.getByRole("button", { name: /Ver gráfico/i }).first()).toBeVisible();

    await auditarPagina(
      page,
      isMobile ? "04-custo-mandato-mobile" : "04-custo-mandato-desktop",
    );
  });

  test("D. Despesas públicas reconcilia estágios, exibe favorecidos PJ, duodécimo, CSV e filtros", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/despesas");
    await expect(
      page.getByRole("heading", { name: /Despesas Públicas \(2026\)/i }),
    ).toBeVisible();

    // Reconciliação exata com o PostgreSQL 16
    await expect(page.getByText(/11\.122\.741,47/).first()).toBeVisible();
    await expect(page.getByText(/1\.244\.416,61/).first()).toBeVisible();
    await expect(page.getByText(/9\.878\.324,86/).first()).toBeVisible();
    await expect(page.getByText(/8\.873\.608,80/).first()).toBeVisible();

    // Favorecidos Pessoa Jurídica (PJ) e detalhamento do duodécimo
    await expect(
      page.getByRole("heading", { name: /Despesas por favorecido Pessoa Jurídica/i }),
    ).toBeVisible();
    await page.getByText(/Ver os 22 lançamentos do duodécimo/i).click();
    await expect(page.getByText(/99\.000,00/).first()).toBeVisible();

    // Exportação CSV a um clique
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /Baixar CSV do duodécimo/i }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("duodecimo-2026-inhumas.csv");

    await auditarPagina(
      page,
      isMobile ? "05-despesas-mobile" : "05-despesas-desktop",
    );

    // Aplicar filtro de Elemento 14 (Diárias)
    await page
      .getByLabel("Classificação (Elemento de despesa)", { exact: true })
      .selectOption("14 - Diárias – Civil");
    await page.getByRole("button", { name: "Aplicar filtros" }).click();
    await expect(page.getByText(/Estágios da despesa no recorte \(14 empenhos\)/i)).toBeVisible();
    await expect(page.getByText(/6\.600,00/).first()).toBeVisible();
  });

  test("E. Diárias explica diferença entre cntdiarias e Elemento 14", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/diarias");
    await expect(page.getByRole("heading", { name: /Diárias \(2026\)/i })).toBeVisible();
    await expect(page.getByText(/cntdiarias/i).first()).toBeVisible();
    await expect(page.getByText(/6\.600,00/).first()).toBeVisible();
    await expect(page.getByText(/1\.600,00/).first()).toBeVisible();
    await auditarPagina(page, isMobile ? "06-diarias-mobile" : "06-diarias-desktop");
  });

  test("F. Sessões e votações navegam para detalhe com pauta, presenças e votos", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/sessoes");
    await expect(
      page.getByRole("heading", { name: /Sessões e Votações/i }),
    ).toBeVisible();
    await expect(page.getByText(/134 sessões encontradas/i)).toBeVisible();
    await auditarPagina(page, isMobile ? "07-sessoes-mobile" : "07-sessoes-desktop");

    // Abrir primeira sessão da lista (Sessão Ordinária 044/2026 — 17/11/2026)
    await page.locator('a[href^="/sessoes/"]').first().click();
    await expect(page.getByText(/Resumo automático/i).first()).toBeVisible();
    await expect(page.getByText(/Presenças registradas/i)).toBeVisible();
    await expect(page.getByText(/Pauta e proposições discutidas/i)).toBeVisible();
    await expect(page.getByText(/Resultados das votações/i)).toBeVisible();
    await auditarPagina(page, isMobile ? undefined : "08-sessao-detalhe-desktop");
  });

  test("H. Boletim da Semana exibe resumo automático, alerta WhatsApp e baixa cards PNG do Instagram Oficial", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/boletins");
    await expect(
      page.getByRole("heading", { name: /Boletim da Semana e Cartões Compartilháveis/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Sessão Ordinária 044\/2026/i }).first(),
    ).toBeVisible();
    await expect(page.getByText(/Resumo automático/i).first()).toBeVisible();
    await expect(page.getByText(/@cerradoaberto/i).first()).toBeVisible();
    await expect(page.getByText(/\/400 caracteres/i)).toBeVisible();

    // Download PNG dos 3 slides do carrossel (1080x1350) para o Instagram Oficial
    const dlFeedPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /Baixar Slide 1 \(1080×1350\)/i }).click();
    const dlFeed = await dlFeedPromise;
    expect(dlFeed.suggestedFilename()).toMatch(/-slide-1-1080x1350\.png$/);
    if (SCREENSHOT_DIR && !isMobile) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
      await dlFeed.saveAs(path.join(SCREENSHOT_DIR, "card-instagram-slide-1-1080x1350.png"));

      const dlSlide2Promise = page.waitForEvent("download");
      await page.getByRole("button", { name: /Baixar Slide 2 \(1080×1350\)/i }).click();
      const dlSlide2 = await dlSlide2Promise;
      await dlSlide2.saveAs(path.join(SCREENSHOT_DIR, "card-instagram-slide-2-1080x1350.png"));

      const dlSlide3Promise = page.waitForEvent("download");
      await page.getByRole("button", { name: /Baixar Slide 3 \(1080×1350\)/i }).click();
      const dlSlide3 = await dlSlide3Promise;
      await dlSlide3.saveAs(path.join(SCREENSHOT_DIR, "card-instagram-slide-3-1080x1350.png"));
    }

    // Download PNG de Story / Status (1080x1920)
    const dlStoryPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /Baixar Story \/ Status \(1080×1920\)/i }).click();
    const dlStory = await dlStoryPromise;
    expect(dlStory.suggestedFilename()).toMatch(/-story-1080x1920\.png$/);
    if (SCREENSHOT_DIR && !isMobile) {
      await dlStory.saveAs(path.join(SCREENSHOT_DIR, "card-instagram-story-1080x1920.png"));
    }

    await auditarPagina(page, isMobile ? "13-boletins-mobile" : "13-boletins-desktop");
  });

  test("G. Como calculamos, correções, cobertura, sobre e registro inexistente (404)", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/como-calculamos");
    await expect(
      page.getByRole("heading", { name: /Como calculamos e limitações dos dados/i }),
    ).toBeVisible();
    await expect(page.getByText(/54\.133 habitantes/i)).toBeVisible();
    await auditarPagina(page, isMobile ? undefined : "09-como-calculamos-desktop");

    await page.goto("/correcoes");
    await expect(
      page.getByRole("heading", { name: /Canal de correção e esclarecimentos/i }),
    ).toBeVisible();
    await expect(page.getByText(/firstonetrillion@gmail\.com/i).first()).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Registro público de correções realizadas/i }),
    ).toBeVisible();
    await auditarPagina(page, isMobile ? undefined : "10-correcoes-desktop");

    await page.goto("/cobertura-e-limitacoes");
    await expect(
      page.getByRole("heading", { name: /Cobertura atual e limitações documentadas/i }),
    ).toBeVisible();
    await auditarPagina(page, isMobile ? undefined : "11-cobertura-limitacoes-desktop");

    await page.goto("/sobre");
    await expect(
      page.getByRole("heading", { name: /Sobre o Cerrado Aberto/i }),
    ).toBeVisible();
    await auditarPagina(page, isMobile ? undefined : "12-sobre-desktop");

    await page.goto("/vereadores/id-inexistente-999");
    await expect(page.getByText(/Vereador não encontrado/i)).toBeVisible();
  });

  test("I. Busca Avançada Unificada pesquisa em proposições, leis, vereadores e despesas", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/busca?q=asfalto");
    await expect(
      page.getByRole("heading", { name: /Busca Avançada no Legislativo de Inhumas/i }),
    ).toBeVisible();
    await expect(page.getByRole("tab", { name: /Proposições/i })).toBeVisible();
    await expect(page.getByText(/Encontrados/i)).toBeVisible();
    await auditarPagina(page, isMobile ? "14-busca-mobile" : "14-busca-desktop");
  });

  test("J. Mapa de Indicações por Bairro exibe cobertura, mapa vetorial, tabela e CSV", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/bairros");
    await expect(
      page.getByRole("heading", { name: /Mapa de Indicações e Requerimentos por Bairro/i }),
    ).toBeVisible();
    await expect(page.getByText(/Proposições citando bairro/i)).toBeVisible();
    await expect(page.getByText(/Sem localidade na ementa/i)).toBeVisible();

    const dlPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /Baixar CSV/i }).click();
    const dl = await dlPromise;
    expect(dl.suggestedFilename()).toMatch(/^cerrado-aberto-bairros-inhumas.*\.csv$/);

    await auditarPagina(page, isMobile ? "15-bairros-mobile" : "15-bairros-desktop");
  });

  test("K. Legislação Municipal Pesquisável lista leis oficiais e abre detalhe com resumo automático", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/legislacao");
    await expect(
      page.getByRole("heading", { name: /Legislação Municipal Pesquisável/i }),
    ).toBeVisible();
    await expect(page.getByText(/407/).first()).toBeVisible();
    await auditarPagina(page, isMobile ? "16-legislacao-mobile" : "16-legislacao-desktop");

    await page.goto("/legislacao/3577");
    await expect(page.getByRole("heading", { name: /3577\/2026/i }).first()).toBeVisible();
    await expect(page.getByText(/Resumo automático/i).first()).toBeVisible();
    await auditarPagina(page, isMobile ? undefined : "17-legislacao-detalhe-desktop");
  });

  test("L. Comparativo SICONFI GO e Portal de API Pública / Dados Abertos", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/comparativo");
    await expect(
      page.getByRole("heading", { name: /Comparativo com Cidades Semelhantes de Goiás/i }),
    ).toBeVisible();
    await expect(page.getByText(/9\.739\.153,62/).first()).toBeVisible();
    await expect(page.getByText(/Morrinhos/i).first()).toBeVisible();
    await auditarPagina(page, isMobile ? "18-comparativo-mobile" : "18-comparativo-desktop");

    await page.goto("/dados-abertos");
    await expect(
      page.getByRole("heading", { name: /API Pública e Dados Abertos/i }),
    ).toBeVisible();
    await page.getByRole("tab", { name: /Python/i }).click();
    await expect(page.getByText(/import httpx/i)).toBeVisible();
    await auditarPagina(page, isMobile ? "19-dados-abertos-mobile" : "19-dados-abertos-desktop");
  });
});
