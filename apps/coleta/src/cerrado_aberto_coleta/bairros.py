"""Extração determinística de bairros/localidades e temas em proposições (Fase 5).

Regras de transparência e qualidade:
- Catálogo canônico multi-município (`CATALOGO_BAIRROS_POR_MUNICIPIO`) com aliases curados.
- Bloqueio explícito de falsos positivos (ex.: "Parque Infantil", "Centro Municipal de Educação").
- Nunca infere bairro quando a ementa não menciona localidade; registra o trecho exato de evidência.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

VERSAO_EXTRATOR_BAIRROS = "cerrado-aberto-bairros/0.1.0"


@dataclass(frozen=True)
class BairroDefinicao:
    slug: str
    nome_oficial: str
    regiao: str
    tipo_localidade: str  # 'BAIRRO', 'DISTRITO', 'ZONA_RURAL'
    latitude_aprox: Decimal
    longitude_aprox: Decimal
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class VinculoProposicaoBairro:
    municipio_id: str
    proposicao_id: str
    bairro_id: str
    bairro_slug: str
    tema_principal: str
    trecho_evidencia: str


# Coordenadas aproximadas da malha urbana de Inhumas/GO (centro: -16.3578, -49.4961)
# Utilizadas exclusivamente para representação cartográfica relativa por região/setor.
_BAIRROS_INHUMAS_GO: tuple[BairroDefinicao, ...] = (
    BairroDefinicao("centro", "Centro", "Central", "BAIRRO", Decimal("-16.3578"), Decimal("-49.4961"), ("setor central", "regiao central", "bairro centro")),
    BairroDefinicao("parque-sao-jorge", "Parque São Jorge", "Norte", "BAIRRO", Decimal("-16.3420"), Decimal("-49.4920"), ("parque sao jorge", "setor parque sao jorge")),
    BairroDefinicao("setor-vale-das-goiabeiras", "Setor Vale das Goiabeiras", "Oeste", "BAIRRO", Decimal("-16.3550"), Decimal("-49.5140"), ("vale das goiabeiras", "setor vale das goiabeiras", "residencial vale das goiabeiras")),
    BairroDefinicao("vila-america", "Vila América", "Sul", "BAIRRO", Decimal("-16.3690"), Decimal("-49.4980"), ("vila america", "setor vila america")),
    BairroDefinicao("vila-31-de-marco", "Vila 31 de Março", "Leste", "BAIRRO", Decimal("-16.3600"), Decimal("-49.4810"), ("vila 31 de marco", "vila 31", "setor vila 31")),
    BairroDefinicao("setor-teodoro-alves", "Setor Teodoro Alves", "Norte", "BAIRRO", Decimal("-16.3455"), Decimal("-49.5030"), ("setor teodoro alves", "bairro teodoro alves", "teodoro alves")),
    BairroDefinicao("setor-alegrino-lelis", "Setor Alegrino Lélis", "Leste", "BAIRRO", Decimal("-16.3510"), Decimal("-49.4820"), ("setor alegrino lelis", "alegrino lelis")),
    BairroDefinicao("setor-saleiro", "Setor Saleiro", "Oeste", "BAIRRO", Decimal("-16.3620"), Decimal("-49.5090"), ("setor saleiro", "bairro saleiro")),
    BairroDefinicao("residencial-monte-alegre", "Residencial Monte Alegre", "Norte", "BAIRRO", Decimal("-16.3385"), Decimal("-49.5015"), ("residencial monte alegre", "setor monte alegre", "monte alegre")),
    BairroDefinicao("setor-paraiso", "Setor Paraíso", "Sul", "BAIRRO", Decimal("-16.3715"), Decimal("-49.4890"), ("setor paraiso", "jardim paraiso", "bairro paraiso")),
    BairroDefinicao("bairro-anhanguera", "Bairro Anhanguera", "Leste", "BAIRRO", Decimal("-16.3540"), Decimal("-49.4765"), ("bairro anhanguera", "setor anhanguera", "vila anhanguera")),
    BairroDefinicao("setor-amelio-alves", "Setor Amélio Alves", "Norte", "BAIRRO", Decimal("-16.3470"), Decimal("-49.4875"), ("setor amelio alves", "amelio alves")),
    BairroDefinicao("vila-santa-terezinha", "Vila Santa Terezinha", "Central", "BAIRRO", Decimal("-16.3525"), Decimal("-49.4995"), ("vila santa terezinha", "setor santa terezinha", "santa terezinha")),
    BairroDefinicao("jardim-raio-de-sol", "Jardim Raio de Sol", "Sul", "BAIRRO", Decimal("-16.3755"), Decimal("-49.5045"), ("jardim raio de sol", "jardim raio do sol", "setor jardim raio de sol", "setor jardim raio do sol")),
    BairroDefinicao("residencial-santa-barbara", "Residencial Santa Bárbara", "Oeste", "BAIRRO", Decimal("-16.3485"), Decimal("-49.5125"), ("residencial santa barbara", "setor santa barbara", "bairro santa barbara")),
    BairroDefinicao("setor-pedrinhas", "Setor Pedrinhas", "Leste", "BAIRRO", Decimal("-16.3645"), Decimal("-49.4770"), ("setor pedrinhas", "bairro pedrinhas")),
    BairroDefinicao("vila-ana-nery", "Vila Ana Nery", "Central", "BAIRRO", Decimal("-16.3625"), Decimal("-49.4910"), ("vila ana nery", "setor ana nery", "ana nery")),
    BairroDefinicao("vila-lucimar", "Vila Lucimar", "Oeste", "BAIRRO", Decimal("-16.3650"), Decimal("-49.5050"), ("vila lucimar", "setor vila lucimar")),
    BairroDefinicao("setor-nova-morada", "Setor Nova Morada", "Sul", "BAIRRO", Decimal("-16.3730"), Decimal("-49.4945"), ("setor nova morada", "residencial nova morada", "nova morada")),
    BairroDefinicao("parque-santa-rita", "Parque Santa Rita", "Norte", "BAIRRO", Decimal("-16.3410"), Decimal("-49.4850"), ("parque santa rita", "setor santa rita")),
    BairroDefinicao("jardim-suico", "Jardim Suíço", "Leste", "BAIRRO", Decimal("-16.3490"), Decimal("-49.4750"), ("jardim suico", "setor jardim suico")),
    BairroDefinicao("vila-marise", "Vila Marise", "Central", "BAIRRO", Decimal("-16.3565"), Decimal("-49.4895"), ("vila marise", "setor vila marise")),
    BairroDefinicao("vila-mutirao", "Vila Mutirão", "Oeste", "BAIRRO", Decimal("-16.3675"), Decimal("-49.5120"), ("vila mutirao", "setor mutirao")),
    BairroDefinicao("vila-operaria", "Vila Operária", "Central", "BAIRRO", Decimal("-16.3610"), Decimal("-49.5015"), ("vila operaria", "setor vila operaria")),
    BairroDefinicao("residencial-maurivan-pucci", "Residencial Maurivan Pucci", "Norte", "BAIRRO", Decimal("-16.3360"), Decimal("-49.4950"), ("residencial maurivan pucci", "setor maurivan pucci", "maurivan pucci")),
    BairroDefinicao("parque-santa-marta", "Parque Santa Marta", "Sul", "BAIRRO", Decimal("-16.3780"), Decimal("-49.4920"), ("parque santa marta", "setor santa marta")),
    BairroDefinicao("residencial-ana-brandao", "Residencial Ana Brandão", "Oeste", "BAIRRO", Decimal("-16.3515"), Decimal("-49.5175"), ("residencial ana brandao", "setor ana brandao", "ana brandao")),
    BairroDefinicao("vila-santa-maria", "Vila Santa Maria", "Central", "BAIRRO", Decimal("-16.3545"), Decimal("-49.5035"), ("vila santa maria", "setor santa maria")),
    BairroDefinicao("setor-euradark", "Setor Euradark", "Sul", "BAIRRO", Decimal("-16.3700"), Decimal("-49.5085"), ("setor euradark", "euradark")),
    BairroDefinicao("setor-clotildes-essado", "Setor Clotildes Essado", "Norte", "BAIRRO", Decimal("-16.3435"), Decimal("-49.5075"), ("setor clotildes essado", "clotildes essado")),
    BairroDefinicao("setor-panorama-park", "Setor Panorama Park", "Leste", "BAIRRO", Decimal("-16.3460"), Decimal("-49.4730"), ("setor panorama park", "panorama park")),
    BairroDefinicao("vila-sao-jose", "Vila São José", "Central", "BAIRRO", Decimal("-16.3640"), Decimal("-49.4955"), ("vila sao jose", "setor vila sao jose")),
    BairroDefinicao("vila-jandira", "Vila Jandira", "Leste", "BAIRRO", Decimal("-16.3585"), Decimal("-49.4790"), ("vila jandira",)),
    BairroDefinicao("vila-heitor", "Vila Heitor", "Sul", "BAIRRO", Decimal("-16.3670"), Decimal("-49.4925"), ("vila heitor",)),
    BairroDefinicao("vila-verde", "Vila Verde", "Norte", "BAIRRO", Decimal("-16.3400"), Decimal("-49.5060"), ("vila verde",)),
    BairroDefinicao("residencial-atlantico-sul", "Residencial Atlântico Sul", "Sul", "BAIRRO", Decimal("-16.3805"), Decimal("-49.4990"), ("residencial atlantico sul", "setor atlantico sul", "atlantico sul")),
    BairroDefinicao("setor-atlantico-norte", "Setor Atlântico Norte", "Norte", "BAIRRO", Decimal("-16.3340"), Decimal("-49.4995"), ("setor atlantico norte", "residencial atlantico norte", "atlantico norte")),
    BairroDefinicao("jardim-jk", "Jardim JK", "Leste", "BAIRRO", Decimal("-16.3660"), Decimal("-49.4835"), ("jardim jk", "setor jk")),
    BairroDefinicao("setor-sol-nascente", "Setor Sol Nascente", "Leste", "BAIRRO", Decimal("-16.3530"), Decimal("-49.4710"), ("setor sol nascente", "residencial sol nascente")),
    BairroDefinicao("setor-alvorada", "Setor Alvorada", "Oeste", "BAIRRO", Decimal("-16.3595"), Decimal("-49.5150"), ("setor alvorada", "jardim alvorada")),
    BairroDefinicao("residencial-joao-do-couto", "Residencial João do Couto", "Sul", "BAIRRO", Decimal("-16.3770"), Decimal("-49.5095"), ("residencial joao do couto", "setor joao do couto", "joao do couto")),
    BairroDefinicao("residencial-tereza-lima", "Residencial Tereza Lima", "Norte", "BAIRRO", Decimal("-16.3370"), Decimal("-49.4880"), ("residencial tereza lima", "setor tereza lima", "tereza lima")),
    BairroDefinicao("setor-taruma", "Setor Tarumã", "Oeste", "BAIRRO", Decimal("-16.3465"), Decimal("-49.5160"), ("setor taruma", "residencial taruma")),
    BairroDefinicao("residencial-vale-azul", "Residencial Vale Azul", "Sul", "BAIRRO", Decimal("-16.3790"), Decimal("-49.4860"), ("residencial vale azul", "setor vale azul")),
    BairroDefinicao("residencial-watanabe", "Residencial Watanabe", "Leste", "BAIRRO", Decimal("-16.3620"), Decimal("-49.4725"), ("residencial watanabe", "setor watanabe")),
    BairroDefinicao("vila-vida", "Vila Vida", "Central", "BAIRRO", Decimal("-16.3510"), Decimal("-49.4930"), ("vila vida",)),
    BairroDefinicao("residencial-raiza", "Residencial Raíza", "Norte", "BAIRRO", Decimal("-16.3355"), Decimal("-49.5065"), ("residencial raiza", "setor raiza")),
    BairroDefinicao("setor-solar-park", "Setor Solar Park", "Leste", "BAIRRO", Decimal("-16.3440"), Decimal("-49.4790"), ("setor solar park", "solar park")),
    BairroDefinicao("residencial-portal-do-sol", "Residencial Portal do Sol", "Oeste", "BAIRRO", Decimal("-16.3685"), Decimal("-49.5165"), ("residencial portal do sol", "setor portal do sol", "setor residencial portal", "residencial portal")),
    BairroDefinicao("distrito-santa-amalia", "Distrito de Santa Amália (KM 60)", "Distrito / Rural", "DISTRITO", Decimal("-16.2980"), Decimal("-49.5280"), ("santa amalia", "distrito de santa amalia", "povoado santa amalia", "km 60")),
    BairroDefinicao("povoado-quilombo", "Povoado Quilombo", "Distrito / Rural", "DISTRITO", Decimal("-16.3180"), Decimal("-49.4550"), ("povoado quilombo", "distrito de quilombo", "comunidade quilombo", "quilombo")),
    BairroDefinicao("zona-rural", "Zona Rural e Estradas Vicinais", "Distrito / Rural", "ZONA_RURAL", Decimal("-16.3950"), Decimal("-49.5250"), ("zona rural", "estradas rurais", "estradas vicinais", "regiao rural")),
)

CATALOGO_BAIRROS_POR_MUNICIPIO: dict[str, tuple[BairroDefinicao, ...]] = {
    "inhumas-go": _BAIRROS_INHUMAS_GO,
}

_RE_CENTRO_CONTEXTO = re.compile(
    r"\b(?:no|do|ao|pelo|para o|em torno do|regiao do|bairro)\s+centro\b(?!\s+(?:municipal|de|da|do|cultural|esportivo|comunitario|cirurgico|medico|olimpico|educacional|integrado|comercial|administrativo|especializado|referencia))",
    re.IGNORECASE,
)

_REGRAS_TEMA: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Infraestrutura e Asfalto",
        ("asfalto", "asfaltica", "pavimentacao", "recapeamento", "tapa-buraco", "tapa buraco", "calcada", "ponte", "estrada", "drenagem", "galeria", "bueiro", "meio-fio", "mata-burro", "patrolamento", "cascalhamento", "reforma"),
    ),
    (
        "Trânsito e Sinalização",
        ("transito", "dmt", "semaforo", "faixa de pedestre", "faixa elevada", "redutor de velocidade", "quebra-mola", "quebra molas", "lombada", "sinalizacao", "estacionamento", "rotatoria", "mao unica", "placa de"),
    ),
    (
        "Saúde",
        ("saude", "ubs", "ubsf", "upa", "caps", "hospital", "posto de saude", "samu", "medico", "enfermeir", "vacina", "medicamento", "ambulancia", "dengue", "autista", "tea", "fisioterapia", "odontolog"),
    ),
    (
        "Educação",
        ("educacao", "escola", "cmei", "creche", "aluno", "professor", "transporte escolar", "fundeb", "merenda", "biblioteca", "ensino", "estudante"),
    ),
    (
        "Iluminação e Energia",
        ("iluminacao", "poste", "lampada", "luminaria", "led", "energia eletrica", "equatorial", "braco de luz"),
    ),
    (
        "Água e Saneamento",
        ("saneago", "esgoto", "abastecimento de agua", "coleta de lixo", "limpeza urbana", "rocagem", "entulho", "lote vago", "lotes vagos", "lago", "corrego", "meio ambiente", "arborizacao"),
    ),
    (
        "Esporte, Cultura e Lazer",
        ("esporte", "futebol", "quadra", "praca", "academia ao ar livre", "ciclistico", "cultura", "lazer", "parque infantil", "escolinha", "evento", "festividade"),
    ),
    (
        "Segurança e Ordem Pública",
        ("seguranca", "policia", "guarda", "videomonitoramento", "camera", "assedio", "violencia", "patrulhamento"),
    ),
)


def normalizar_sem_acentos(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto or "")
    sem_marcas = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem_marcas).strip().lower()


def classificar_tema_proposicao(ementa: str | None) -> str:
    norm = normalizar_sem_acentos(ementa or "")
    if not norm:
        return "Outros Temas"
    for tema, palavras in _REGRAS_TEMA:
        for kw in palavras:
            if kw in norm:
                return tema
    return "Outros Temas"


def extrair_bairros_da_ementa(
    *,
    municipio_id: str,
    proposicao_id: str,
    ementa: str | None,
) -> list[VinculoProposicaoBairro]:
    """Identifica menções verificáveis a bairros do município na ementa oficial."""
    if not ementa or len(ementa.strip()) < 8:
        return []

    catalogo = CATALOGO_BAIRROS_POR_MUNICIPIO.get(municipio_id, ())
    if not catalogo:
        return []

    norm = normalizar_sem_acentos(ementa)
    tema = classificar_tema_proposicao(ementa)
    encontrados: list[VinculoProposicaoBairro] = []
    vistos: set[str] = set()

    for bairro in catalogo:
        trecho: str | None = None
        for alias in bairro.aliases:
            padrao = re.compile(rf"\b{re.escape(alias)}\b")
            m = padrao.search(norm)
            if m:
                inicio = max(0, m.start() - 35)
                fim = min(len(norm), m.end() + 45)
                trecho = norm[inicio:fim].strip()
                break

        # Caso especial para "Centro": só aceita em contexto geográfico e fora de nomes de órgãos/equipamentos
        if trecho is None and bairro.slug == "centro":
            mc = _RE_CENTRO_CONTEXTO.search(norm)
            if mc:
                inicio = max(0, mc.start() - 30)
                fim = min(len(norm), mc.end() + 45)
                trecho = norm[inicio:fim].strip()

        if trecho is not None and bairro.slug not in vistos:
            vistos.add(bairro.slug)
            encontrados.append(
                VinculoProposicaoBairro(
                    municipio_id=municipio_id,
                    proposicao_id=proposicao_id,
                    bairro_id=f"{municipio_id}-bairro-{bairro.slug}",
                    bairro_slug=bairro.slug,
                    tema_principal=tema,
                    trecho_evidencia=trecho[:235],
                )
            )

    return encontrados


def popular_bairros_e_vinculos_postgres(
    conn: psycopg.Connection[Any],
    *,
    municipio_id: str = "inhumas-go",
) -> dict[str, Any]:
    """Carrega o catálogo de bairros e vincula proposições parlamentares de forma 100% idempotente."""
    catalogo = CATALOGO_BAIRROS_POR_MUNICIPIO.get(municipio_id, ())
    agora = datetime.now(UTC)

    with conn.cursor(row_factory=dict_row) as cur:
        for b in catalogo:
            bairro_id = f"{municipio_id}-bairro-{b.slug}"
            cur.execute(
                """
                INSERT INTO bairro (
                    bairro_id, municipio_id, slug, nome_oficial, regiao,
                    tipo_localidade, latitude_aprox, longitude_aprox, aliases_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (municipio_id, slug) DO UPDATE SET
                    nome_oficial = EXCLUDED.nome_oficial,
                    regiao = EXCLUDED.regiao,
                    tipo_localidade = EXCLUDED.tipo_localidade,
                    latitude_aprox = EXCLUDED.latitude_aprox,
                    longitude_aprox = EXCLUDED.longitude_aprox,
                    aliases_json = EXCLUDED.aliases_json
                """,
                (
                    bairro_id,
                    municipio_id,
                    b.slug,
                    b.nome_oficial,
                    b.regiao,
                    b.tipo_localidade,
                    b.latitude_aprox,
                    b.longitude_aprox,
                    json.dumps(list(b.aliases), ensure_ascii=False),
                ),
            )

        cur.execute(
            """
            SELECT proposicao_id, ementa
            FROM proposicao
            WHERE municipio_id = %s AND eh_proposicao_parlamentar = TRUE
            ORDER BY proposicao_id
            """,
            (municipio_id,),
        )
        proposicoes = cur.fetchall()

        # Recalcula vínculos determinísticos de forma limpa e atômica na transação
        cur.execute("DELETE FROM proposicao_bairro WHERE municipio_id = %s", (municipio_id,))

        total_com_bairro = 0
        total_vinculos = 0
        por_tema: Counter[str] = Counter()
        por_bairro: Counter[str] = Counter()

        for row in proposicoes:
            vinculos = extrair_bairros_da_ementa(
                municipio_id=municipio_id,
                proposicao_id=row["proposicao_id"],
                ementa=row["ementa"],
            )
            if vinculos:
                total_com_bairro += 1
            for v in vinculos:
                cur.execute(
                    """
                    INSERT INTO proposicao_bairro (
                        municipio_id, proposicao_id, bairro_id, tema_principal,
                        trecho_evidencia, metodo_extracao, versao_extrator, extraido_em
                    )
                    VALUES (%s, %s, %s, %s, %s, 'REGEX_DICIONARIO_CURADO', %s, %s)
                    ON CONFLICT (proposicao_id, bairro_id) DO UPDATE SET
                        tema_principal = EXCLUDED.tema_principal,
                        trecho_evidencia = EXCLUDED.trecho_evidencia,
                        versao_extrator = EXCLUDED.versao_extrator,
                        extraido_em = EXCLUDED.extraido_em
                    """,
                    (
                        v.municipio_id,
                        v.proposicao_id,
                        v.bairro_id,
                        v.tema_principal,
                        v.trecho_evidencia,
                        VERSAO_EXTRATOR_BAIRROS,
                        agora,
                    ),
                )
                total_vinculos += 1
                por_tema[v.tema_principal] += 1
                por_bairro[v.bairro_slug] += 1

        conn.commit()

    return {
        "municipio_id": municipio_id,
        "versao_extrator": VERSAO_EXTRATOR_BAIRROS,
        "bairros_cadastrados": len(catalogo),
        "bairros_com_proposicoes": len(por_bairro),
        "proposicoes_parlamentares_analisadas": len(proposicoes),
        "proposicoes_com_bairro_identificado": total_com_bairro,
        "proposicoes_sem_bairro_na_ementa": len(proposicoes) - total_com_bairro,
        "total_vinculos_proposicao_bairro": total_vinculos,
        "distribuicao_temas": dict(por_tema.most_common()),
        "top_10_bairros": por_bairro.most_common(10),
    }
