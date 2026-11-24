"use client";

import { useState } from "react";
import Link from "next/link";
import { Code2, ExternalLink, ShieldCheck, Database } from "lucide-react";
import { BotaoCopiar } from "@/components/BotaoCopiar";

const EXEMPLOS_CODIGO = [
  {
    id: "curl",
    label: "cURL (Terminal)",
    codigo: `# 1. Buscar proposições e leis sobre asfalto em Inhumas
curl -s "https://cerradoaberto.org.br/api/v1/busca?q=asfalto&per_page=10" | jq .

# 2. Listar o comparativo oficial SICONFI (2025)
curl -s "https://cerradoaberto.org.br/api/v1/comparativo?ano=2025" | jq .

# 3. Obter o Boletim da Semana mais recente
curl -s "https://cerradoaberto.org.br/api/v1/boletins/resumo-semanal" | jq .`,
  },
  {
    id: "python",
    label: "Python (httpx)",
    codigo: `import httpx

base = "https://cerradoaberto.org.br/api/v1"

# Exemplo: bairros de Inhumas com mais proposições sobre infraestrutura
resp = httpx.get(f"{base}/bairros", params={"tema": "Infraestrutura e Asfalto"}, timeout=15)
resp.raise_for_status()
dados = resp.json()

for b in dados["bairros"][:10]:
    print(f"{b['nome_oficial']}: {b['total_proposicoes']} proposições")`,
  },
  {
    id: "js",
    label: "JavaScript (fetch)",
    codigo: `const res = await fetch(
  "https://cerradoaberto.org.br/api/v1/legislacao?q=educacao&per_page=10"
);
const dados = await res.json();
console.log("Total de leis encontradas:", dados.total);
console.table(dados.items.map((l) => ({ numero: l.numero, ano: l.ano, categoria: l.categoria_descricao })));`,
  },
] as const;

