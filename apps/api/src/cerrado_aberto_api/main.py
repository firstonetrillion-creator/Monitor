"""Aplicação FastAPI de leitura do Cerrado Aberto (Fase 1 — Dados validados de 2026)."""

from __future__ import annotations

import logging
import math
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from cerrado_aberto_api import __version__
from cerrado_aberto_api.boletins_router import router as boletins_router
from cerrado_aberto_api.db import obter_conexao_db
from cerrado_aberto_api.fase5_router import router as fase5_router
from cerrado_aberto_api.rate_limit import RateLimitMiddleware
from cerrado_aberto_api.resumos import gerar_resumo_materia, gerar_resumo_sessao
from cerrado_aberto_api.schemas import (
    AliasVereadorOut,
    AutorMateriaOut,
    ColetaFonteOut,
    CustoMandatoMensalOut,
    CustoMandatoResumoAnualOut,
    DeclaracaoTransparenciaOut,
    DeliberacaoMateriaSessaoOut,
    DespesaEmpenhoOut,
    DespesaPorElementoOut,
    DespesasResumoOut,
    DiariaOut,
    DuodecimoOut,
    FavorecidoDespesaOut,
    FolhaPagamentoOut,
    HealthOut,
    LacunaHistoricaOut,
    MandatoVereadorOut,
    MateriaDetalheOut,
    MateriaResumoOut,
    PaginacaoOut,
    PautaItemSessaoOut,
    PresencaSessaoOut,
    ProducaoPorTipoOut,
    ProposicaoRecenteVereadorOut,
    ProvenienciaOut,
    ResumoPresenca2026Out,
    SessaoDetalheOut,
    SessaoResumoOut,
    TotaisDespesaOut,
    TramitacaoMateriaOut,
    VereadorDetalheOut,
    VereadorResumoOut,
    VotacaoSessaoOut,
    VotoNominalItemOut,
    VotoRecenteVereadorOut,
)
from cerrado_aberto_api.security import (
    FiltroLogLGPD,
    LGPDAndReadOnlyMiddleware,
    sanitizar_estrutura_lgpd,
)

# Configura filtro LGPD nos loggers da aplicação
logger = logging.getLogger("cerrado_aberto_api")
logger.addFilter(FiltroLogLGPD())

