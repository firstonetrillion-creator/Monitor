"""Endpoints somente leitura da Fase 5 — Busca Avançada, Bairros, Legislação e Comparativo SICONFI."""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from cerrado_aberto_api.db import obter_conexao_db
from cerrado_aberto_api.resumos import gerar_resumo_materia
from cerrado_aberto_api.schemas import ProvenienciaOut
from cerrado_aberto_api.schemas_fase5 import (
    BairroDetalheOut,
    BairroResumoOut,
    BairrosPainelOut,
    BuscaUnificadaOut,
    ComparativoMunicipioOut,
    ComparativoSiconfiOut,
    ItemBuscaOut,
    NormaDetalheOut,
    NormaResumoOut,
    NormasListagemOut,
    ProposicaoBairroItemOut,
    TemaContagemOut,
    VereadorBairroContagemOut,
)

router = APIRouter(tags=["Aprofundamento e Dados Abertos (Fase 5)"])
DbConnDep = Annotated[psycopg.Connection[dict[str, Any]], Depends(obter_conexao_db)]

_CategoriaBusca = Literal["todos", "proposicoes", "normas", "vereadores", "sessoes", "despesas"]


def _trecho_seguro(texto: str | None, limite: int = 240) -> str | None:
    if not texto:
        return None
    limpo = " ".join(texto.split())
    if len(limpo) <= limite:
        return limpo
    return f"{limpo[: limite - 1].rstrip()}…"