const ENDPOINTS_CATALOGO = [
  { grupo: "Observabilidade", rota: "/api/v1/health", desc: "Status do banco, contagens por tabela, última coleta por fonte e lacunas documentadas." },
  { grupo: "Busca e Território", rota: "/api/v1/busca?q=asfalto", desc: "Busca avançada unificada (Full-Text Search em português) em proposições, leis, vereadores, sessões e despesas." },
  { grupo: "Busca e Território", rota: "/api/v1/bairros", desc: "Painel de indicações e requerimentos por bairro/distrito de Inhumas, com filtro por ano, tema e vereador." },
  { grupo: "Busca e Território", rota: "/api/v1/bairros/centro", desc: "Detalhe completo das proposições vinculadas a um bairro específico com trecho de evidência." },
  { grupo: "Legislação", rota: "/api/v1/legislacao", desc: "Catálogo pesquisável das leis municipais cadastradas desde 1990 com link canônico oficial." },
  { grupo: "Legislação", rota: "/api/v1/legislacao/3577", desc: "Detalhe de uma lei com resumo automático, status de extração/OCR e hash SHA-256." },
  { grupo: "Comparativo Regional", rota: "/api/v1/comparativo?ano=2025", desc: "Despesa da Função 01 (Legislativa) de Inhumas e 7 municípios pares de Goiás (SICONFI/STN)." },
  { grupo: "Legislativo (Nexlegis)", rota: "/api/v1/vereadores", desc: "Lista paginada de vereadores com aliases, mandatos e indicadores de 2025–2026." },
  { grupo: "Legislativo (Nexlegis)", rota: "/api/v1/vereadores/inhumas-go-ver-5", desc: "Perfil completo do parlamentar: presenças, produção por tipo, votos nominais e Custo da Estrutura do Mandato." },
  { grupo: "Legislativo (Nexlegis)", rota: "/api/v1/sessoes", desc: "Sessões plenárias, presenças, pautas e votações nominais." },
  { grupo: "Legislativo (Nexlegis)", rota: "/api/v1/sessoes/inhumas-go-sessao-1035", desc: "Detalhe completo de uma sessão plenária (presenças, pauta, votos nominais e resumo automático)." },
  { grupo: "Legislativo (Nexlegis)", rota: "/api/v1/materias", desc: "Proposições legislativas com filtros e separação ADR-005 (parlamentares vs. administrativas)." },
  { grupo: "Legislativo (Nexlegis)", rota: "/api/v1/materias/inhumas-go-prop-2786", desc: "Detalhe de uma matéria com tramitações, deliberações em sessão e resumo automático." },
  { grupo: "Boletins (Fase 4)", rota: "/api/v1/boletins/resumo-semanal", desc: "Resumo automático da sessão mais recente, alerta WhatsApp (<=400 chars) e slides Instagram." },
  { grupo: "Finanças (Transparência)", rota: "/api/v1/transparencia/custo-mandato?ano=2026", desc: "Custo da Estrutura do Mandato com preservação estrita de NULL." },
  { grupo: "Finanças (Transparência)", rota: "/api/v1/transparencia/folha?ano=2026&mes=10", desc: "Folha de pagamento nominal mensal (sem CPF completo, LGPD) com lotação por gabinete ou setor." },
  { grupo: "Finanças (Transparência)", rota: "/api/v1/transparencia/despesas?ano=2026", desc: "Lista paginada de empenhos de despesa com filtros por período, favorecido e elemento." },
  { grupo: "Finanças (Transparência)", rota: "/api/v1/transparencia/despesas/resumo?ano=2026", desc: "Somatório reconciliado por estágio, por elemento e por fornecedor Pessoa Jurídica." },
  { grupo: "Finanças (Transparência)", rota: "/api/v1/transparencia/diarias?ano=2026", desc: "Diárias identificadas no cruzamento contábil do Elemento 14 com filtro por vereador." },
  { grupo: "Finanças (Transparência)", rota: "/api/v1/transparencia/duodecimo?ano=2026", desc: "Repasses de duodécimo e devoluções à Prefeitura em 2026." },
  { grupo: "Finanças (Transparência)", rota: "/api/v1/transparencia/declaracoes", desc: "Declarações oficiais de inexistência de cota parlamentar (CEAP) e não concessão de diárias." },
];