app = FastAPI(
    title="Cerrado Aberto — API Pública de Transparência Legislativa",
    description=(
        "Plataforma cidadã independente de monitoramento e interpretação de dados públicos "
        "do Legislativo municipal de Inhumas (GO), sem vínculo institucional, contratual ou "
        "político com a Câmara Municipal.\n\n"
        "- **Modo:** Somente leitura (`GET`).\n"
        "- **Proveniência:** Todos os registros exibem `fonte_url`, `coletado_em`, `hash_conteudo` (SHA-256) e `versao_coletor`.\n"
        "- **LGPD:** Nenhum CPF completo é armazenado ou retornado.\n"
        "- **Rate Limit:** Limite configurável por IP (`X-RateLimit-Limit` / `X-RateLimit-Remaining`, padrão 240 req/min).\n"
        "- **Escopo ativo:** Fase 1 (Nexlegis 2025–2026) + Fase 2 (Transparência CENTI/NúcleoGov 2026) + "
        "Fase 4 (Resumos e Boletins Semanais) + Fase 5 (Busca FTS, Mapa por Bairros, Legislação Municipal e Comparativo SICONFI/GO)."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(LGPDAndReadOnlyMiddleware)
app.add_middleware(RateLimitMiddleware)
app.include_router(boletins_router)
app.include_router(fase5_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    detalhes_limpos = sanitizar_estrutura_lgpd(exc.errors())
    return JSONResponse(status_code=422, content={"detail": detalhes_limpos})


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detalhe_limpo = sanitizar_estrutura_lgpd(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": detalhe_limpo})


DbConnDep = Annotated[psycopg.Connection[dict[str, Any]], Depends(obter_conexao_db)]


def _construir_proveniencia(row: dict[str, Any]) -> ProvenienciaOut:
    return ProvenienciaOut(
        municipio_id=row["municipio_id"],
        fonte_id=row["fonte_id"],
        fonte_url=row["fonte_url"],
        coletado_em=row["coletado_em"],
        hash_conteudo=row["hash_conteudo"].strip(),
        versao_coletor=row["versao_coletor"],
    )


def _calcular_total_pages(total: int, per_page: int) -> int:
    if total == 0:
        return 0
    return math.ceil(total / per_page)


# -----------------------------------------------------------------------------
# 1. GET /api/v1/health
# -----------------------------------------------------------------------------


@app.get(
    "/api/v1/health",
    response_model=HealthOut,
    tags=["Observabilidade e Escopo"],
    summary="Verifica a saúde do banco PostgreSQL 16, contagens persistidas e lacunas documentadas",
)
def get_health(
    conn: DbConnDep,
    municipio_id: Annotated[
        str, Query(min_length=2, max_length=64, description="Identificador do município.")
    ] = "inhumas-go",
) -> HealthOut:
    with conn.cursor() as cur:
        cur.execute("SELECT version() AS ver")
        ver_row = cur.fetchone()
        versao_pg = str(ver_row["ver"]).split(",")[0] if ver_row else "PostgreSQL 16"

        tabelas_Monitoradas = (
            "vereador",
            "vereador_alias",
            "mandato",
            "sessao",
            "presenca",
            "proposicao",
            "autoria",
            "tramitacao",
            "pauta_item",
            "votacao",
            "voto",
            "documento_bruto",
            "fornecedor",
            "folha_pagamento",
            "despesa_empenho",
            "diaria",
            "receita_duodecimo",
            "declaracao_oficial_transparencia",
            "custo_estrutura_mandato_mensal",
            "norma",
            "bairro",
            "proposicao_bairro",
            "comparativo_legislativo_siconfi",
        )
        contagens: dict[str, int] = {}
        for t in tabelas_Monitoradas:
            cur.execute("SELECT to_regclass(%s) AS reg", (f"public.{t}",))
            reg_row = cur.fetchone()
            if not reg_row or reg_row["reg"] is None:
                contagens[t] = 0
                continue
            cur.execute(f"SELECT COUNT(*) AS c FROM {t} WHERE municipio_id = %s", (municipio_id,))
            r = cur.fetchone()
            contagens[t] = int(r["c"]) if r else 0

        cur.execute(
            """
            SELECT lacuna_id, fonte_id, entidade_afetada,
                   data_inicio_lacuna, data_fim_lacuna,
                   motivo_oficial, evidencia_url, pedido_lai_previsto
            FROM lacuna_historica
            WHERE municipio_id = %s AND ativa = TRUE
            ORDER BY data_inicio_lacuna
            """,
            (municipio_id,),
        )
        lacunas = [LacunaHistoricaOut(**row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT fonte_id, MAX(coletado_em) AS ultima_coleta_em, COUNT(*) AS documentos_brutos
            FROM documento_bruto
            WHERE municipio_id = %s
            GROUP BY fonte_id
            ORDER BY fonte_id
            """,
            (municipio_id,),
        )
        coletas = [
            ColetaFonteOut(
                fonte_id=row["fonte_id"],
                ultima_coleta_em=row["ultima_coleta_em"],
                documentos_brutos=int(row["documentos_brutos"]),
            )
            for row in cur.fetchall()
        ]

    return HealthOut(
        status="ok",
        banco_dados="conectado",
        versao_postgresql=versao_pg,
        municipio_padrao=municipio_id,
        contagens_persistidas=contagens,
        lacunas_historicas_documentadas=lacunas,
        ultima_coleta_por_fonte=coletas,
    )


# -----------------------------------------------------------------------------
# 2. GET /api/v1/vereadores & GET /api/v1/vereadores/{id}
# -----------------------------------------------------------------------------


@app.get(
    "/api/v1/vereadores",
    response_model=PaginacaoOut[VereadorResumoOut],
    tags=["Vereadores"],
    summary="Lista vereadores com filtros, paginação, presença e produção parlamentar em 2026",
)
def listar_vereadores(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1, description="Número da página (1-indexed).")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Itens por página.")] = 20,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=100, description="Busca textual por nome político, nome civil ou slug."),
    ] = None,
    partido: Annotated[
        str | None,
        Query(min_length=1, max_length=32, description="Filtra pela sigla partidária na legislatura 2025-2028."),
    ] = None,
    condicao: Annotated[
        str | None,
        Query(pattern="^(TITULAR|SUPLENTE)$", description="Filtra por condição do mandato (TITULAR ou SUPLENTE)."),
    ] = None,
    apenas_legislatura_atual: Annotated[
        bool,
        Query(description="Se verdadeiro, retorna apenas vereadores com mandato na legislatura 2025-2028."),
    ] = False,
) -> PaginacaoOut[VereadorResumoOut]:
    filtros = ["v.municipio_id = %s", "v.valido_ate IS NULL"]
    params: list[Any] = [municipio_id]

    if q:
        termo = f"%{q.strip().lower()}%"
        filtros.append(
            "(LOWER(v.nome_politico) LIKE %s OR LOWER(COALESCE(v.nome_civil, '')) LIKE %s "
            "OR LOWER(v.slug) LIKE %s OR LOWER(v.chave_busca) LIKE %s)"
        )
        params.extend([termo, termo, termo, termo])

    if partido:
        filtros.append("UPPER(m.partido_id) = UPPER(%s)")
        params.append(partido.strip())

    if condicao:
        filtros.append("m.condicao = %s")
        params.append(condicao)

    if apenas_legislatura_atual:
        filtros.append("m.mandato_id IS NOT NULL")

    where_sql = " AND ".join(filtros)
    offset = (page - 1) * per_page

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(DISTINCT v.vereador_id) AS total
            FROM vereador v
            LEFT JOIN mandato m
                ON m.municipio_id = v.municipio_id
               AND m.vereador_id = v.vereador_id
               AND m.legislatura_id = 'inhumas-go-2025-2028'
            WHERE {where_sql}
            """,
            params,
        )
        total_row = cur.fetchone()
        total = int(total_row["total"]) if total_row else 0

        cur.execute(
            f"""
            WITH pres_2025 AS (
                SELECT
                    pr.vereador_id,
                    COUNT(*) FILTER (WHERE pr.status_normalizado = 'PRESENTE') AS presentes,
                    COUNT(*) FILTER (WHERE pr.status_normalizado <> 'PRESENTE') AS ausentes
                FROM presenca pr
                JOIN sessao s ON s.sessao_id = pr.sessao_id AND s.ano = 2025
                WHERE pr.municipio_id = %s
                GROUP BY pr.vereador_id
            ),
            prod_2025 AS (
                SELECT
                    vw.vereador_id,
                    COALESCE(SUM(vw.total_proposicoes), 0)::int AS total_prop
                FROM vw_producao_legislativa_vereador vw
                WHERE vw.municipio_id = %s AND vw.ano = 2025
                GROUP BY vw.vereador_id
            ),
            pres_2026 AS (
                SELECT
                    pr.vereador_id,
                    COUNT(*) FILTER (WHERE pr.status_normalizado = 'PRESENTE') AS presentes,
                    COUNT(*) FILTER (WHERE pr.status_normalizado <> 'PRESENTE') AS ausentes
                FROM presenca pr
                JOIN sessao s ON s.sessao_id = pr.sessao_id AND s.ano = 2026
                WHERE pr.municipio_id = %s
                GROUP BY pr.vereador_id
            ),
            prod_2026 AS (
                SELECT
                    vw.vereador_id,
                    COALESCE(SUM(vw.total_proposicoes), 0)::int AS total_prop
                FROM vw_producao_legislativa_vereador vw
                WHERE vw.municipio_id = %s AND vw.ano = 2026
                GROUP BY vw.vereador_id
            ),
            custo_2026 AS (
                SELECT
                    c.vereador_id,
                    COUNT(*) FILTER (WHERE c.competencia_status = 'FECHADA')::int AS comp_fechadas,
                    CASE
                        WHEN COUNT(*) FILTER (WHERE c.competencia_status = 'LACUNA_PARCIAL_LOTACAO') > 0 THEN NULL
                        WHEN COUNT(*) FILTER (WHERE c.competencia_status = 'FECHADA') = 0 THEN NULL
                        ELSE SUM(c.custo_estrutura_mandato_total) FILTER (WHERE c.competencia_status = 'FECHADA')
                    END AS custo_acumulado
                FROM custo_estrutura_mandato_mensal c
                WHERE c.municipio_id = %s AND c.ano = 2026
                GROUP BY c.vereador_id
            )
            SELECT
                v.vereador_id,
                v.municipio_id,
                v.id_origem_nexlegis,
                v.nome_civil,
                v.nome_politico,
                v.nome_exibicao,
                v.slug,
                v.avatar_url,
                v.fonte_id,
                v.fonte_url,
                v.coletado_em,
                v.hash_conteudo,
                v.versao_coletor,
                m.partido_id AS partido_sigla,
                m.condicao AS condicao_mandato_2025_2028,
                COALESCE(p25.presentes, 0)::int AS sessoes_presente_2025,
                COALESCE(p25.ausentes, 0)::int AS sessoes_ausente_ou_justificado_2025,
                COALESCE(pr25.total_prop, 0)::int AS total_proposicoes_parlamentares_2025,
                COALESCE(p26.presentes, 0)::int AS sessoes_presente_2026,
                COALESCE(p26.ausentes, 0)::int AS sessoes_ausente_ou_justificado_2026,
                COALESCE(pr26.total_prop, 0)::int AS total_proposicoes_parlamentares_2026,
                c26.custo_acumulado AS custo_estrutura_mandato_acumulado_2026,
                COALESCE(c26.comp_fechadas, 0)::int AS competencias_custo_fechadas_2026
            FROM vereador v
            LEFT JOIN mandato m
                ON m.municipio_id = v.municipio_id
               AND m.vereador_id = v.vereador_id
               AND m.legislatura_id = 'inhumas-go-2025-2028'
            LEFT JOIN pres_2025 p25 ON p25.vereador_id = v.vereador_id
            LEFT JOIN prod_2025 pr25 ON pr25.vereador_id = v.vereador_id
            LEFT JOIN pres_2026 p26 ON p26.vereador_id = v.vereador_id
            LEFT JOIN prod_2026 pr26 ON pr26.vereador_id = v.vereador_id
            LEFT JOIN custo_2026 c26 ON c26.vereador_id = v.vereador_id
            WHERE {where_sql}
            ORDER BY
                CASE WHEN m.condicao = 'TITULAR' THEN 0 WHEN m.condicao = 'SUPLENTE' THEN 1 ELSE 2 END,
                v.nome_exibicao ASC
            LIMIT %s OFFSET %s
            """,
            [municipio_id, municipio_id, municipio_id, municipio_id, municipio_id, *params, per_page, offset],
        )
        rows = cur.fetchall()

    items = [
        VereadorResumoOut(
            vereador_id=r["vereador_id"],
            municipio_id=r["municipio_id"],
            id_origem_nexlegis=r["id_origem_nexlegis"],
            nome_civil=r["nome_civil"],
            nome_politico=r["nome_politico"],
            nome_exibicao=r["nome_exibicao"],
            slug=r["slug"],
            partido_sigla=r["partido_sigla"],
            condicao_mandato_2025_2028=r["condicao_mandato_2025_2028"],
            avatar_url=r["avatar_url"],
            sessoes_presente_2025=r["sessoes_presente_2025"],
            sessoes_ausente_ou_justificado_2025=r["sessoes_ausente_ou_justificado_2025"],
            total_proposicoes_parlamentares_2025=r["total_proposicoes_parlamentares_2025"],
            sessoes_presente_2026=r["sessoes_presente_2026"],
            sessoes_ausente_ou_justificado_2026=r["sessoes_ausente_ou_justificado_2026"],
            total_proposicoes_parlamentares_2026=r["total_proposicoes_parlamentares_2026"],
            custo_estrutura_mandato_acumulado_2026=r["custo_estrutura_mandato_acumulado_2026"],
            competencias_custo_fechadas_2026=r["competencias_custo_fechadas_2026"],
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]

    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


@app.get(
    "/api/v1/vereadores/{id}",
    response_model=VereadorDetalheOut,
    tags=["Vereadores"],
    summary="Obtém o perfil detalhado de um vereador por ID canônico, ID de origem ou slug",
)
def obter_vereador(
    conn: DbConnDep,
    id: Annotated[str, Path(min_length=1, max_length=160, description="vereador_id, id_origem_nexlegis ou slug.")],
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
) -> VereadorDetalheOut:
    id_num = int(id) if id.isdigit() else -1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM vereador
            WHERE municipio_id = %s
              AND (vereador_id = %s OR slug = %s OR id_origem_nexlegis = %s)
            LIMIT 1
            """,
            (municipio_id, id, id, id_num),
        )
        ver = cur.fetchone()
        if ver is None:
            raise HTTPException(status_code=404, detail=f"Vereador '{id}' não encontrado.")

        vid = ver["vereador_id"]

        cur.execute(
            """
            SELECT alias_texto, tipo_alias, fonte_origem, confianca
            FROM vereador_alias
            WHERE municipio_id = %s AND vereador_id = %s
            ORDER BY tipo_alias, alias_texto
            """,
            (municipio_id, vid),
        )
        aliases = [AliasVereadorOut(**a) for a in cur.fetchall()]

        cur.execute(
            """
            SELECT mandato_id, legislatura_id, partido_id, condicao,
                   cargo_mesa, votos_eleicao, valido_de, valido_ate
            FROM mandato
            WHERE municipio_id = %s AND vereador_id = %s
            ORDER BY valido_de DESC
            """,
            (municipio_id, vid),
        )
        mandatos = [MandatoVereadorOut(**m) for m in cur.fetchall()]

        cur.execute(
            """
            SELECT
                COUNT(*)::int AS total_sessoes_registradas,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'PRESENTE')::int AS presentes,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'FALTA_JUSTIFICADA')::int AS faltas_justificadas,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'AUSENTE')::int AS ausentes,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'LICENCA')::int AS licencas
            FROM presenca pr
            JOIN sessao s ON s.sessao_id = pr.sessao_id AND s.ano = 2025
            WHERE pr.municipio_id = %s AND pr.vereador_id = %s
            """,
            (municipio_id, vid),
        )
        pres_2025_row = cur.fetchone() or {
            "total_sessoes_registradas": 0,
            "presentes": 0,
            "faltas_justificadas": 0,
            "ausentes": 0,
            "licencas": 0,
        }
        resumo_presenca_2025 = ResumoPresenca2026Out(**pres_2025_row)

        cur.execute(
            """
            SELECT
                COUNT(*)::int AS total_sessoes_registradas,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'PRESENTE')::int AS presentes,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'FALTA_JUSTIFICADA')::int AS faltas_justificadas,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'AUSENTE')::int AS ausentes,
                COUNT(*) FILTER (WHERE pr.status_normalizado = 'LICENCA')::int AS licencas
            FROM presenca pr
            JOIN sessao s ON s.sessao_id = pr.sessao_id AND s.ano = 2026
            WHERE pr.municipio_id = %s AND pr.vereador_id = %s
            """,
            (municipio_id, vid),
        )
        pres_row = cur.fetchone() or {
            "total_sessoes_registradas": 0,
            "presentes": 0,
            "faltas_justificadas": 0,
            "ausentes": 0,
            "licencas": 0,
        }
        resumo_presenca = ResumoPresenca2026Out(**pres_row)

        cur.execute(
            """
            SELECT ano, tipo_id_origem, tipo_proposicao, categoria,
                   total_proposicoes::int AS total_proposicoes
            FROM vw_producao_legislativa_vereador
            WHERE municipio_id = %s AND vereador_id = %s AND ano = 2025
            ORDER BY total_proposicoes DESC, tipo_proposicao ASC
            """,
            (municipio_id, vid),
        )
        prod_tipos_2025 = [ProducaoPorTipoOut(**p) for p in cur.fetchall()]
        total_prod_2025 = sum(p.total_proposicoes for p in prod_tipos_2025)

        cur.execute(
            """
            SELECT ano, tipo_id_origem, tipo_proposicao, categoria,
                   total_proposicoes::int AS total_proposicoes
            FROM vw_producao_legislativa_vereador
            WHERE municipio_id = %s AND vereador_id = %s AND ano = 2026
            ORDER BY total_proposicoes DESC, tipo_proposicao ASC
            """,
            (municipio_id, vid),
        )
        prod_tipos = [ProducaoPorTipoOut(**p) for p in cur.fetchall()]
        total_prod_2026 = sum(p.total_proposicoes for p in prod_tipos)

        cur.execute(
            """
            SELECT DISTINCT
                p.proposicao_id, p.id_origem_nexlegis, p.nome_materia,
                p.tipo_id_origem, p.tipo_descricao_origem, p.ano, p.numero,
                p.ementa, p.data_publicacao,
                p.eh_proposicao_parlamentar, p.contabilizar_producao_vereador
            FROM autoria a
            JOIN proposicao p ON p.proposicao_id = a.proposicao_id
            WHERE a.municipio_id = %s
              AND a.vereador_id = %s
              AND p.contabilizar_producao_vereador = TRUE
            ORDER BY p.ano DESC, p.id_origem_nexlegis DESC
            LIMIT 20
            """,
            (municipio_id, vid),
        )
        props_recentes = [ProposicaoRecenteVereadorOut(**pr) for pr in cur.fetchall()]

        cur.execute(
            """
            SELECT
                vt.voto_id, vt.votacao_id, s.sessao_id, s.nome_sessao,
                s.data_abertura AS data_sessao, p.proposicao_id, p.nome_materia,
                vt.voto_descricao, vt.voto_normalizado
            FROM voto vt
            JOIN votacao vo ON vo.votacao_id = vt.votacao_id
            JOIN sessao s ON s.sessao_id = vo.sessao_id
            JOIN proposicao p ON p.proposicao_id = vo.proposicao_id
            WHERE vt.municipio_id = %s AND vt.vereador_id = %s AND s.ano = 2025
            ORDER BY s.data_abertura DESC, vo.id_origem_nexlegis DESC
            LIMIT 25
            """,
            (municipio_id, vid),
        )
        votos_recentes_2025 = [VotoRecenteVereadorOut(**vr) for vr in cur.fetchall()]

        cur.execute(
            """
            SELECT
                vt.voto_id, vt.votacao_id, s.sessao_id, s.nome_sessao,
                s.data_abertura AS data_sessao, p.proposicao_id, p.nome_materia,
                vt.voto_descricao, vt.voto_normalizado
            FROM voto vt
            JOIN votacao vo ON vo.votacao_id = vt.votacao_id
            JOIN sessao s ON s.sessao_id = vo.sessao_id
            JOIN proposicao p ON p.proposicao_id = vo.proposicao_id
            WHERE vt.municipio_id = %s AND vt.vereador_id = %s AND s.ano = 2026
            ORDER BY s.data_abertura DESC, vo.id_origem_nexlegis DESC
            LIMIT 25
            """,
            (municipio_id, vid),
        )
        votos_recentes = [VotoRecenteVereadorOut(**vr) for vr in cur.fetchall()]

        cur.execute(
            """
            SELECT c.*, v.nome_politico, v.nome_exibicao
            FROM custo_estrutura_mandato_mensal c
            JOIN vereador v ON v.vereador_id = c.vereador_id
            WHERE c.municipio_id = %s AND c.vereador_id = %s AND c.ano = 2026
            ORDER BY c.mes ASC
            """,
            (municipio_id, vid),
        )
        custos_rows = cur.fetchall()

    custo_resumo_2026: CustoMandatoResumoAnualOut | None = None
    if custos_rows:
        series_mensais = [
            CustoMandatoMensalOut(
                custo_mensal_id=cr["custo_mensal_id"],
                vereador_id=cr["vereador_id"],
                nome_politico=cr["nome_politico"],
                nome_exibicao=cr["nome_exibicao"],
                ano=cr["ano"],
                mes=cr["mes"],
                competencia_status=cr["competencia_status"],
                subsidio_bruto_vereador=cr["subsidio_bruto_vereador"],
                subsidio_mensal_base=cr["subsidio_mensal_base"],
                adicionais_ferias_decimo_terceiro_vereador=cr[
                    "adicionais_ferias_decimo_terceiro_vereador"
                ],
                folha_bruta_gabinete=cr["folha_bruta_gabinete"],
                folha_mensal_gabinete=cr["folha_mensal_gabinete"],
                adicionais_ferias_decimo_terceiro_gabinete=cr[
                    "adicionais_ferias_decimo_terceiro_gabinete"
                ],
                quantidade_servidores_gabinete=cr["quantidade_servidores_gabinete"],
                diarias_atribuiveis_empenhadas=cr["diarias_atribuiveis_empenhadas"],
                diarias_atribuiveis_liquidadas=cr["diarias_atribuiveis_liquidadas"],
                diarias_atribuiveis_pagas=cr["diarias_atribuiveis_pagas"],
                custo_estrutura_mandato_total=cr["custo_estrutura_mandato_total"],
                nota_cota_parlamentar=cr["nota_cota_parlamentar"],
                periodo_declaracao_ceap=cr["periodo_declaracao_ceap"],
                metodologia_resumo=cr["metodologia_resumo"],
                limitacoes_dados=cr["limitacoes_dados"],
                avisos=list(cr["avisos"] or []),
                proveniencia=_construir_proveniencia(cr),
            )
            for cr in custos_rows
        ]
        fechadas = [s for s in series_mensais if s.competencia_status == "FECHADA"]
        lacuna = [s for s in series_mensais if s.competencia_status == "LACUNA_PARCIAL_LOTACAO"]
        abertas = [s for s in series_mensais if s.competencia_status == "ABERTA_SEM_PUBLICACAO"]

        subs_validos = [s.subsidio_bruto_vereador for s in series_mensais if s.subsidio_bruto_vereador is not None]
        gabs_validos = [s.folha_bruta_gabinete for s in series_mensais if s.folha_bruta_gabinete is not None]
        dias_validas = [s.diarias_atribuiveis_pagas for s in series_mensais if s.diarias_atribuiveis_pagas is not None]
        totais_validos = [s.custo_estrutura_mandato_total for s in fechadas if s.custo_estrutura_mandato_total is not None]

        custo_resumo_2026 = CustoMandatoResumoAnualOut(
            ano=2026,
            competencias_fechadas=len(fechadas),
            competencias_lacuna_parcial=len(lacuna),
            competencias_abertas_null=len(abertas),
            subsidio_bruto_acumulado=(
                sum(subs_validos, Decimal("0.00")) if subs_validos else None
            ),
            folha_bruta_gabinete_acumulada=(
                sum(gabs_validos, Decimal("0.00")) if gabs_validos and not lacuna else None
            ),
            diarias_atribuiveis_pagas_acumuladas=(
                sum(dias_validas, Decimal("0.00")) if dias_validas else None
            ),
            custo_estrutura_mandato_acumulado=(
                sum(totais_validos, Decimal("0.00"))
                if totais_validos and not lacuna
                else None
            ),
            nota_cota_parlamentar=series_mensais[0].nota_cota_parlamentar,
            periodo_declaracao_ceap=series_mensais[0].periodo_declaracao_ceap,
            metodologia_resumo=series_mensais[0].metodologia_resumo,
            limitacoes_gerais=(
                "Competências fechadas em 2026: janeiro a outubro. Competências 11 e 12/2026 permanecem NULL "
                "(não encerradas até 12/11/2026). Valores não incluem encargos patronais agregados. "
                "Para o Presidente da Câmara, a folha de gabinete permanece NULL devido à lotação institucional 'PRESIDENCIA'."
            ),
            series_mensais=series_mensais,
        )

    return VereadorDetalheOut(
        vereador_id=ver["vereador_id"],
        municipio_id=ver["municipio_id"],
        id_origem_nexlegis=ver["id_origem_nexlegis"],
        nome_civil=ver["nome_civil"],
        nome_politico=ver["nome_politico"],
        nome_exibicao=ver["nome_exibicao"],
        slug=ver["slug"],
        email_publico=ver["email_publico"],
        avatar_url=ver["avatar_url"],
        biografia_texto=ver["biografia_texto"],
        aliases=aliases,
        mandatos=mandatos,
        resumo_presenca_2025=resumo_presenca_2025,
        total_proposicoes_parlamentares_2025=total_prod_2025,
        producao_por_tipo_2025=prod_tipos_2025,
        resumo_presenca_2026=resumo_presenca,
        total_proposicoes_parlamentares_2026=total_prod_2026,
        producao_por_tipo_2026=prod_tipos,
        proposicoes_recentes=props_recentes,
        votos_recentes_2025=votos_recentes_2025,
        votos_recentes_2026=votos_recentes,
        custo_estrutura_mandato_2026=custo_resumo_2026,
        proveniencia=_construir_proveniencia(ver),
    )


# -----------------------------------------------------------------------------
# 3. GET /api/v1/sessoes & GET /api/v1/sessoes/{id}
# -----------------------------------------------------------------------------


@app.get(
    "/api/v1/sessoes",
    response_model=PaginacaoOut[SessaoResumoOut],
    tags=["Sessões Plenárias"],
    summary="Lista sessões plenárias com filtros de ano, tipo, período e busca textual",
)
def listar_sessoes(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    ano: Annotated[int | None, Query(ge=2020, le=2030, description="Filtra pelo ano da sessão.")] = None,
    tipo_id: Annotated[int | None, Query(ge=1, description="Filtra pelo tipo_id_origem da sessão (ex.: 1 Ordinária, 2 Extraordinária).")] = None,
    data_inicio: Annotated[date | None, Query(description="Data inicial de abertura (YYYY-MM-DD).")] = None,
    data_fim: Annotated[date | None, Query(description="Data final de abertura (YYYY-MM-DD).")] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100, description="Busca textual no nome ou número da sessão.")] = None,
) -> PaginacaoOut[SessaoResumoOut]:
    filtros = ["s.municipio_id = %s", "s.valido_ate IS NULL"]
    params: list[Any] = [municipio_id]

    if ano is not None:
        filtros.append("s.ano = %s")
        params.append(ano)
    if tipo_id is not None:
        filtros.append("s.tipo_id_origem = %s")
        params.append(tipo_id)
    if data_inicio is not None:
        filtros.append("s.data_abertura >= %s")
        params.append(data_inicio)
    if data_fim is not None:
        filtros.append("s.data_abertura <= %s")
        params.append(data_fim)
    if q:
        termo = f"%{q.strip().lower()}%"
        filtros.append("(LOWER(s.nome_sessao) LIKE %s OR LOWER(s.numero) LIKE %s OR LOWER(s.slug) LIKE %s)")
        params.extend([termo, termo, termo])

    where_sql = " AND ".join(filtros)
    offset = (page - 1) * per_page

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM sessao s WHERE {where_sql}", params)
        total_row = cur.fetchone()
        total = int(total_row["total"]) if total_row else 0

        cur.execute(
            f"""
            WITH pres_cnt AS (
                SELECT
                    sessao_id,
                    COUNT(*) FILTER (WHERE status_normalizado = 'PRESENTE')::int AS presentes,
                    COUNT(*) FILTER (WHERE status_normalizado <> 'PRESENTE')::int AS ausentes
                FROM presenca
                WHERE municipio_id = %s
                GROUP BY sessao_id
            ),
            pauta_cnt AS (
                SELECT sessao_id, COUNT(*)::int AS itens
                FROM pauta_item
                WHERE municipio_id = %s
                GROUP BY sessao_id
            ),
            vot_cnt AS (
                SELECT sessao_id, COUNT(*)::int AS votacoes
                FROM votacao
                WHERE municipio_id = %s
                GROUP BY sessao_id
            )
            SELECT
                s.sessao_id,
                s.municipio_id,
                s.legislatura_id,
                s.id_origem_nexlegis,
                s.ids_origem_duplicados,
                s.tipo_id_origem,
                s.tipo_descricao,
                s.numero,
                s.ano,
                s.nome_sessao,
                s.slug,
                s.data_abertura,
                s.horario_abertura::text AS horario_abertura,
                s.data_encerramento,
                s.horario_encerramento::text AS horario_encerramento,
                s.quorum,
                s.ata_pdf_url,
                s.fonte_id,
                s.fonte_url,
                s.coletado_em,
                s.hash_conteudo,
                s.versao_coletor,
                COALESCE(pc.presentes, 0)::int AS total_presentes,
                COALESCE(pc.ausentes, 0)::int AS total_ausentes_ou_justificados,
                COALESCE(ptc.itens, 0)::int AS total_itens_pauta,
                COALESCE(vc.votacoes, 0)::int AS total_votacoes
            FROM sessao s
            LEFT JOIN pres_cnt pc ON pc.sessao_id = s.sessao_id
            LEFT JOIN pauta_cnt ptc ON ptc.sessao_id = s.sessao_id
            LEFT JOIN vot_cnt vc ON vc.sessao_id = s.sessao_id
            WHERE {where_sql}
            ORDER BY s.data_abertura DESC, s.id_origem_nexlegis DESC
            LIMIT %s OFFSET %s
            """,
            [municipio_id, municipio_id, municipio_id, *params, per_page, offset],
        )
        rows = cur.fetchall()

    items = [
        SessaoResumoOut(
            sessao_id=r["sessao_id"],
            municipio_id=r["municipio_id"],
            legislatura_id=r["legislatura_id"],
            id_origem_nexlegis=r["id_origem_nexlegis"],
            ids_origem_duplicados=list(r["ids_origem_duplicados"] or []),
            tipo_id_origem=r["tipo_id_origem"],
            tipo_descricao=r["tipo_descricao"],
            numero=r["numero"],
            ano=r["ano"],
            nome_sessao=r["nome_sessao"],
            slug=r["slug"],
            data_abertura=r["data_abertura"],
            horario_abertura=r["horario_abertura"],
            data_encerramento=r["data_encerramento"],
            horario_encerramento=r["horario_encerramento"],
            quorum=r["quorum"],
            ata_pdf_url=r["ata_pdf_url"],
            total_presentes=r["total_presentes"],
            total_ausentes_ou_justificados=r["total_ausentes_ou_justificados"],
            total_itens_pauta=r["total_itens_pauta"],
            total_votacoes=r["total_votacoes"],
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]

    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


@app.get(
    "/api/v1/sessoes/{id}",
    response_model=SessaoDetalheOut,
    tags=["Sessões Plenárias"],
    summary="Obtém os detalhes de uma sessão plenária, incluindo lista de presença, pauta e votações nominais",
)
def obter_sessao(
    conn: DbConnDep,
    id: Annotated[str, Path(min_length=1, max_length=200, description="sessao_id, id_origem_nexlegis ou slug.")],
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
) -> SessaoDetalheOut:
    id_num = int(id) if id.isdigit() else -1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.*,
                s.horario_abertura::text AS horario_abertura_txt,
                s.horario_encerramento::text AS horario_encerramento_txt
            FROM sessao s
            WHERE s.municipio_id = %s
              AND (s.sessao_id = %s OR s.slug = %s OR s.id_origem_nexlegis = %s)
            LIMIT 1
            """,
            (municipio_id, id, id, id_num),
        )
        ses = cur.fetchone()
        if ses is None:
            raise HTTPException(status_code=404, detail=f"Sessão '{id}' não encontrada.")

        sid = ses["sessao_id"]

        cur.execute(
            """
            SELECT
                pr.presenca_id, pr.vereador_id,
                v.nome_politico, v.nome_exibicao, v.slug,
                pr.situacao_id_origem, pr.situacao_descricao, pr.status_normalizado
            FROM presenca pr
            JOIN vereador v ON v.vereador_id = pr.vereador_id
            WHERE pr.municipio_id = %s AND pr.sessao_id = %s
            ORDER BY v.nome_exibicao ASC
            """,
            (municipio_id, sid),
        )
        presencas = [PresencaSessaoOut(**p) for p in cur.fetchall()]

        cur.execute(
            """
            SELECT
                pi.pauta_item_id, pi.ordem, pi.turno,
                pi.tipo_pauta_id_origem, pi.tipo_pauta_descricao,
                pi.proposicao_id, p.id_origem_nexlegis AS id_origem_proposicao,
                p.nome_materia, p.tipo_id_origem, p.tipo_descricao_origem,
                p.ementa, p.eh_proposicao_parlamentar,
                pi.unanime AS unanime_flag_api, pi.has_votos
            FROM pauta_item pi
            JOIN proposicao p ON p.proposicao_id = pi.proposicao_id
            WHERE pi.municipio_id = %s AND pi.sessao_id = %s
            ORDER BY pi.ordem ASC, pi.pauta_item_id ASC
            """,
            (municipio_id, sid),
        )
        pauta_itens = [PautaItemSessaoOut(**pi) for pi in cur.fetchall()]

        cur.execute(
            """
            SELECT
                vo.votacao_id, vo.id_origem_nexlegis, vo.proposicao_id,
                p.nome_materia, vo.tipo_turno_id,
                vo.unanime AS unanime_flag_api, vo.has_votos,
                vo.discussed_at, vo.started_at, vo.closed_at, vo.tempo_decorrido_segundos
            FROM votacao vo
            JOIN proposicao p ON p.proposicao_id = vo.proposicao_id
            WHERE vo.municipio_id = %s AND vo.sessao_id = %s
            ORDER BY vo.id_origem_nexlegis ASC
            """,
            (municipio_id, sid),
        )
        votacoes_rows = cur.fetchall()

        cur.execute(
            """
            SELECT
                vt.votacao_id, vt.voto_id, vt.vereador_id,
                v.nome_politico, v.nome_exibicao,
                vt.voto_id_origem, vt.voto_descricao, vt.voto_normalizado
            FROM voto vt
            JOIN votacao vo ON vo.votacao_id = vt.votacao_id
            JOIN vereador v ON v.vereador_id = vt.vereador_id
            WHERE vo.municipio_id = %s AND vo.sessao_id = %s
            ORDER BY v.nome_exibicao ASC
            """,
            (municipio_id, sid),
        )
        votos_por_votacao: dict[str, list[VotoNominalItemOut]] = {}
        for vr in cur.fetchall():
            vid_key = vr["votacao_id"]
            votos_por_votacao.setdefault(vid_key, []).append(
                VotoNominalItemOut(
                    voto_id=vr["voto_id"],
                    vereador_id=vr["vereador_id"],
                    nome_politico=vr["nome_politico"],
                    nome_exibicao=vr["nome_exibicao"],
                    voto_id_origem=vr["voto_id_origem"],
                    voto_descricao=vr["voto_descricao"],
                    voto_normalizado=vr["voto_normalizado"],
                )
            )

        votacoes_out: list[VotacaoSessaoOut] = []
        for vo in votacoes_rows:
            votos_lista = votos_por_votacao.get(vo["votacao_id"], [])
            votacoes_out.append(
                VotacaoSessaoOut(
                    votacao_id=vo["votacao_id"],
                    id_origem_nexlegis=vo["id_origem_nexlegis"],
                    proposicao_id=vo["proposicao_id"],
                    nome_materia=vo["nome_materia"],
                    tipo_turno_id=vo["tipo_turno_id"],
                    unanime_flag_api=vo["unanime_flag_api"],
                    has_votos=vo["has_votos"],
                    placar_favoravel=sum(1 for x in votos_lista if x.voto_normalizado == "FAVORAVEL"),
                    placar_contrario=sum(1 for x in votos_lista if x.voto_normalizado == "CONTRARIO"),
                    placar_abstencao=sum(1 for x in votos_lista if x.voto_normalizado == "ABSTENCAO"),
                    placar_ausente=sum(1 for x in votos_lista if x.voto_normalizado == "AUSENTE"),
                    discussed_at=vo["discussed_at"],
                    started_at=vo["started_at"],
                    closed_at=vo["closed_at"],
                    tempo_decorrido_segundos=vo["tempo_decorrido_segundos"],
                    votos_nominais=votos_lista,
                )
            )

    contagem_tipos_sessao: dict[str, int] = {}
    props_vistas: set[str] = set()
    for pi_item in pauta_itens:
        if pi_item.eh_proposicao_parlamentar and pi_item.proposicao_id not in props_vistas:
            props_vistas.add(pi_item.proposicao_id)
            contagem_tipos_sessao[pi_item.tipo_descricao_origem] = (
                contagem_tipos_sessao.get(pi_item.tipo_descricao_origem, 0) + 1
            )

    resumo_sessao = gerar_resumo_sessao(
        nome_sessao=ses["nome_sessao"],
        data_abertura=ses["data_abertura"],
        total_presentes=sum(1 for x in presencas if x.status_normalizado == "PRESENTE"),
        total_faltas_justificadas=sum(
            1 for x in presencas if x.status_normalizado == "FALTA_JUSTIFICADA"
        ),
        total_ausentes=sum(1 for x in presencas if x.status_normalizado == "AUSENTE"),
        total_licencas=sum(1 for x in presencas if x.status_normalizado == "LICENCA"),
        total_proposicoes_parlamentares=len(props_vistas),
        total_votacoes=len(votacoes_out),
        contagem_por_tipo=contagem_tipos_sessao,
        fonte_url=f"https://inhumas.nexlegis.com.br/sessoes/{ses['id_origem_nexlegis']}",
        coletado_em=ses["coletado_em"],
    )

    return SessaoDetalheOut(
        sessao_id=ses["sessao_id"],
        municipio_id=ses["municipio_id"],
        legislatura_id=ses["legislatura_id"],
        id_origem_nexlegis=ses["id_origem_nexlegis"],
        ids_origem_duplicados=list(ses["ids_origem_duplicados"] or []),
        tipo_id_origem=ses["tipo_id_origem"],
        tipo_descricao=ses["tipo_descricao"],
        numero=ses["numero"],
        ano=ses["ano"],
        nome_sessao=ses["nome_sessao"],
        slug=ses["slug"],
        data_abertura=ses["data_abertura"],
        horario_abertura=ses["horario_abertura_txt"],
        data_encerramento=ses["data_encerramento"],
        horario_encerramento=ses["horario_encerramento_txt"],
        inicio_sessao_real=ses["inicio_sessao_real"],
        presidente_vereador_id=ses["presidente_vereador_id"],
        quorum=ses["quorum"],
        ata_pdf_url=ses["ata_pdf_url"],
        presencas=presencas,
        pauta_itens=pauta_itens,
        votacoes=votacoes_out,
        resumo_cidadao=resumo_sessao,
        proveniencia=_construir_proveniencia(ses),
    )