@router.get(
    "/api/v1/busca",
    response_model=BuscaUnificadaOut,
    summary="Busca avançada unificada em linguagem natural (Full-Text Search PostgreSQL em português)",
)
def buscar_unificado(
    conn: DbConnDep,
    q: Annotated[str, Query(min_length=2, max_length=160, description="Termo de busca (assunto, bairro, vereador, fornecedor ou número de lei)")],
    categoria: Annotated[_CategoriaBusca, Query()] = "todos",
    ano: Annotated[int | None, Query(ge=1988, le=2100)] = None,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> BuscaUnificadaOut:
    termo = " ".join(q.strip().split())
    like_pat = f"%{termo}%"
    itens: list[ItemBuscaOut] = []
    contagens: dict[str, int] = {
        "proposicoes": 0,
        "normas": 0,
        "vereadores": 0,
        "sessoes": 0,
        "despesas": 0,
    }

    with conn.cursor() as cur:
        # 1. Proposições legislativas
        sql_prop_where = """
            WHERE p.municipio_id = %s
              AND p.eh_proposicao_parlamentar = TRUE
              AND (
                to_tsvector('portuguese', normalizar_texto_busca(COALESCE(p.nome_materia,'') || ' ' || COALESCE(p.tipo_descricao_origem,'') || ' ' || COALESCE(p.ementa,'')))
                @@ websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                OR normalizar_texto_busca(COALESCE(p.nome_materia,'') || ' ' || COALESCE(p.ementa,'')) LIKE normalizar_texto_busca(%s)
              )
        """
        params_prop: list[Any] = [municipio_id, termo, like_pat]
        if ano is not None:
            sql_prop_where += " AND p.ano = %s"
            params_prop.append(ano)

        cur.execute(f"SELECT COUNT(*)::int AS c FROM proposicao p {sql_prop_where}", params_prop)
        contagens["proposicoes"] = int((cur.fetchone() or {"c": 0})["c"])

        if categoria in ("todos", "proposicoes") and contagens["proposicoes"] > 0:
            cur.execute(
                f"""
                SELECT
                    p.proposicao_id, p.id_origem_nexlegis, p.nome_materia,
                    p.tipo_descricao_origem, p.ementa, p.ano, p.data_publicacao,
                    p.situacao_atual,
                    ts_rank(
                        to_tsvector('portuguese', normalizar_texto_busca(COALESCE(p.nome_materia,'') || ' ' || COALESCE(p.tipo_descricao_origem,'') || ' ' || COALESCE(p.ementa,''))),
                        websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                    )::float AS relevancia
                FROM proposicao p
                {sql_prop_where}
                ORDER BY relevancia DESC, p.data_publicacao DESC NULLS LAST, p.id_origem_nexlegis DESC
                LIMIT 60
                """,
                [termo, *params_prop],
            )
            for r in cur.fetchall():
                itens.append(
                    ItemBuscaOut(
                        tipo="proposicao",
                        id=r["proposicao_id"],
                        titulo=r["nome_materia"],
                        subtitulo=f"{r['tipo_descricao_origem']} · {r['situacao_atual'] or 'Situação não publicada'}",
                        trecho_destaque=_trecho_seguro(r["ementa"]),
                        data_referencia=r["data_publicacao"],
                        ano=r["ano"],
                        url_interna=f"/materias/{r['proposicao_id']}",
                        fonte_url=f"https://inhumas.nexlegis.com.br/materias/{r['id_origem_nexlegis']}",
                        relevancia=round(float(r["relevancia"]) + 0.15, 4),
                    )
                )

        # 2. Legislação Municipal (Normas / Leis)
        sql_norma_where = """
            WHERE n.municipio_id = %s
              AND (
                to_tsvector('portuguese', normalizar_texto_busca(COALESCE(n.numero,'') || ' ' || COALESCE(n.categoria_descricao,'') || ' ' || COALESCE(n.ementa,'') || ' ' || COALESCE(n.texto_extraido,'')))
                @@ websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                OR normalizar_texto_busca(COALESCE(n.numero,'') || ' ' || COALESCE(n.categoria_descricao,'') || ' ' || COALESCE(n.ementa,'')) LIKE normalizar_texto_busca(%s)
              )
        """
        params_norma: list[Any] = [municipio_id, termo, like_pat]
        if ano is not None:
            sql_norma_where += " AND n.ano = %s"
            params_norma.append(ano)

        cur.execute(f"SELECT COUNT(*)::int AS c FROM norma n {sql_norma_where}", params_norma)
        contagens["normas"] = int((cur.fetchone() or {"c": 0})["c"])

        if categoria in ("todos", "normas") and contagens["normas"] > 0:
            cur.execute(
                f"""
                SELECT
                    n.norma_id, n.numero, n.ano, n.categoria_descricao,
                    n.data_publicacao, n.ementa, n.fonte_url,
                    ts_rank(
                        to_tsvector('portuguese', normalizar_texto_busca(COALESCE(n.numero,'') || ' ' || COALESCE(n.categoria_descricao,'') || ' ' || COALESCE(n.ementa,'') || ' ' || COALESCE(n.texto_extraido,''))),
                        websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                    )::float AS relevancia
                FROM norma n
                {sql_norma_where}
                ORDER BY relevancia DESC, n.data_publicacao DESC NULLS LAST, n.id_origem DESC
                LIMIT 60
                """,
                [termo, *params_norma],
            )
            for r in cur.fetchall():
                ano_txt = f"/{r['ano']}" if r["ano"] else ""
                itens.append(
                    ItemBuscaOut(
                        tipo="norma",
                        id=r["norma_id"],
                        titulo=f"{r['categoria_descricao']} nº {r['numero']}{ano_txt}",
                        subtitulo=f"Legislação municipal · {r['categoria_descricao']}",
                        trecho_destaque=_trecho_seguro(r["ementa"]),
                        data_referencia=r["data_publicacao"],
                        ano=r["ano"],
                        url_interna=f"/legislacao/{r['norma_id']}",
                        fonte_url=r["fonte_url"],
                        relevancia=round(float(r["relevancia"]) + 0.18, 4),
                    )
                )

        # 3. Vereadores (independente do filtro de ano)
        sql_ver_where = """
            WHERE v.municipio_id = %s
              AND (
                to_tsvector('portuguese', normalizar_texto_busca(COALESCE(v.nome_exibicao,'') || ' ' || COALESCE(v.nome_civil,'') || ' ' || COALESCE(v.nome_politico,'')))
                @@ websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                OR normalizar_texto_busca(COALESCE(v.nome_exibicao,'') || ' ' || COALESCE(v.nome_civil,'') || ' ' || COALESCE(v.nome_politico,'')) LIKE normalizar_texto_busca(%s)
              )
        """
        params_ver: list[Any] = [municipio_id, termo, like_pat]
        cur.execute(f"SELECT COUNT(*)::int AS c FROM vereador v {sql_ver_where}", params_ver)
        contagens["vereadores"] = int((cur.fetchone() or {"c": 0})["c"])

        if categoria in ("todos", "vereadores") and contagens["vereadores"] > 0:
            cur.execute(
                f"""
                SELECT v.vereador_id, v.slug, v.nome_exibicao, v.nome_civil, v.fonte_url
                FROM vereador v
                {sql_ver_where}
                ORDER BY v.nome_exibicao ASC
                LIMIT 20
                """,
                params_ver,
            )
            for r in cur.fetchall():
                itens.append(
                    ItemBuscaOut(
                        tipo="vereador",
                        id=r["vereador_id"],
                        titulo=r["nome_exibicao"],
                        subtitulo=f"Perfil parlamentar{(' · ' + r['nome_civil']) if r['nome_civil'] else ''}",
                        trecho_destaque="Consulte presenças, proposições, votos nominais e Custo da Estrutura do Mandato.",
                        data_referencia=None,
                        ano=None,
                        url_interna=f"/vereadores/{r['slug']}",
                        fonte_url=r["fonte_url"],
                        relevancia=0.95,
                    )
                )

        # 4. Sessões plenárias
        sql_ses_where = """
            WHERE s.municipio_id = %s AND s.valido_ate IS NULL
              AND (
                to_tsvector('portuguese', normalizar_texto_busca(COALESCE(s.nome_sessao,'') || ' ' || COALESCE(s.tipo_descricao,'')))
                @@ websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                OR normalizar_texto_busca(COALESCE(s.nome_sessao,'') || ' ' || COALESCE(s.tipo_descricao,'')) LIKE normalizar_texto_busca(%s)
              )
        """
        params_ses: list[Any] = [municipio_id, termo, like_pat]
        if ano is not None:
            sql_ses_where += " AND s.ano = %s"
            params_ses.append(ano)

        cur.execute(f"SELECT COUNT(*)::int AS c FROM sessao s {sql_ses_where}", params_ses)
        contagens["sessoes"] = int((cur.fetchone() or {"c": 0})["c"])

        if categoria in ("todos", "sessoes") and contagens["sessoes"] > 0:
            cur.execute(
                f"""
                SELECT s.sessao_id, s.id_origem_nexlegis, s.nome_sessao, s.tipo_descricao, s.ano, s.data_abertura
                FROM sessao s
                {sql_ses_where}
                ORDER BY s.data_abertura DESC
                LIMIT 30
                """,
                params_ses,
            )
            for r in cur.fetchall():
                itens.append(
                    ItemBuscaOut(
                        tipo="sessao",
                        id=r["sessao_id"],
                        titulo=r["nome_sessao"],
                        subtitulo=f"{r['tipo_descricao']} · {r['data_abertura'].strftime('%d/%m/%Y')}",
                        trecho_destaque="Sessão plenária com lista de presença, pauta discutida, resumo automático e votações.",
                        data_referencia=r["data_abertura"],
                        ano=r["ano"],
                        url_interna=f"/sessoes/{r['sessao_id']}",
                        fonte_url=f"https://inhumas.nexlegis.com.br/sessoes/{r['id_origem_nexlegis']}",
                        relevancia=0.6,
                    )
                )

        # 5. Despesas públicas e fornecedores
        sql_desp_where = """
            WHERE d.municipio_id = %s
              AND (
                to_tsvector('portuguese', normalizar_texto_busca(COALESCE(d.numero_empenho,'') || ' ' || COALESCE(d.favorecido_nome,'') || ' ' || COALESCE(d.elemento_despesa,'') || ' ' || COALESCE(d.historico,'')))
                @@ websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                OR normalizar_texto_busca(COALESCE(d.numero_empenho,'') || ' ' || COALESCE(d.favorecido_nome,'') || ' ' || COALESCE(d.elemento_despesa,'') || ' ' || COALESCE(d.historico,'')) LIKE normalizar_texto_busca(%s)
              )
        """
        params_desp: list[Any] = [municipio_id, termo, like_pat]
        if ano is not None:
            sql_desp_where += " AND d.ano = %s"
            params_desp.append(ano)

        cur.execute(f"SELECT COUNT(*)::int AS c FROM despesa_empenho d {sql_desp_where}", params_desp)
        contagens["despesas"] = int((cur.fetchone() or {"c": 0})["c"])

        if categoria in ("todos", "despesas") and contagens["despesas"] > 0:
            cur.execute(
                f"""
                SELECT
                    d.empenho_id, d.numero_empenho, d.ano, d.data_empenho,
                    d.favorecido_nome, d.elemento_despesa, d.valor_pago, d.historico, d.fonte_url,
                    ts_rank(
                        to_tsvector('portuguese', normalizar_texto_busca(COALESCE(d.numero_empenho,'') || ' ' || COALESCE(d.favorecido_nome,'') || ' ' || COALESCE(d.elemento_despesa,'') || ' ' || COALESCE(d.historico,''))),
                        websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                    )::float AS relevancia
                FROM despesa_empenho d
                {sql_desp_where}
                ORDER BY relevancia DESC, d.data_empenho DESC
                LIMIT 40
                """,
                [termo, *params_desp],
            )
            for r in cur.fetchall():
                valor_fmt = f"R$ {Decimal(r['valor_pago']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                itens.append(
                    ItemBuscaOut(
                        tipo="despesa",
                        id=r["empenho_id"],
                        titulo=f"Empenho {r['numero_empenho']}/{r['ano']} — {r['favorecido_nome']}",
                        subtitulo=f"{r['elemento_despesa'] or 'Despesa pública'} · Pago: {valor_fmt}",
                        trecho_destaque=_trecho_seguro(r["historico"]),
                        data_referencia=r["data_empenho"],
                        ano=r["ano"],
                        url_interna=f"/despesas?q={r['numero_empenho']}",
                        fonte_url=r["fonte_url"],
                        relevancia=round(float(r["relevancia"]) + 0.12, 4),
                    )
                )

    itens.sort(
        key=lambda x: (
            -x.relevancia,
            -(x.data_referencia.toordinal() if x.data_referencia else 0),
            x.titulo,
        )
    )
    total_cat = sum(contagens.values()) if categoria == "todos" else contagens[categoria]
    total_exibivel = len(itens)
    total_pages = max(1, math.ceil(total_exibivel / per_page)) if total_exibivel > 0 else 1
    inicio = (page - 1) * per_page
    pagina_itens = itens[inicio : inicio + per_page]

    return BuscaUnificadaOut(
        termo=termo,
        categoria=categoria,
        ano=ano,
        page=page,
        per_page=per_page,
        total=total_cat,
        total_pages=total_pages,
        contagem_por_tipo=contagens,
        items=pagina_itens,
    )