export function DadosAbertosClient() {
  const [abaAtiva, setAbaAtiva] = useState<string>("curl");

  return (
    <div className="space-y-8">
      {/* Princípios da API pública */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 space-y-1">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
            <Database className="w-4 h-4" aria-hidden="true" />
            Somente leitura (GET)
          </p>
          <p className="text-sm text-[var(--ink)]">
            Acesso aberto em JSON UTF-8 sem cadastro ou chave paga. Rate limit padrão: 240 req/min
            por IP (<code>X-RateLimit-*</code>).
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 space-y-1">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
            <ShieldCheck className="w-4 h-4" aria-hidden="true" />
            Proveniência e LGPD
          </p>
          <p className="text-sm text-[var(--ink)]">
            Todo registro inclui <code>fonte_url</code>, <code>coletado_em</code> e{" "}
            <code>hash_conteudo</code> SHA-256. Zero CPF completo em toda a API.
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 space-y-1">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
            <Code2 className="w-4 h-4" aria-hidden="true" />
            Atalhos CSV no site
          </p>
          <p className="text-sm text-[var(--ink)]">
            Prefere planilha? Baixe CSV pronto em{" "}
            <Link href="/despesas" className="underline text-[var(--primary)]">Despesas</Link>,{" "}
            <Link href="/folha" className="underline text-[var(--primary)]">Folha</Link>,{" "}
            <Link href="/diarias" className="underline text-[var(--primary)]">Diárias</Link>,{" "}
            <Link href="/materias" className="underline text-[var(--primary)]">Proposições</Link>,{" "}
            <Link href="/bairros" className="underline text-[var(--primary)]">Bairros</Link>,{" "}
            <Link href="/legislacao" className="underline text-[var(--primary)]">Leis</Link> e{" "}
            <Link href="/comparativo" className="underline text-[var(--primary)]">Comparativo</Link>.
          </p>
        </div>
      </div>

      {/* Exemplos de código em abas acessíveis (modern-web-guidance: tabs com hidden="until-found" e wrapper interno) */}
      <section className="space-y-3" aria-label="Exemplos de uso da API Pública">
        <h2 className="font-display text-2xl font-bold text-[var(--ink)]">
          Exemplos rápidos para jornalistas e pesquisadores
        </h2>

        <div
          role="tablist"
          aria-label="Linguagem do exemplo de código"
          className="flex items-center gap-1 overflow-x-auto border-b border-[var(--border)] pb-px"
        >
          {EXEMPLOS_CODIGO.map((ex) => {
            const sel = abaAtiva === ex.id;
            return (
              <button
                key={ex.id}
                id={`tab-codigo-${ex.id}`}
                type="button"
                role="tab"
                aria-selected={sel}
                onClick={(e) => {
                  setAbaAtiva(ex.id);
                  e.currentTarget.scrollIntoView({ block: "nearest", inline: "nearest" });
                }}
                className={`flex-none px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-[3px] transition-colors ${
                  sel
                    ? "border-[var(--primary)] text-[var(--primary)]"
                    : "border-transparent text-[var(--ink-muted)] hover:text-[var(--ink)]"
                }`}
              >
                {ex.label}
              </button>
            );
          })}
        </div>

        {/* Painéis sem border/padding no elemento [role=tabpanel] para compatibilidade com hidden="until-found" */}
        <div>
          {EXEMPLOS_CODIGO.map((ex) => {
            const sel = abaAtiva === ex.id;
            return (
              <div
                key={ex.id}
                role="tabpanel"
                aria-labelledby={`tab-codigo-${ex.id}`}
                hidden={!sel ? ("until-found" as unknown as boolean) : undefined}
              >
                <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-[var(--ink-muted)]">
                      {ex.label} — substitua o domínio por <code>http://127.0.0.1:8000</code> em
                      homologação local
                    </span>
                    <BotaoCopiar
                      targetId={`codigo-exemplo-${ex.id}`}
                      textoFallback={ex.codigo}
                      rotulo={`Copiar ${ex.label}`}
                    />
                  </div>
                  <pre
                    tabIndex={0}
                    role="region"
                    aria-label={`Exemplo de código ${ex.label}`}
                    className="overflow-x-auto rounded-xl bg-[var(--bg)] border border-[var(--border)] p-4 text-xs font-mono text-[var(--ink)] leading-relaxed"
                  >
                    <code id={`codigo-exemplo-${ex.id}`}>{ex.codigo}</code>
                  </pre>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Catálogo de endpoints clicáveis */}
      <section className="space-y-3">
        <h2 className="font-display text-2xl font-bold text-[var(--ink)]">
          Endpoints públicos disponíveis (GET)
        </h2>
        <div
          role="region"
          aria-label="Catálogo de endpoints da API Pública v1"
          tabIndex={0}
          className="overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)]"
        >
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-[var(--surface-alt)] text-xs uppercase text-[var(--ink-muted)]">
              <tr>
                <th scope="col" className="px-4 py-3">Domínio</th>
                <th scope="col" className="px-4 py-3">Endpoint (testar JSON)</th>
                <th scope="col" className="px-4 py-3">Descrição</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {ENDPOINTS_CATALOGO.map((ep) => (
                <tr key={ep.rota} className="hover:bg-[var(--surface-alt)]/40">
                  <td className="px-4 py-2.5 text-xs font-semibold text-[var(--primary)] whitespace-nowrap">
                    {ep.grupo}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs whitespace-nowrap">
                    <a
                      href={ep.rota}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[var(--ink)] hover:text-[var(--primary)] underline"
                    >
                      {ep.rota}
                      <ExternalLink className="w-3 h-3" aria-hidden="true" />
                    </a>
                  </td>
                  <td className="px-4 py-2.5 text-[var(--ink-muted)]">{ep.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