# -----------------------------------------------------------------------------
# 4. GET /api/v1/materias & GET /api/v1/materias/{id}
# -----------------------------------------------------------------------------


@app.get(
    "/api/v1/materias",
    response_model=PaginacaoOut[MateriaResumoOut],
    tags=["Matérias e Proposições"],
    summary="Lista matérias e proposições com filtros por tipo, classificação ADR-005, autor e busca textual",
)
def listar_materias(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    ano: Annotated[int | None, Query(ge=2020, le=2030, description="Filtra pelo ano da matéria.")] = None,
    tipo_id: Annotated[int | None, Query(ge=1, description="Filtra pelo tipo_id_origem (ex.: 5 Requerimento, 113 PL do Legislativo, 144 Ata).")] = None,
    eh_proposicao_parlamentar: Annotated[
        bool | None,
        Query(description="Se True, exclui atas (144/145), julgamentos de contas (211), balanços (213) e atos externos conforme ADR-005."),
    ] = None,
    vereador_id: Annotated[
        str | None,
        Query(min_length=1, max_length=64, description="Filtra matérias que tenham o vereador informado como autor."),
    ] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=120, description="Busca textual na ementa ou nome da matéria."),
    ] = None,
) -> PaginacaoOut[MateriaResumoOut]:
    filtros = ["p.municipio_id = %s", "p.valido_ate IS NULL"]
    params: list[Any] = [municipio_id]

    if ano is not None:
        filtros.append("p.ano = %s")
        params.append(ano)
    if tipo_id is not None:
        filtros.append("p.tipo_id_origem = %s")
        params.append(tipo_id)
    if eh_proposicao_parlamentar is not None:
        filtros.append("p.eh_proposicao_parlamentar = %s")
        params.append(eh_proposicao_parlamentar)
    if vereador_id:
        vid_num = int(vereador_id) if vereador_id.isdigit() else -1
        filtros.append(
            """
            EXISTS (
                SELECT 1
                FROM autoria ax
                JOIN vereador vx ON vx.vereador_id = ax.vereador_id
                WHERE ax.proposicao_id = p.proposicao_id
                  AND (vx.vereador_id = %s OR vx.slug = %s OR vx.id_origem_nexlegis = %s)
            )
            """
        )
        params.extend([vereador_id, vereador_id, vid_num])
    if q:
        termo = f"%{q.strip().lower()}%"
        filtros.append("(LOWER(p.nome_materia) LIKE %s OR LOWER(p.ementa) LIKE %s)")
        params.extend([termo, termo])

    where_sql = " AND ".join(filtros)
    offset = (page - 1) * per_page

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM proposicao p WHERE {where_sql}", params)
        total_row = cur.fetchone()
        total = int(total_row["total"]) if total_row else 0

        cur.execute(
            f"""
            SELECT *
            FROM proposicao p
            WHERE {where_sql}
            ORDER BY p.ano DESC, p.id_origem_nexlegis DESC
            LIMIT %s OFFSET %s
            """,
            [*params, per_page, offset],
        )
        props_rows = cur.fetchall()

        prop_ids = [r["proposicao_id"] for r in props_rows]
        autores_por_prop: dict[str, list[AutorMateriaOut]] = {}
        if prop_ids:
            cur.execute(
                """
                SELECT
                    a.autoria_id, a.proposicao_id, a.tipo_autor,
                    a.vereador_id, a.autor_institucional,
                    v.nome_politico, v.nome_exibicao, v.slug
                FROM autoria a
                LEFT JOIN vereador v ON v.vereador_id = a.vereador_id
                WHERE a.municipio_id = %s AND a.proposicao_id = ANY(%s)
                ORDER BY a.autoria_id ASC
                """,
                (municipio_id, prop_ids),
            )
            for ar in cur.fetchall():
                autores_por_prop.setdefault(ar["proposicao_id"], []).append(
                    AutorMateriaOut(
                        autoria_id=ar["autoria_id"],
                        tipo_autor=ar["tipo_autor"],
                        vereador_id=ar["vereador_id"],
                        nome_politico=ar["nome_politico"],
                        nome_exibicao=ar["nome_exibicao"],
                        slug=ar["slug"],
                        autor_institucional=ar["autor_institucional"],
                    )
                )

    items = [
        MateriaResumoOut(
            proposicao_id=r["proposicao_id"],
            municipio_id=r["municipio_id"],
            id_origem_nexlegis=r["id_origem_nexlegis"],
            tipo_id_origem=r["tipo_id_origem"],
            tipo_descricao_origem=r["tipo_descricao_origem"],
            numero=r["numero"],
            ano=r["ano"],
            nome_materia=r["nome_materia"],
            slug=r["slug"],
            ementa=r["ementa"],
            data_publicacao=r["data_publicacao"],
            ultima_movimentacao=r["ultima_movimentacao"],
            situacao_atual=r["situacao_atual"],
            categoria_classificada=r["categoria_classificada"],
            eh_proposicao_parlamentar=r["eh_proposicao_parlamentar"],
            contabilizar_producao_vereador=r["contabilizar_producao_vereador"],
            autores=autores_por_prop.get(r["proposicao_id"], []),
            proveniencia=_construir_proveniencia(r),
        )
        for r in props_rows
    ]

    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


