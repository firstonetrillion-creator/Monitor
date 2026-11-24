import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-[var(--border)] bg-[var(--surface-alt)] text-sm text-[var(--ink-muted)]">
      <div className="max-w-6xl mx-auto px-4 py-10 grid gap-8 md:grid-cols-3">
        <div>
          <p className="font-display text-lg font-bold text-[var(--ink)]">Cerrado Aberto</p>
          <p className="mt-2 leading-relaxed">
            Plataforma cidadã independente de monitoramento e interpretação de dados públicos do
            Legislativo municipal de Inhumas (GO), sem vínculo institucional, contratual ou
            político com a Câmara Municipal.
          </p>
        </div>

        <div>
          <p className="font-semibold text-[var(--ink)]">Fontes oficiais monitoradas</p>
          <ul className="mt-2 space-y-1.5">
            <li>
              <a
                href="https://acessoainformacao.inhumas.go.leg.br/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-[var(--primary)]"
              >
                Portal da Transparência CENTI / NúcleoGov
              </a>
            </li>
            <li>
              <a
                href="https://inhumas.nexlegis.com.br/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-[var(--primary)]"
              >
                Sistema Legislativo Nexlegis
              </a>
            </li>
            <li>
              <a
                href="https://acessoainformacao.inhumas.go.leg.br/cidadao/legislacao/leis"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-[var(--primary)]"
              >
                Legislação Municipal (Inhumas/GO)
              </a>
            </li>
            <li>
              <a
                href="https://siconfi.tesouro.gov.br/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-[var(--primary)]"
              >
                SICONFI — Secretaria do Tesouro Nacional
              </a>
            </li>
          </ul>
          <p className="mt-4 font-semibold text-[var(--ink)]">Explorar ferramentas</p>
          <ul className="mt-2 space-y-1.5">
            <li>
              <Link href="/busca" className="underline hover:text-[var(--primary)]">
                Busca avançada unificada
              </Link>
            </li>
            <li>
              <Link href="/bairros" className="underline hover:text-[var(--primary)]">
                Mapa de indicações por bairro
              </Link>
            </li>
            <li>
              <Link href="/legislacao" className="underline hover:text-[var(--primary)]">
                Legislação municipal pesquisável
              </Link>
            </li>
            <li>
              <Link href="/comparativo" className="underline hover:text-[var(--primary)]">
                Comparativo com cidades de Goiás (SICONFI)
              </Link>
            </li>
            <li>
              <Link href="/dados-abertos" className="underline hover:text-[var(--primary)]">
                API Pública e Dados Abertos (JSON / CSV)
              </Link>
            </li>
          </ul>
        </div>

        <div>
          <p className="font-semibold text-[var(--ink)]">Transparência, método e contato</p>
          <ul className="mt-2 space-y-1.5">
            <li>
              <Link href="/boletins" className="underline hover:text-[var(--primary)]">
                Boletim da Semana e cartões (WhatsApp / Instagram)
              </Link>
            </li>
            <li>
              <a
                href="https://www.instagram.com/cerradoaberto/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-[var(--primary)]"
              >
                Instagram Oficial do Cerrado Aberto (@cerradoaberto)
              </a>
            </li>
            <li>
              <Link href="/como-calculamos" className="underline hover:text-[var(--primary)]">
                Como calculamos os indicadores
              </Link>
            </li>
            <li>
              <Link
                href="/cobertura-e-limitacoes"
                className="underline hover:text-[var(--primary)]"
              >
                Cobertura atual e limitações documentadas
              </Link>
            </li>
            <li>
              <Link href="/custo-mandato" className="underline hover:text-[var(--primary)]">
                Metodologia do Custo da Estrutura do Mandato
              </Link>
            </li>
            <li>
              <Link href="/correcoes" className="underline hover:text-[var(--primary)]">
                Canal de correção e direito de resposta
              </Link>
            </li>
            <li>
              <Link href="/sobre" className="underline hover:text-[var(--primary)]">
                Sobre o Cerrado Aberto e declaração de independência
              </Link>
            </li>
          </ul>
          <p className="mt-3 text-xs">
            Proteção LGPD: nenhum CPF completo é armazenado ou exibido. Valores ausentes são
            preservados como não publicados, nunca convertidos em zero.
          </p>
        </div>
      </div>
    </footer>
  );
}
