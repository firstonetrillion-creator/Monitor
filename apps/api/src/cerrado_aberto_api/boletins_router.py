"""Endpoints somente leitura de boletins semanais e distribuição cidadã (Fase 4)."""

from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from cerrado_aberto_api.db import obter_conexao_db
from cerrado_aberto_api.resumos import (
    gerar_alerta_whatsapp,
    gerar_legenda_instagram,
    gerar_resumo_materia,
    gerar_resumo_sessao,
    gerar_slides_instagram,
)
from cerrado_aberto_api.schemas import (
    BoletimSemanalOut,
    ContagemTipoBoletimOut,
    DestaquePautaBoletimOut,
    PanoramaFinanceiroBoletimOut,
    ProvenienciaOut,
    SessaoOpcaoBoletimOut,
)

router = APIRouter(tags=["Boletins e Distribuição (Fase 4)"])
DbConnDep = Annotated[psycopg.Connection[dict[str, Any]], Depends(obter_conexao_db)]

_CONFIG_DISTRIBUICAO_MUNICIPIO: dict[str, dict[str, Any]] = {
    "inhumas-go": {
        "populacao_ibge_2026": 54133,
        "handle_instagram_oficial": "@cerradoaberto",
        "dominio_oficial": "cerradoaberto.org.br",
    }
}


def _obter_config_municipio(municipio_id: str) -> dict[str, Any]:
    return _CONFIG_DISTRIBUICAO_MUNICIPIO.get(
        municipio_id,
        {
            "populacao_ibge_2026": 54133,
            "handle_instagram_oficial": "@cerradoaberto",
            "dominio_oficial": "cerradoaberto.org.br",
        },
    )


def _formatar_placar_item(
    *,
    unanime_flag: bool,
    has_votos: bool,
    favoraveis: int,
    contrarios: int,
    abstencoes: int,
    situacao_atual: str | None,
) -> str:
    if favoraveis > 0 or contrarios > 0 or abstencoes > 0:
        return (
            f"{favoraveis} favorável(is), {contrarios} contrário(s), "
            f"{abstencoes} abstenção(ões)"
        )
    if unanime_flag and has_votos:
        return "Registrada na fonte como aprovada por unanimidade"
    if situacao_atual:
        return situacao_atual
    return "Em pauta / sem placar nominal publicado"