@app.get(
    "/api/v1/materias/{id}",
    response_model=MateriaDetalheOut,
    tags=["Matérias e Proposições"],
    summary="Obtém os detalhes de uma matéria/proposição, incluindo classificação, autores, tramitações e votações",
)
def obter_materia(
    conn: DbConnDep,
    id: Annotated[str, Path(min_length=1, max_length=220, description="proposicao_id, id_origem_nexlegis ou slug.")],
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
) -> MateriaDetalheOut:
    id_num = int(id) if id.isdigit() else -1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.*, tp.justificativa_classificacao
            FROM proposicao p
            LEFT JOIN de_para_tipo_proposicao tp
                ON tp.municipio_id = p.municipio_id
               AND tp.tipo_id_origem = p.tipo_id_origem
            WHERE p.municipio_id = %s
              AND (p.proposicao_id = %s OR p.slug = %s OR p.id_origem_nexlegis = %s)
            LIMIT 1
            """,
            (municipio_id, id, id, id_num),
        )
        prop = cur.fetchone()
        if prop is None:
            raise HTTPException(status_code=404, detail=f"Matéria '{id}' não encontrada.")

        pid = prop["proposicao_id"]

        cur.execute(
            """
            SELECT
                a.autoria_id, a.tipo_autor, a.vereador_id,
                a.autor_institucional, v.nome_politico, v.nome_exibicao, v.slug
            FROM autoria a
            LEFT JOIN vereador v ON v.vereador_id = a.vereador_id
            WHERE a.municipio_id = %s AND a.proposicao_id = %s
            ORDER BY a.autoria_id ASC
            """,
            (municipio_id, pid),
        )
        autores = [AutorMateriaOut(**a) for a in cur.fetchall()]

        cur.execute(
            """
            SELECT
                tramitacao_id, id_origem_nexlegis, data_tramitacao,
                local_origem, local_destino, situacao_descricao,
                prioridade_descricao, prazo_descricao, justificativa
            FROM tramitacao
            WHERE municipio_id = %s AND proposicao_id = %s
            ORDER BY data_tramitacao DESC, id_origem_nexlegis DESC
            """,
            (municipio_id, pid),
        )
        tramitacoes = [TramitacaoMateriaOut(**t) for t in cur.fetchall()]

        cur.execute(
            """
            SELECT
                s.sessao_id, s.id_origem_nexlegis AS id_origem_sessao,
                s.nome_sessao, s.data_abertura AS data_sessao,
                pi.ordem, pi.turno, pi.tipo_pauta_descricao,
                vo.votacao_id
            FROM pauta_item pi
            JOIN sessao s ON s.sessao_id = pi.sessao_id
            LEFT JOIN votacao vo
                ON vo.sessao_id = pi.sessao_id
               AND vo.proposicao_id = pi.proposicao_id
            WHERE pi.municipio_id = %s AND pi.proposicao_id = %s
            ORDER BY s.data_abertura DESC, pi.ordem ASC
            """,
            (municipio_id, pid),
        )
        delib_rows = cur.fetchall()

        deliberacoes: list[DeliberacaoMateriaSessaoOut] = []
        for d in delib_rows:
            votos_nominais: list[VotoNominalItemOut] = []
            if d["votacao_id"]:
                cur.execute(
                    """
                    SELECT
                        vt.voto_id, vt.vereador_id,
                        v.nome_politico, v.nome_exibicao,
                        vt.voto_id_origem, vt.voto_descricao, vt.voto_normalizado
                    FROM voto vt
                    JOIN vereador v ON v.vereador_id = vt.vereador_id
                    WHERE vt.municipio_id = %s AND vt.votacao_id = %s
                    ORDER BY v.nome_exibicao ASC
                    """,
                    (municipio_id, d["votacao_id"]),
                )
                votos_nominais = [VotoNominalItemOut(**vr) for vr in cur.fetchall()]

            deliberacoes.append(
                DeliberacaoMateriaSessaoOut(
                    sessao_id=d["sessao_id"],
                    id_origem_sessao=d["id_origem_sessao"],
                    nome_sessao=d["nome_sessao"],
                    data_sessao=d["data_sessao"],
                    ordem=d["ordem"],
                    turno=d["turno"],
                    tipo_pauta_descricao=d["tipo_pauta_descricao"],
                    votacao_id=d["votacao_id"],
                    placar_favoravel=sum(1 for x in votos_nominais if x.voto_normalizado == "FAVORAVEL"),
                    placar_contrario=sum(1 for x in votos_nominais if x.voto_normalizado == "CONTRARIO"),
                    placar_abstencao=sum(1 for x in votos_nominais if x.voto_normalizado == "ABSTENCAO"),
                    votos_nominais=votos_nominais,
                )
            )

    autores_nomes_mat = [
        a.nome_exibicao or a.autor_institucional
        for a in autores
        if (a.nome_exibicao or a.autor_institucional)
    ]
    placar_mat: str | None = None
    if deliberacoes:
        d0 = deliberacoes[0]
        if d0.placar_favoravel or d0.placar_contrario or d0.placar_abstencao:
            placar_mat = (
                f"{d0.placar_favoravel} favorável(is), {d0.placar_contrario} contrário(s), "
                f"{d0.placar_abstencao} abstenção(ões) na {d0.nome_sessao}"
            )
    resumo_mat = gerar_resumo_materia(
        nome_materia=prop["nome_materia"],
        tipo_descricao=prop["tipo_descricao_origem"],
        ementa=prop["ementa"],
        autores_nomes=autores_nomes_mat,
        situacao_atual=prop["situacao_atual"],
        data_referencia=prop["ultima_movimentacao"] or prop["data_publicacao"],
        placar_resumo=placar_mat,
        fonte_url=f"https://inhumas.nexlegis.com.br/materias/{prop['id_origem_nexlegis']}",
        coletado_em=prop["coletado_em"],
    )

    return MateriaDetalheOut(
        proposicao_id=prop["proposicao_id"],
        municipio_id=prop["municipio_id"],
        id_origem_nexlegis=prop["id_origem_nexlegis"],
        tipo_id_origem=prop["tipo_id_origem"],
        tipo_descricao_origem=prop["tipo_descricao_origem"],
        numero=prop["numero"],
        ano=prop["ano"],
        nome_materia=prop["nome_materia"],
        slug=prop["slug"],
        ementa=prop["ementa"],
        data_publicacao=prop["data_publicacao"],
        ultima_movimentacao=prop["ultima_movimentacao"],
        situacao_atual=prop["situacao_atual"],
        local_origem=prop["local_origem"],
        local_destino=prop["local_destino"],
        autoria_codigo_origem=prop["autoria_codigo_origem"],
        anexo_principal_url=prop["anexo_principal_url"],
        anexo_principal_nome=prop["anexo_principal_nome"],
        anexo_principal_mime=prop["anexo_principal_mime"],
        anexo_principal_tamanho=prop["anexo_principal_tamanho"],
        categoria_classificada=prop["categoria_classificada"],
        eh_proposicao_parlamentar=prop["eh_proposicao_parlamentar"],
        contabilizar_producao_vereador=prop["contabilizar_producao_vereador"],
        justificativa_classificacao=prop["justificativa_classificacao"],
        autores=autores,
        tramitacoes=tramitacoes,
        deliberacoes_em_sessao=deliberacoes,
        resumo_cidadao=resumo_mat,
        proveniencia=_construir_proveniencia(prop),
    )


# -----------------------------------------------------------------------------
# 5. Transparência CENTI/NúcleoGov e Custo da Estrutura do Mandato (Fase 2 — 2026)
# -----------------------------------------------------------------------------


@app.get(
    "/api/v1/transparencia/custo-mandato",
    response_model=PaginacaoOut[CustoMandatoMensalOut],
    tags=["Transparência Financeira (2026)"],
    summary="Lista a série mensal do Custo da Estrutura do Mandato (Subsídio + Folha Gabinete + Diárias)",
)
def listar_custo_mandato(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    ano: Annotated[int, Query(ge=2020, le=2030)] = 2026,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    vereador_id: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
    status_competencia: Annotated[
        str | None,
        Query(pattern="^(FECHADA|ABERTA_SEM_PUBLICACAO|LACUNA_PARCIAL_LOTACAO)$"),
    ] = None,
) -> PaginacaoOut[CustoMandatoMensalOut]:
    filtros = ["c.municipio_id = %s", "c.ano = %s"]
    params: list[Any] = [municipio_id, ano]
    if mes is not None:
        filtros.append("c.mes = %s")
        params.append(mes)
    if vereador_id:
        filtros.append("c.vereador_id = %s")
        params.append(vereador_id)
    if status_competencia:
        filtros.append("c.competencia_status = %s")
        params.append(status_competencia)

    where_sql = " AND ".join(filtros)
    offset = (page - 1) * per_page

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) AS total FROM custo_estrutura_mandato_mensal c WHERE {where_sql}",
            params,
        )
        total = int((cur.fetchone() or {"total": 0})["total"])
        cur.execute(
            f"""
            SELECT c.*, v.nome_politico, v.nome_exibicao
            FROM custo_estrutura_mandato_mensal c
            JOIN vereador v ON v.vereador_id = c.vereador_id
            WHERE {where_sql}
            ORDER BY c.ano DESC, c.mes DESC, v.nome_exibicao ASC
            LIMIT %s OFFSET %s
            """,
            [*params, per_page, offset],
        )
        rows = cur.fetchall()

    items = [
        CustoMandatoMensalOut(
            custo_mensal_id=r["custo_mensal_id"],
            vereador_id=r["vereador_id"],
            nome_politico=r["nome_politico"],
            nome_exibicao=r["nome_exibicao"],
            ano=r["ano"],
            mes=r["mes"],
            competencia_status=r["competencia_status"],
            subsidio_bruto_vereador=r["subsidio_bruto_vereador"],
            subsidio_mensal_base=r["subsidio_mensal_base"],
            adicionais_ferias_decimo_terceiro_vereador=r["adicionais_ferias_decimo_terceiro_vereador"],
            folha_bruta_gabinete=r["folha_bruta_gabinete"],
            folha_mensal_gabinete=r["folha_mensal_gabinete"],
            adicionais_ferias_decimo_terceiro_gabinete=r["adicionais_ferias_decimo_terceiro_gabinete"],
            quantidade_servidores_gabinete=r["quantidade_servidores_gabinete"],
            diarias_atribuiveis_empenhadas=r["diarias_atribuiveis_empenhadas"],
            diarias_atribuiveis_liquidadas=r["diarias_atribuiveis_liquidadas"],
            diarias_atribuiveis_pagas=r["diarias_atribuiveis_pagas"],
            custo_estrutura_mandato_total=r["custo_estrutura_mandato_total"],
            nota_cota_parlamentar=r["nota_cota_parlamentar"],
            periodo_declaracao_ceap=r["periodo_declaracao_ceap"],
            metodologia_resumo=r["metodologia_resumo"],
            limitacoes_dados=r["limitacoes_dados"],
            avisos=list(r["avisos"] or []),
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]
    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


@app.get(
    "/api/v1/transparencia/folha",
    response_model=PaginacaoOut[FolhaPagamentoOut],
    tags=["Transparência Financeira (2026)"],
    summary="Lista registros da folha de pagamento (sem CPF completo, LGPD)",
)
def listar_folha_pagamento(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    ano: Annotated[int, Query(ge=2020, le=2030)] = 2026,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    vereador_id: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
    gabinete_vereador_id: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
    apenas_vereadores: Annotated[bool, Query()] = False,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> PaginacaoOut[FolhaPagamentoOut]:
    filtros = ["municipio_id = %s", "ano = %s"]
    params: list[Any] = [municipio_id, ano]
    if mes is not None:
        filtros.append("mes = %s")
        params.append(mes)
    if vereador_id:
        filtros.append("vereador_id = %s")
        params.append(vereador_id)
    if gabinete_vereador_id:
        filtros.append("gabinete_vereador_id = %s")
        params.append(gabinete_vereador_id)
    if apenas_vereadores:
        filtros.append("eh_vereador = TRUE")
    if q:
        termo = f"%{q.strip().lower()}%"
        filtros.append("(LOWER(nome_servidor) LIKE %s OR LOWER(cargo) LIKE %s OR LOWER(lotacao) LIKE %s)")
        params.extend([termo, termo, termo])

    where_sql = " AND ".join(filtros)
    offset = (page - 1) * per_page

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM folha_pagamento WHERE {where_sql}", params)
        total = int((cur.fetchone() or {"total": 0})["total"])
        cur.execute(
            f"""
            SELECT *
            FROM folha_pagamento
            WHERE {where_sql}
            ORDER BY ano DESC, mes DESC, nome_servidor ASC, tipo_folha ASC
            LIMIT %s OFFSET %s
            """,
            [*params, per_page, offset],
        )
        rows = cur.fetchall()

    items = [
        FolhaPagamentoOut(
            folha_id=r["folha_id"],
            ano=r["ano"],
            mes=r["mes"],
            referencia=r["referencia"],
            matricula=r["matricula"],
            nome_servidor=r["nome_servidor"],
            cpf_mascarado=r["cpf_mascarado"],
            situacao=r["situacao"],
            orgao=r["orgao"],
            cargo=r["cargo"],
            funcao=r["funcao"],
            lotacao=r["lotacao"],
            data_admissao=r["data_admissao"],
            data_exoneracao=r["data_exoneracao"],
            tipo_admissao=r["tipo_admissao"],
            tipo_folha=r["tipo_folha"],
            movimentacao=r["movimentacao"],
            salario_base=r["salario_base"],
            remuneracao_bruta=r["remuneracao_bruta"],
            descontos=r["descontos"],
            remuneracao_liquida=r["remuneracao_liquida"],
            eh_vereador=r["eh_vereador"],
            vereador_id=r["vereador_id"],
            gabinete_vereador_id=r["gabinete_vereador_id"],
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]
    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


def _filtros_despesas(
    municipio_id: str,
    ano: int,
    mes: int | None,
    eh_diaria: bool | None,
    q: str | None,
    data_inicio: date | None,
    data_fim: date | None,
    fornecedor_id: str | None,
    elemento_despesa: str | None,
) -> tuple[str, list[Any]]:
    """Monta o WHERE parametrizado compartilhado pela listagem e pelo resumo de despesas."""
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=422, detail="data_inicio deve ser anterior ou igual a data_fim."
        )
    filtros = ["municipio_id = %s", "ano = %s"]
    params: list[Any] = [municipio_id, ano]
    if mes is not None:
        filtros.append("mes = %s")
        params.append(mes)
    if eh_diaria is not None:
        filtros.append("eh_diaria = %s")
        params.append(eh_diaria)
    if data_inicio is not None:
        filtros.append("data_empenho >= %s")
        params.append(data_inicio)
    if data_fim is not None:
        filtros.append("data_empenho <= %s")
        params.append(data_fim)
    if fornecedor_id:
        filtros.append("fornecedor_id = %s")
        params.append(fornecedor_id)
    if elemento_despesa:
        filtros.append("elemento_despesa = %s")
        params.append(elemento_despesa)
    if q:
        termo = f"%{q.strip().lower()}%"
        filtros.append(
            "(LOWER(favorecido_nome) LIKE %s OR LOWER(historico) LIKE %s OR numero_empenho LIKE %s)"
        )
        params.extend([termo, termo, termo])
    return " AND ".join(filtros), params


FiltroDataInicio = Annotated[
    date | None, Query(description="Data inicial do empenho (inclusive), AAAA-MM-DD.")
]
FiltroDataFim = Annotated[
    date | None, Query(description="Data final do empenho (inclusive), AAAA-MM-DD.")
]
FiltroFornecedor = Annotated[
    str | None,
    Query(min_length=2, max_length=80, description="Identificador do favorecido (fornecedor_id)."),
]
FiltroElemento = Annotated[
    str | None,
    Query(
        min_length=2,
        max_length=160,
        description="Elemento de despesa exatamente como publicado (ex.: '30 - Material de Consumo').",
    ),
]


@app.get(
    "/api/v1/transparencia/despesas",
    response_model=PaginacaoOut[DespesaEmpenhoOut],
    tags=["Transparência Financeira (2026)"],
    summary="Lista empenhos, liquidações e pagamentos de 2026 (com separação estrita dos estágios)",
)
def listar_despesas(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    ano: Annotated[int, Query(ge=2020, le=2030)] = 2026,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    eh_diaria: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    data_inicio: FiltroDataInicio = None,
    data_fim: FiltroDataFim = None,
    fornecedor_id: FiltroFornecedor = None,
    elemento_despesa: FiltroElemento = None,
) -> PaginacaoOut[DespesaEmpenhoOut]:
    where_sql, params = _filtros_despesas(
        municipio_id, ano, mes, eh_diaria, q, data_inicio, data_fim, fornecedor_id, elemento_despesa
    )
    offset = (page - 1) * per_page

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM despesa_empenho WHERE {where_sql}", params)
        total = int((cur.fetchone() or {"total": 0})["total"])
        cur.execute(
            f"""
            SELECT *
            FROM despesa_empenho
            WHERE {where_sql}
            ORDER BY data_empenho DESC, numero_empenho DESC
            LIMIT %s OFFSET %s
            """,
            [*params, per_page, offset],
        )
        rows = cur.fetchall()

    items = [
        DespesaEmpenhoOut(
            empenho_id=r["empenho_id"],
            numero_empenho=r["numero_empenho"],
            ano=r["ano"],
            mes=r["mes"],
            data_empenho=r["data_empenho"],
            fornecedor_id=r["fornecedor_id"],
            favorecido_nome=r["favorecido_nome"],
            documento_favorecido=r["documento_favorecido"],
            tipo_pessoa_favorecido=r["tipo_pessoa_favorecido"],
            valor_empenhado_bruto=r["valor_empenhado_bruto"],
            valor_anulacao=r["valor_anulacao"],
            valor_empenhado_liquido=r["valor_empenhado_liquido"],
            valor_liquidado=r["valor_liquidado"],
            valor_pago=r["valor_pago"],
            saldo_pagar=r["saldo_pagar"],
            historico=r["historico"],
            processo_licitatorio=r["processo_licitatorio"],
            elemento_despesa=r["elemento_despesa"],
            subelemento_despesa=r["subelemento_despesa"],
            fonte_recurso=r["fonte_recurso"],
            eh_diaria=r["eh_diaria"],
            vereador_beneficiario_id=r["vereador_beneficiario_id"],
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]
    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


_SQL_SOMAS_DESPESA = """
    COUNT(*) AS quantidade_empenhos,
    COALESCE(SUM(valor_empenhado_bruto), 0) AS valor_empenhado_bruto,
    COALESCE(SUM(valor_anulacao), 0) AS valor_anulacao,
    COALESCE(SUM(valor_empenhado_liquido), 0) AS valor_empenhado_liquido,
    COALESCE(SUM(valor_liquidado), 0) AS valor_liquidado,
    COALESCE(SUM(valor_pago), 0) AS valor_pago,
    COALESCE(SUM(saldo_pagar), 0) AS saldo_pagar