@router.get(
    "/api/v1/bairros",
    response_model=BairrosPainelOut,
    summary="Mapa e painel de indicações e requerimentos por bairro (extração determinística sobre ementas)",
)
def listar_bairros(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    ano: Annotated[int | None, Query(ge=2020, le=2100)] = None,
    tema: Annotated[str | None, Query(max_length=80)] = None,
    vereador_id: Annotated[str | None, Query(max_length=80)] = None,
) -> BairrosPainelOut:
    with conn.cursor() as cur:
        # Total de proposições parlamentares no recorte
        filtros_prop = ["p.municipio_id = %s", "p.eh_proposicao_parlamentar = TRUE"]
        params_prop: list[Any] = [municipio_id]
        if ano is not None:
            filtros_prop.append("p.ano = %s")
            params_prop.append(ano)
        if vereador_id:
            filtros_prop.append(
                "EXISTS (SELECT 1 FROM autoria a WHERE a.proposicao_id = p.proposicao_id AND a.vereador_id = %s)"
            )
            params_prop.append(vereador_id)
        where_prop = " AND ".join(filtros_prop)

        cur.execute(f"SELECT COUNT(*)::int AS total FROM proposicao p WHERE {where_prop}", params_prop)
        total_parlamentares = int((cur.fetchone() or {"total": 0})["total"])

        # Vínculos filtrados
        filtros_v = [where_prop]
        params_v = list(params_prop)
        if tema:
            filtros_v.append("pb.tema_principal = %s")
            params_v.append(tema)
        where_v = " AND ".join(filtros_v)

        cur.execute(
            f"""
            SELECT COUNT(DISTINCT pb.proposicao_id)::int AS com_bairro
            FROM proposicao_bairro pb
            JOIN proposicao p ON p.proposicao_id = pb.proposicao_id
            WHERE {where_v}
            """,
            params_v,
        )
        com_bairro = int((cur.fetchone() or {"com_bairro": 0})["com_bairro"])

        # Distribuição de temas (respeitando ano e vereador, para popular filtros)
        cur.execute(
            f"""
            SELECT pb.tema_principal AS tema, COUNT(*)::int AS quantidade
            FROM proposicao_bairro pb
            JOIN proposicao p ON p.proposicao_id = pb.proposicao_id
            WHERE {where_prop}
            GROUP BY pb.tema_principal
            ORDER BY quantidade DESC, tema ASC
            """,
            params_prop,
        )
        temas_disp = [TemaContagemOut(**r) for r in cur.fetchall()]

        # Contagem por bairro + tema mais frequente
        cur.execute(
            f"""
            WITH filtrado AS (
                SELECT pb.bairro_id, pb.tema_principal, p.data_publicacao
                FROM proposicao_bairro pb
                JOIN proposicao p ON p.proposicao_id = pb.proposicao_id
                WHERE {where_v}
            ),
            tema_top AS (
                SELECT DISTINCT ON (bairro_id)
                    bairro_id, tema_principal
                FROM (
                    SELECT bairro_id, tema_principal, COUNT(*) AS qtd
                    FROM filtrado
                    GROUP BY bairro_id, tema_principal
                ) t
                ORDER BY bairro_id, qtd DESC, tema_principal ASC
            )
            SELECT
                b.bairro_id, b.slug, b.nome_oficial, b.regiao, b.tipo_localidade,
                b.latitude_aprox, b.longitude_aprox,
                COUNT(f.bairro_id)::int AS total_proposicoes,
                tt.tema_principal AS tema_mais_frequente,
                MAX(f.data_publicacao) AS ultimo_registro
            FROM bairro b
            LEFT JOIN filtrado f ON f.bairro_id = b.bairro_id
            LEFT JOIN tema_top tt ON tt.bairro_id = b.bairro_id
            WHERE b.municipio_id = %s
            GROUP BY b.bairro_id, tt.tema_principal
            HAVING COUNT(f.bairro_id) > 0
            ORDER BY total_proposicoes DESC, b.nome_oficial ASC
            """,
            [*params_v, municipio_id],
        )
        bairros = [BairroResumoOut(**r) for r in cur.fetchall()]

    return BairrosPainelOut(
        municipio_id=municipio_id,
        ano_filtro=ano,
        tema_filtro=tema,
        proposicoes_parlamentares_total=total_parlamentares,
        proposicoes_com_bairro=com_bairro,
        proposicoes_sem_bairro=max(0, total_parlamentares - com_bairro),
        nota_metodologica=(
            "O mapeamento identifica exclusivamente menções explícitas a bairros, setores, vilas, "
            "residenciais ou distritos na ementa oficial das proposições parlamentares (excluindo atas "
            "administrativas e bloqueando falsos positivos como equipamentos públicos). Proposições sem "
            "localidade citada na ementa permanecem fora do mapa e são contabilizadas à parte. As posições "
            "no mapa vetorial representam a localização aproximada de cada região de Inhumas."
        ),
        temas_disponiveis=temas_disp,
        bairros=bairros,
    )