@router.get(
    "/api/v1/boletins/resumo-semanal",
    response_model=BoletimSemanalOut,
    summary="Retorna o boletim em linguagem simples da sessão mais recente (ou de uma sessão específica), com alerta WhatsApp e slides para o Instagram Oficial",
)
def obter_boletim_semanal(
    conn: DbConnDep,
    municipio_id: Annotated[str, Query(min_length=2, max_length=64)] = "inhumas-go",
    sessao_id: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
            description="Opcional: sessao_id, slug ou id_origem_nexlegis. Se omitido, retorna a sessão mais recente.",
        ),
    ] = None,
) -> BoletimSemanalOut:
    cfg = _obter_config_municipio(municipio_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sessao_id, nome_sessao, data_abertura, tipo_descricao
            FROM sessao
            WHERE municipio_id = %s AND valido_ate IS NULL
            ORDER BY data_abertura DESC, id_origem_nexlegis DESC
            LIMIT 12
            """,
            (municipio_id,),
        )
        sessoes_disponiveis = [SessaoOpcaoBoletimOut(**r) for r in cur.fetchall()]
        if not sessoes_disponiveis:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma sessão plenária disponível para geração de boletim.",
            )

        if sessao_id:
            id_num = int(sessao_id) if sessao_id.isdigit() else -1
            cur.execute(
                """
                SELECT s.*, s.horario_abertura::text AS horario_abertura_txt
                FROM sessao s
                WHERE s.municipio_id = %s
                  AND (s.sessao_id = %s OR s.slug = %s OR s.id_origem_nexlegis = %s)
                LIMIT 1
                """,
                (municipio_id, sessao_id, sessao_id, id_num),
            )
        else:
            cur.execute(
                """
                SELECT s.*, s.horario_abertura::text AS horario_abertura_txt
                FROM sessao s
                WHERE s.municipio_id = %s AND s.valido_ate IS NULL
                ORDER BY s.data_abertura DESC, s.id_origem_nexlegis DESC
                LIMIT 1
                """,
                (municipio_id,),
            )
        ses = cur.fetchone()
        if ses is None:
            raise HTTPException(status_code=404, detail=f"Sessão '{sessao_id}' não encontrada.")

        sid = ses["sessao_id"]

        # Presenças separando justificadas e licenças de ausências
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status_normalizado = 'PRESENTE')::int AS presentes,
                COUNT(*) FILTER (WHERE status_normalizado = 'FALTA_JUSTIFICADA')::int AS justificadas,
                COUNT(*) FILTER (WHERE status_normalizado = 'AUSENTE')::int AS ausentes,
                COUNT(*) FILTER (WHERE status_normalizado = 'LICENCA')::int AS licencas
            FROM presenca
            WHERE municipio_id = %s AND sessao_id = %s
            """,
            (municipio_id, sid),
        )
        pres = cur.fetchone() or {
            "presentes": 0,
            "justificadas": 0,
            "ausentes": 0,
            "licencas": 0,
        }

        # Pauta e proposições
        cur.execute(
            """
            SELECT
                pi.pauta_item_id, pi.ordem, pi.unanime AS unanime_flag, pi.has_votos,
                p.proposicao_id, p.id_origem_nexlegis, p.nome_materia, p.tipo_descricao_origem,
                p.ementa, p.situacao_atual, p.data_publicacao, p.ultima_movimentacao,
                p.eh_proposicao_parlamentar, p.fonte_url, p.coletado_em,
                vo.votacao_id
            FROM pauta_item pi
            JOIN proposicao p ON p.proposicao_id = pi.proposicao_id
            LEFT JOIN votacao vo
                ON vo.sessao_id = pi.sessao_id AND vo.proposicao_id = pi.proposicao_id
            WHERE pi.municipio_id = %s AND pi.sessao_id = %s
            ORDER BY pi.ordem ASC, pi.pauta_item_id ASC
            """,
            (municipio_id, sid),
        )
        pauta_rows = cur.fetchall()

        cur.execute(
            "SELECT COUNT(*)::int AS total FROM votacao WHERE municipio_id = %s AND sessao_id = %s",
            (municipio_id, sid),
        )
        total_votacoes = int((cur.fetchone() or {"total": 0})["total"])

        prop_ids = list({r["proposicao_id"] for r in pauta_rows})
        autores_por_prop: dict[str, list[str]] = {}
        if prop_ids:
            cur.execute(
                """
                SELECT a.proposicao_id, COALESCE(v.nome_exibicao, a.autor_institucional) AS nome_autor
                FROM autoria a
                LEFT JOIN vereador v ON v.vereador_id = a.vereador_id
                WHERE a.municipio_id = %s AND a.proposicao_id = ANY(%s)
                ORDER BY a.autoria_id ASC
                """,
                (municipio_id, prop_ids),
            )
            for ar in cur.fetchall():
                if ar["nome_autor"]:
                    autores_por_prop.setdefault(ar["proposicao_id"], []).append(ar["nome_autor"])

        vot_ids = [r["votacao_id"] for r in pauta_rows if r["votacao_id"]]
        placares_por_vot: dict[str, tuple[int, int, int]] = {}
        if vot_ids:
            cur.execute(
                """
                SELECT
                    votacao_id,
                    COUNT(*) FILTER (WHERE voto_normalizado = 'FAVORAVEL')::int AS fav,
                    COUNT(*) FILTER (WHERE voto_normalizado = 'CONTRARIO')::int AS con,
                    COUNT(*) FILTER (WHERE voto_normalizado = 'ABSTENCAO')::int AS abst
                FROM voto
                WHERE municipio_id = %s AND votacao_id = ANY(%s)
                GROUP BY votacao_id
                """,
                (municipio_id, vot_ids),
            )
            for vr in cur.fetchall():
                placares_por_vot[vr["votacao_id"]] = (vr["fav"], vr["con"], vr["abst"])

        # Panorama financeiro 2026
        cur.execute(
            """
            SELECT
                COALESCE(SUM(valor_pago), 0) AS pago,
                COALESCE(SUM(valor_empenhado_liquido), 0) AS empenhado_liquido,
                MAX(coletado_em) AS ultima_coleta
            FROM despesa_empenho
            WHERE municipio_id = %s AND ano = 2026
            """,
            (municipio_id,),
        )
        desp_row = cur.fetchone() or {}

        cur.execute(
            """
            SELECT
                COALESCE(SUM(valor) FILTER (WHERE tipo_natureza = 'RECEITA_REPASSE'), 0) AS repasses,
                COALESCE(SUM(valor) FILTER (WHERE tipo_natureza = 'DEVOLUCAO_DUODECIMO'), 0) AS devolucoes,
                COUNT(DISTINCT mes) FILTER (WHERE tipo_natureza = 'RECEITA_REPASSE')::int AS meses
            FROM receita_duodecimo
            WHERE municipio_id = %s AND ano = 2026
            """,
            (municipio_id,),
        )
        duo_row = cur.fetchone() or {}

    contagem_tipos: Counter[str] = Counter()
    destaques: list[DestaquePautaBoletimOut] = []
    vistas_prop: set[str] = set()

    for r in pauta_rows:
        if not r["eh_proposicao_parlamentar"]:
            continue
        pid = r["proposicao_id"]
        if pid in vistas_prop:
            continue
        vistas_prop.add(pid)
        tipo_desc = r["tipo_descricao_origem"]
        contagem_tipos[tipo_desc] += 1

        fav, con, abst = placares_por_vot.get(r["votacao_id"], (0, 0, 0))
        placar_txt = _formatar_placar_item(
            unanime_flag=bool(r["unanime_flag"]),
            has_votos=bool(r["has_votos"]),
            favoraveis=fav,
            contrarios=con,
            abstencoes=abst,
            situacao_atual=r["situacao_atual"],
        )
        autores_nomes = autores_por_prop.get(pid, [])
        url_mat_oficial = f"https://inhumas.nexlegis.com.br/materias/{r['id_origem_nexlegis']}"
        resumo_mat = gerar_resumo_materia(
            nome_materia=r["nome_materia"],
            tipo_descricao=tipo_desc,
            ementa=r["ementa"],
            autores_nomes=autores_nomes,
            situacao_atual=r["situacao_atual"],
            data_referencia=r["ultima_movimentacao"] or r["data_publicacao"] or ses["data_abertura"],
            placar_resumo=placar_txt,
            fonte_url=url_mat_oficial,
            coletado_em=r["coletado_em"],
        )
        destaques.append(
            DestaquePautaBoletimOut(
                proposicao_id=pid,
                nome_materia=r["nome_materia"],
                tipo_descricao_origem=tipo_desc,
                ementa_original=r["ementa"],
                autores_nomes=autores_nomes,
                placar_resumo=placar_txt,
                resumo_cidadao=resumo_mat,
            )
        )

    # Prioriza Projetos de Lei antes de Requerimentos nos destaques dos cards
    destaques.sort(
        key=lambda d: (
            0 if "projeto de lei" in d.tipo_descricao_origem.lower() else 1,
            d.nome_materia,
        )
    )

    meses_apurados = int(duo_row.get("meses") or 10)
    despesa_paga = Decimal(desp_row["pago"]) if desp_row.get("pago") is not None else None
    populacao = int(cfg["populacao_ibge_2026"])
    per_capita_mes = (
        (despesa_paga / Decimal(populacao) / Decimal(meses_apurados)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if despesa_paga is not None and populacao > 0 and meses_apurados > 0
        else None
    )

    panorama = PanoramaFinanceiroBoletimOut(
        ano=2026,
        despesa_paga_acumulada=despesa_paga,
        despesa_empenhada_liquida=(
            Decimal(desp_row["empenhado_liquido"])
            if desp_row.get("empenhado_liquido") is not None
            else None
        ),
        duodecimo_recebido_acumulado=(
            Decimal(duo_row["repasses"]) if duo_row.get("repasses") is not None else None
        ),
        duodecimo_devolvido_acumulado=(
            Decimal(duo_row["devolucoes"]) if duo_row.get("devolucoes") is not None else None
        ),
        populacao_ibge_2026=populacao,
        meses_apurados=meses_apurados,
        valor_por_habitante_mes=per_capita_mes,
        ultima_coleta_transparencia=desp_row.get("ultima_coleta"),
    )

    url_sessao_oficial = f"https://inhumas.nexlegis.com.br/sessoes/{ses['id_origem_nexlegis']}"
    url_sessao_portal = f"https://{cfg['dominio_oficial']}/sessoes/{sid}"
    contagem_dict = dict(contagem_tipos)

    resumo_sessao = gerar_resumo_sessao(
        nome_sessao=ses["nome_sessao"],
        data_abertura=ses["data_abertura"],
        total_presentes=pres["presentes"],
        total_faltas_justificadas=pres["justificadas"],
        total_ausentes=pres["ausentes"],
        total_licencas=pres["licencas"],
        total_proposicoes_parlamentares=len(destaques),
        total_votacoes=total_votacoes,
        contagem_por_tipo=contagem_dict,
        fonte_url=url_sessao_oficial,
        coletado_em=ses["coletado_em"],
    )

    alerta_whatsapp = gerar_alerta_whatsapp(
        nome_sessao=ses["nome_sessao"],
        data_abertura=ses["data_abertura"],
        total_presentes=pres["presentes"],
        total_proposicoes_parlamentares=len(destaques),
        contagem_por_tipo=contagem_dict,
        url_sessao=url_sessao_portal,
        coletado_em=ses["coletado_em"],
    )

    legenda_instagram = gerar_legenda_instagram(
        nome_sessao=ses["nome_sessao"],
        data_abertura=ses["data_abertura"],
        total_presentes=pres["presentes"],
        total_proposicoes_parlamentares=len(destaques),
        destaques=destaques,
        panorama=panorama,
        coletado_em=ses["coletado_em"],
        handle_instagram=cfg["handle_instagram_oficial"],
        dominio_oficial=cfg["dominio_oficial"],
    )

    slides_instagram = gerar_slides_instagram(
        nome_sessao=ses["nome_sessao"],
        data_abertura=ses["data_abertura"],
        total_presentes=pres["presentes"],
        total_proposicoes_parlamentares=len(destaques),
        total_votacoes=total_votacoes,
        destaques=destaques,
        panorama=panorama,
        coletado_em=ses["coletado_em"],
        handle_instagram=cfg["handle_instagram_oficial"],
        dominio_oficial=cfg["dominio_oficial"],
    )

    return BoletimSemanalOut(
        municipio_id=municipio_id,
        handle_instagram_oficial=cfg["handle_instagram_oficial"],
        dominio_oficial=cfg["dominio_oficial"],
        sessao_id=sid,
        nome_sessao=ses["nome_sessao"],
        tipo_descricao=ses["tipo_descricao"],
        data_abertura=ses["data_abertura"],
        horario_abertura=ses["horario_abertura_txt"],
        ata_pdf_url=ses["ata_pdf_url"],
        total_presentes=pres["presentes"],
        total_faltas_justificadas=pres["justificadas"],
        total_ausentes=pres["ausentes"],
        total_licencas=pres["licencas"],
        total_itens_pauta=len(pauta_rows),
        total_proposicoes_parlamentares=len(destaques),
        total_votacoes=total_votacoes,
        contagem_por_tipo=[
            ContagemTipoBoletimOut(tipo_descricao=k, quantidade=v)
            for k, v in sorted(contagem_dict.items(), key=lambda x: (-x[1], x[0]))
        ],
        destaques_pauta=destaques,
        resumo_sessao=resumo_sessao,
        panorama_financeiro_2026=panorama,
        alerta_whatsapp=alerta_whatsapp,
        legenda_instagram=legenda_instagram,
        slides_instagram=slides_instagram,
        sessoes_disponiveis=sessoes_disponiveis,
        proveniencia=ProvenienciaOut(
            municipio_id=ses["municipio_id"],
            fonte_id=ses["fonte_id"],
            fonte_url=ses["fonte_url"],
            coletado_em=ses["coletado_em"],
            hash_conteudo=ses["hash_conteudo"].strip(),
            versao_coletor=ses["versao_coletor"],
        ),
    )