"""

_CAMPOS_TOTAIS_DESPESA = (
    "quantidade_empenhos",
    "valor_empenhado_bruto",
    "valor_anulacao",
    "valor_empenhado_liquido",
    "valor_liquidado",
    "valor_pago",
    "saldo_pagar",
)


@app.get(
    "/api/v1/transparencia/despesas/resumo",
    response_model=DespesasResumoOut,
    tags=["Transparência Financeira (2026)"],
    summary="Totais por estágio da despesa, por elemento e lista de favorecidos (mesmos filtros da listagem)",
)
def resumir_despesas(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    ano: Annotated[int, Query(ge=2020, le=2030)] = 2026,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    eh_diaria: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    data_inicio: FiltroDataInicio = None,
    data_fim: FiltroDataFim = None,
    fornecedor_id: FiltroFornecedor = None,
    elemento_despesa: FiltroElemento = None,
) -> DespesasResumoOut:
    where_sql, params = _filtros_despesas(
        municipio_id, ano, mes, eh_diaria, q, data_inicio, data_fim, fornecedor_id, elemento_despesa
    )
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_SQL_SOMAS_DESPESA},
                   MIN(data_empenho) AS data_primeiro_empenho,
                   MAX(data_empenho) AS data_ultimo_empenho,
                   MAX(coletado_em) AS ultima_coleta_em,
                   MIN(fonte_url) AS fonte_url
            FROM despesa_empenho
            WHERE {where_sql}
            """,
            params,
        )
        tot = cur.fetchone() or {}
        cur.execute(
            f"""
            SELECT elemento_despesa, {_SQL_SOMAS_DESPESA}
            FROM despesa_empenho
            WHERE {where_sql}
            GROUP BY elemento_despesa
            ORDER BY elemento_despesa NULLS LAST
            """,
            params,
        )
        elementos = cur.fetchall()
        cur.execute(
            f"""
            SELECT fornecedor_id,
                   MIN(favorecido_nome) AS favorecido_nome,
                   MIN(documento_favorecido) AS documento_favorecido,
                   MIN(tipo_pessoa_favorecido) AS tipo_pessoa_favorecido,
                   {_SQL_SOMAS_DESPESA}
            FROM despesa_empenho
            WHERE {where_sql}
            GROUP BY fornecedor_id
            ORDER BY MIN(favorecido_nome), fornecedor_id
            """,
            params,
        )
        favorecidos = cur.fetchall()

    return DespesasResumoOut(
        ano=ano,
        data_primeiro_empenho=tot.get("data_primeiro_empenho"),
        data_ultimo_empenho=tot.get("data_ultimo_empenho"),
        totais=TotaisDespesaOut(**{k: tot.get(k, 0) for k in _CAMPOS_TOTAIS_DESPESA}),
        por_elemento=[
            DespesaPorElementoOut(
                elemento_despesa=e["elemento_despesa"],
                **{k: e[k] for k in _CAMPOS_TOTAIS_DESPESA},
            )
            for e in elementos
        ],
        favorecidos=[
            FavorecidoDespesaOut(
                fornecedor_id=f["fornecedor_id"],
                favorecido_nome=f["favorecido_nome"],
                documento_favorecido=f["documento_favorecido"],
                tipo_pessoa_favorecido=f["tipo_pessoa_favorecido"],
                **{k: f[k] for k in _CAMPOS_TOTAIS_DESPESA},
            )
            for f in favorecidos
        ],
        nota_metodologica=(
            "Somas calculadas diretamente no banco a partir dos empenhos publicados no Portal da "
            "Transparência. Empenho líquido = empenho bruto − anulações. Liquidado e pago são "
            "estágios posteriores e não devem ser somados ao empenhado."
        ),
        fonte_url=tot.get("fonte_url"),
        ultima_coleta_em=tot.get("ultima_coleta_em"),
    )