@router.get(
    "/api/v1/bairros/{slug}",
    response_model=BairroDetalheOut,
    summary="Detalha todas as proposições vinculadas a um bairro específico",
)
def obter_bairro_detalhe(
    conn: DbConnDep,
    slug: Annotated[str, Path(min_length=2, max_length=96)],
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    ano: Annotated[int | None, Query(ge=2020, le=2100)] = None,
    tema: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> BairroDetalheOut:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT bairro_id, slug, nome_oficial, regiao, tipo_localidade, latitude_aprox, longitude_aprox
            FROM bairro
            WHERE municipio_id = %s AND (slug = %s OR bairro_id = %s)
            LIMIT 1
            """,
            (municipio_id, slug, slug),
        )
        b_row = cur.fetchone()
        if b_row is None:
            raise HTTPException(status_code=404, detail=f"Bairro '{slug}' não encontrado.")

        bid = b_row["bairro_id"]
        filtros = ["pb.municipio_id = %s", "pb.bairro_id = %s"]
        params: list[Any] = [municipio_id, bid]
        if ano is not None:
            filtros.append("p.ano = %s")
            params.append(ano)
        if tema:
            filtros.append("pb.tema_principal = %s")
            params.append(tema)
        where_sql = " AND ".join(filtros)

        cur.execute(
            f"""
            SELECT COUNT(*)::int AS total, MAX(p.data_publicacao) AS ultimo_registro
            FROM proposicao_bairro pb
            JOIN proposicao p ON p.proposicao_id = pb.proposicao_id
            WHERE {where_sql}
            """,
            params,
        )
        agg = cur.fetchone() or {"total": 0, "ultimo_registro": None}
        total = int(agg["total"])
        total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1

        cur.execute(
            f"""
            SELECT pb.tema_principal AS tema, COUNT(*)::int AS quantidade
            FROM proposicao_bairro pb
            JOIN proposicao p ON p.proposicao_id = pb.proposicao_id
            WHERE {where_sql}
            GROUP BY pb.tema_principal
            ORDER BY quantidade DESC, tema ASC
            """,
            params,
        )
        temas = [TemaContagemOut(**r) for r in cur.fetchall()]

        cur.execute(
            f"""
            SELECT v.vereador_id, v.nome_exibicao, v.slug, COUNT(DISTINCT p.proposicao_id)::int AS quantidade_proposicoes
            FROM proposicao_bairro pb
            JOIN proposicao p ON p.proposicao_id = pb.proposicao_id
            JOIN autoria a ON a.proposicao_id = p.proposicao_id
            JOIN vereador v ON v.vereador_id = a.vereador_id
            WHERE {where_sql}
            GROUP BY v.vereador_id, v.nome_exibicao, v.slug
            ORDER BY quantidade_proposicoes DESC, v.nome_exibicao ASC
            """,
            params,
        )
        autores_bairro = [VereadorBairroContagemOut(**r) for r in cur.fetchall()]

        offset = (page - 1) * per_page
        cur.execute(
            f"""
            SELECT
                p.proposicao_id, p.id_origem_nexlegis, p.nome_materia,
                p.tipo_descricao_origem, p.ano, p.data_publicacao,
                p.ementa, p.situacao_atual, pb.tema_principal, pb.trecho_evidencia
            FROM proposicao_bairro pb
            JOIN proposicao p ON p.proposicao_id = pb.proposicao_id
            WHERE {where_sql}
            ORDER BY p.data_publicacao DESC NULLS LAST, p.id_origem_nexlegis DESC
            LIMIT %s OFFSET %s
            """,
            [*params, per_page, offset],
        )
        p_rows = cur.fetchall()
        pids = [r["proposicao_id"] for r in p_rows]
        autores_map: dict[str, list[str]] = {}
        if pids:
            cur.execute(
                """
                SELECT a.proposicao_id, COALESCE(v.nome_exibicao, a.autor_institucional) AS nome
                FROM autoria a
                LEFT JOIN vereador v ON v.vereador_id = a.vereador_id
                WHERE a.municipio_id = %s AND a.proposicao_id = ANY(%s)
                ORDER BY a.autoria_id ASC
                """,
                (municipio_id, pids),
            )
            for ar in cur.fetchall():
                if ar["nome"]:
                    autores_map.setdefault(ar["proposicao_id"], []).append(ar["nome"])

    proposicoes = [
        ProposicaoBairroItemOut(
            proposicao_id=r["proposicao_id"],
            nome_materia=r["nome_materia"],
            tipo_descricao_origem=r["tipo_descricao_origem"],
            ano=r["ano"],
            data_publicacao=r["data_publicacao"],
            ementa=r["ementa"],
            situacao_atual=r["situacao_atual"],
            tema_principal=r["tema_principal"],
            trecho_evidencia=r["trecho_evidencia"],
            autores_nomes=autores_map.get(r["proposicao_id"], []),
            fonte_url=f"https://inhumas.nexlegis.com.br/materias/{r['id_origem_nexlegis']}",
        )
        for r in p_rows
    ]

    resumo_b = BairroResumoOut(
        **b_row,
        total_proposicoes=total,
        tema_mais_frequente=temas[0].tema if temas else None,
        ultimo_registro=agg["ultimo_registro"],
    )
    return BairroDetalheOut(
        bairro=resumo_b,
        temas=temas,
        vereadores_autores=autores_bairro,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        proposicoes=proposicoes,
    )


@router.get(
    "/api/v1/legislacao",
    response_model=NormasListagemOut,
    summary="Catálogo pesquisável de leis e normas municipais coletadas no portal oficial",
)
def listar_legislacao(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    q: Annotated[str | None, Query(max_length=160)] = None,
    ano: Annotated[int | None, Query(ge=1950, le=2100)] = None,
    categoria: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> NormasListagemOut:
    filtros = ["municipio_id = %s"]
    params: list[Any] = [municipio_id]
    if ano is not None:
        filtros.append("ano = %s")
        params.append(ano)
    if categoria:
        filtros.append("categoria_descricao = %s")
        params.append(categoria)
    if q and q.strip():
        termo = " ".join(q.strip().split())
        filtros.append(
            """(
                to_tsvector('portuguese', normalizar_texto_busca(COALESCE(numero,'') || ' ' || COALESCE(categoria_descricao,'') || ' ' || COALESCE(ementa,'') || ' ' || COALESCE(texto_extraido,'')))
                @@ websearch_to_tsquery('portuguese', normalizar_texto_busca(%s))
                OR normalizar_texto_busca(COALESCE(numero,'') || ' ' || COALESCE(ementa,'')) LIKE normalizar_texto_busca(%s)
            )"""
        )
        params.extend([termo, f"%{termo}%"])

    where_sql = " AND ".join(filtros)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT categoria_descricao FROM norma WHERE municipio_id = %s ORDER BY 1",
            (municipio_id,),
        )
        categorias = [r["categoria_descricao"] for r in cur.fetchall()]

        cur.execute(
            "SELECT DISTINCT ano FROM norma WHERE municipio_id = %s AND ano IS NOT NULL ORDER BY ano DESC",
            (municipio_id,),
        )
        anos = [int(r["ano"]) for r in cur.fetchall()]

        cur.execute(f"SELECT COUNT(*)::int AS total FROM norma WHERE {where_sql}", params)
        total = int((cur.fetchone() or {"total": 0})["total"])
        total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1

        offset = (page - 1) * per_page
        cur.execute(
            f"""
            SELECT
                norma_id, tabela_origem, id_origem, numero, ano, tipo_norma,
                categoria_descricao, data_publicacao, ementa, total_anexos,
                status_ocr, extraido_por_ocr, requer_revisao_humana, fonte_url, coletado_em
            FROM norma
            WHERE {where_sql}
            ORDER BY data_publicacao DESC NULLS LAST, id_origem DESC
            LIMIT %s OFFSET %s
            """,
            [*params, per_page, offset],
        )
        items = [NormaResumoOut(**r) for r in cur.fetchall()]

    return NormasListagemOut(
        municipio_id=municipio_id,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        categorias_disponiveis=categorias,
        anos_disponiveis=anos,
        nota_cobertura=(
            "Cobertura correspondente às normas cadastradas no Portal da Transparência/Legislação da Câmara "
            "de Inhumas (desde a Lei Orgânica 001/1990 até as leis de 2026). Leis históricas anteriores não "
            "digitalizadas pelo portal oficial não constam nesta base. Os links direcionam sempre para a "
            "página permanente oficial da lei (nunca para URLs temporárias de download)."
        ),
        items=items,
    )


@router.get(
    "/api/v1/legislacao/{id}",
    response_model=NormaDetalheOut,
    summary="Detalhe de uma lei/norma municipal com resumo automático, status de OCR e proveniência",
)
def obter_norma_detalhe(
    conn: DbConnDep,
    id: Annotated[str, Path(min_length=1, max_length=100)],
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
) -> NormaDetalheOut:
    id_num = int(id) if id.isdigit() else -1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM norma
            WHERE municipio_id = %s
              AND (norma_id = %s OR id_origem = %s OR numero = %s)
            ORDER BY CASE WHEN norma_id = %s THEN 0 WHEN id_origem = %s THEN 1 ELSE 2 END, data_publicacao DESC NULLS LAST
            LIMIT 1
            """,
            (municipio_id, id, id_num, id, id, id_num),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Norma '{id}' não encontrada.")

    ano_txt = f"/{row['ano']}" if row["ano"] else ""
    resumo = gerar_resumo_materia(
        nome_materia=f"{row['categoria_descricao']} nº {row['numero']}{ano_txt}",
        tipo_descricao=row["categoria_descricao"],
        ementa=row["ementa"],
        autores_nomes=[],
        situacao_atual="Norma publicada no portal oficial de legislação municipal",
        data_referencia=row["data_publicacao"],
        placar_resumo=None,
        fonte_url=row["fonte_url"],
        coletado_em=row["coletado_em"],
    )

    return NormaDetalheOut(
        norma_id=row["norma_id"],
        tabela_origem=row["tabela_origem"],
        id_origem=row["id_origem"],
        numero=row["numero"],
        ano=row["ano"],
        tipo_norma=row["tipo_norma"],
        categoria_descricao=row["categoria_descricao"],
        data_publicacao=row["data_publicacao"],
        data_publicacao_portal=row["data_publicacao_portal"],
        ementa=row["ementa"],
        total_anexos=row["total_anexos"],
        texto_extraido=row["texto_extraido"],
        status_ocr=row["status_ocr"],
        extraido_por_ocr=row["extraido_por_ocr"],
        ocr_engine_versao=row["ocr_engine_versao"],
        ocr_confianca_media=row["ocr_confianca_media"],
        requer_revisao_humana=row["requer_revisao_humana"],
        motivo_revisao_humana=row["motivo_revisao_humana"],
        fonte_url=row["fonte_url"],
        coletado_em=row["coletado_em"],
        resumo_cidadao=resumo,
        proveniencia=ProvenienciaOut(
            municipio_id=row["municipio_id"],
            fonte_id=row["fonte_id"],
            fonte_url=row["fonte_url"],
            coletado_em=row["coletado_em"],
            hash_conteudo=row["hash_conteudo"].strip(),
            versao_coletor=row["versao_coletor"],
        ),
    )


@router.get(
    "/api/v1/comparativo",
    response_model=ComparativoSiconfiOut,
    summary="Comparativo oficial SICONFI (Função 01 - Legislativa) entre Inhumas e municípios pares de Goiás",
)
def obter_comparativo_siconfi(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    ano: Annotated[int | None, Query(ge=2020, le=2100)] = None,
) -> ComparativoSiconfiOut:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ano
            FROM comparativo_legislativo_siconfi
            WHERE municipio_id = %s
            ORDER BY ano DESC
            """,
            (municipio_id,),
        )
        anos_disp = [int(r["ano"]) for r in cur.fetchall()]
        if not anos_disp:
            raise HTTPException(
                status_code=404,
                detail="Nenhum dado comparativo SICONFI disponível para este município.",
            )

        ano_sel = ano if ano in anos_disp else anos_disp[0]

        cur.execute(
            """
            SELECT *
            FROM comparativo_legislativo_siconfi
            WHERE municipio_id = %s AND ano = %s
            ORDER BY populacao_siconfi DESC NULLS LAST, ente_nome ASC
            """,
            (municipio_id, ano_sel),
        )
        rows = cur.fetchall()

        cur.execute(
            """
            SELECT codigo_ibge, despesa_paga
            FROM comparativo_legislativo_siconfi
            WHERE municipio_id = %s AND ano = %s
            """,
            (municipio_id, ano_sel - 1),
        )
        prev_map: dict[str, Decimal | None] = {
            r["codigo_ibge"].strip(): r["despesa_paga"] for r in cur.fetchall()
        }

    municipios_out: list[ComparativoMunicipioOut] = []
    per_capitas: list[Decimal] = []
    for r in rows:
        cod = r["codigo_ibge"].strip()
        paga = r["despesa_paga"]
        paga_ant = prev_map.get(cod)
        var_pct: Decimal | None = None
        if paga is not None and paga_ant is not None and paga_ant > 0:
            var_pct = (((paga - paga_ant) / paga_ant) * Decimal(100)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        if r["despesa_paga_per_capita_ano"] is not None:
            per_capitas.append(Decimal(r["despesa_paga_per_capita_ano"]))

        municipios_out.append(
            ComparativoMunicipioOut(
                comparativo_id=r["comparativo_id"],
                codigo_ibge=cod,
                ente_nome=r["ente_nome"],
                uf=r["uf"].strip(),
                eh_municipio_foco=bool(r["eh_municipio_foco"]),
                ano=r["ano"],
                populacao_siconfi=r["populacao_siconfi"],
                despesa_empenhada=r["despesa_empenhada"],
                despesa_liquidada=r["despesa_liquidada"],
                despesa_paga=paga,
                despesa_paga_per_capita_ano=r["despesa_paga_per_capita_ano"],
                despesa_paga_per_capita_mes=r["despesa_paga_per_capita_mes"],
                despesa_paga_ano_anterior=paga_ant,
                variacao_pct_ano_anterior=var_pct,
                fonte_url=r["fonte_url"],
                coletado_em=r["coletado_em"],
            )
        )

    media_pc = (
        (sum(per_capitas) / Decimal(len(per_capitas))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if per_capitas
        else None
    )
    mediana_pc = (
        Decimal(str(median(per_capitas))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if per_capitas
        else None
    )

    return ComparativoSiconfiOut(
        municipio_id=municipio_id,
        ano_selecionado=ano_sel,
        anos_disponiveis=anos_disp,
        fonte_oficial="SICONFI — Secretaria do Tesouro Nacional (Ministério da Fazenda)",
        anexo_siconfi="DCA-Anexo I-E (Despesas Orçamentárias por Função)",
        funcao_descricao="01 - Legislativa",
        nota_metodologica=(
            "Comparativo factual entre municípios goianos de porte populacional semelhante (faixa de 44 mil a "
            "67 mil habitantes), ordenado por população para leitura neutra — sem ranking de juízo de valor. "
            "Os valores representam a despesa paga declarada ao Tesouro Nacional na Função 01 (Legislativa) "
            "da Declaração de Contas Anuais (DCA), dividida pela população informada no próprio SICONFI/IBGE. "
            "Diferenças entre municípios podem decorrer do número de cadeiras na Câmara, estrutura de sede "
            "própria, investimentos pontuais ou regimes previdenciários locais."
        ),
        media_per_capita_ano_grupo=media_pc,
        mediana_per_capita_ano_grupo=mediana_pc,
        municipios=municipios_out,
    )