@app.get(
    "/api/v1/transparencia/diarias",
    response_model=PaginacaoOut[DiariaOut],
    tags=["Transparência Financeira (2026)"],
    summary="Lista diárias identificadas no cruzamento contábil (Elemento 14 - Diárias Civil)",
)
def listar_diarias(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    ano: Annotated[int, Query(ge=2020, le=2030)] = 2026,
    vereador_id: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
) -> PaginacaoOut[DiariaOut]:
    filtros = ["municipio_id = %s", "ano = %s"]
    params: list[Any] = [municipio_id, ano]
    if vereador_id:
        filtros.append("vereador_id_verificado = %s")
        params.append(vereador_id)

    where_sql = " AND ".join(filtros)
    offset = (page - 1) * per_page

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM diaria WHERE {where_sql}", params)
        total = int((cur.fetchone() or {"total": 0})["total"])
        cur.execute(
            f"""
            SELECT * FROM diaria
            WHERE {where_sql}
            ORDER BY data_concessao DESC, numero_empenho DESC
            LIMIT %s OFFSET %s
            """,
            [*params, per_page, offset],
        )
        rows = cur.fetchall()

    items = [
        DiariaOut(
            diaria_id=r["diaria_id"],
            empenho_id=r["empenho_id"],
            numero_empenho=r["numero_empenho"],
            ano=r["ano"],
            mes=r["mes"],
            data_concessao=r["data_concessao"],
            beneficiario_nome=r["beneficiario_nome"],
            cpf_mascarado=r["cpf_mascarado"],
            tipo_beneficiario=r["tipo_beneficiario"],
            vereador_id_verificado=r["vereador_id_verificado"],
            gabinete_vereador_id=r["gabinete_vereador_id"],
            cargo_beneficiario=r["cargo_beneficiario"],
            identificacao_documental_verificavel=r["identificacao_documental_verificavel"],
            destino_ou_finalidade=r["destino_ou_finalidade"],
            valor_empenhado_liquido=r["valor_empenhado_liquido"],
            valor_liquidado=r["valor_liquidado"],
            valor_pago=r["valor_pago"],
            origem_registro=r["origem_registro"],
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]
    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


@app.get(
    "/api/v1/transparencia/duodecimo",
    response_model=PaginacaoOut[DuodecimoOut],
    tags=["Transparência Financeira (2026)"],
    summary="Lista repasses e devoluções de duodécimo de 2026",
)
def listar_duodecimo(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 30,
    ano: Annotated[int, Query(ge=2020, le=2030)] = 2026,
) -> PaginacaoOut[DuodecimoOut]:
    offset = (page - 1) * per_page
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS total FROM receita_duodecimo WHERE municipio_id = %s AND ano = %s",
            (municipio_id, ano),
        )
        total = int((cur.fetchone() or {"total": 0})["total"])
        cur.execute(
            """
            SELECT * FROM receita_duodecimo
            WHERE municipio_id = %s AND ano = %s
            ORDER BY data_lancamento DESC, id_origem DESC
            LIMIT %s OFFSET %s
            """,
            (municipio_id, ano, per_page, offset),
        )
        rows = cur.fetchall()

    items = [
        DuodecimoOut(
            duodecimo_id=r["duodecimo_id"],
            id_origem=r["id_origem"],
            ano=r["ano"],
            mes=r["mes"],
            data_lancamento=r["data_lancamento"],
            tipo_codigo=r["tipo_codigo"],
            tipo_natureza=r["tipo_natureza"],
            descricao=r["descricao"],
            valor=r["valor"],
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]
    return PaginacaoOut(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=_calcular_total_pages(total, per_page),
        items=items,
    )


@app.get(
    "/api/v1/transparencia/declaracoes",
    response_model=list[DeclaracaoTransparenciaOut],
    tags=["Transparência Financeira (2026)"],
    summary="Lista declarações oficiais da Câmara (inexistência de CEAP e não concessão de diárias)",
)
def listar_declaracoes_transparencia(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
) -> list[DeclaracaoTransparenciaOut]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT * FROM declaracao_oficial_transparencia
            WHERE municipio_id = %s
            ORDER BY tipo_declaracao ASC
            """,
            (municipio_id,),
        )
        rows = cur.fetchall()
    return [
        DeclaracaoTransparenciaOut(
            declaracao_id=r["declaracao_id"],
            tipo_declaracao=r["tipo_declaracao"],
            titulo_oficial=r["titulo_oficial"],
            texto_integral=r["texto_integral"],
            data_inicio_cobertura=r["data_inicio_cobertura"],
            data_fim_cobertura=r["data_fim_cobertura"],
            data_atualizacao=r["data_atualizacao"],
            signatario_presidente=r["signatario_presidente"],
            signatario_certificador=r["signatario_certificador"],
            observacao_cruzamento=r["observacao_cruzamento"],
            proveniencia=_construir_proveniencia(r),
        )
        for r in rows
    ]

