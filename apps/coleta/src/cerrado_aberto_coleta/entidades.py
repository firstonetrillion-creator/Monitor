"""Resolução curada de entidades (vereadores e aliases) e classificação de proposições (ADR-005)."""

from __future__ import annotations

from dataclasses import dataclass

from cerrado_aberto_coleta.normalizacao import gerar_chave_busca, normalizar_texto


@dataclass(frozen=True)
class RegraTipoProposicao:
    tipo_id_origem: int
    descricao_origem: str
    codigo_normalizado: str
    nome_exibicao: str
    categoria: str
    eh_proposicao_parlamentar: bool
    contabilizar_producao_vereador: bool
    justificativa: str


# Tabela de classificação documentada (ADR-005, Decisão 4) — atualizada com os tipo_id reais do Lote 1
MAPA_TIPOS_PROPOSICAO_PADRAO: dict[int, RegraTipoProposicao] = {
    1: RegraTipoProposicao(
        tipo_id_origem=1,
        descricao_origem="Moção de Aplausos",
        codigo_normalizado="MOCAO_DE_APLAUSOS",
        nome_exibicao="Moção de Aplausos",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Manifestação formal de aplauso ou reconhecimento de autoria parlamentar.",
    ),
    2: RegraTipoProposicao(
        tipo_id_origem=2,
        descricao_origem="PROJETO DE LEI DO LEGISLATIVO",
        codigo_normalizado="PROJETO_LEI_LEGISLATIVO",
        nome_exibicao="Projeto de Lei do Legislativo",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Projeto de lei de iniciativa parlamentar.",
    ),
    3: RegraTipoProposicao(
        tipo_id_origem=3,
        descricao_origem="Projeto de Decreto Legislativo",
        codigo_normalizado="PROJETO_DECRETO_LEGISLATIVO",
        nome_exibicao="Projeto de Decreto Legislativo",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Matéria de competência exclusiva do Legislativo.",
    ),
    4: RegraTipoProposicao(
        tipo_id_origem=4,
        descricao_origem="Projeto de Lei",
        codigo_normalizado="PROJETO_DE_LEI",
        nome_exibicao="Projeto de Lei",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Proposição legislativa substantiva submetida ao Plenário (Executivo ou Legislativo).",
    ),
    5: RegraTipoProposicao(
        tipo_id_origem=5,
        descricao_origem="Requerimento",
        codigo_normalizado="REQUERIMENTO",
        nome_exibicao="Requerimento",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Pedido formal de providências ou informações feito por vereador.",
    ),
    6: RegraTipoProposicao(
        tipo_id_origem=6,
        descricao_origem="Indicação",
        codigo_normalizado="INDICACAO",
        nome_exibicao="Indicação",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Sugestão de obra ou serviço encaminhada ao Executivo por vereador.",
    ),
    7: RegraTipoProposicao(
        tipo_id_origem=7,
        descricao_origem="Moção",
        codigo_normalizado="MOCAO",
        nome_exibicao="Moção",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Manifestação formal de aplauso, pesar, apoio ou apelo.",
    ),
    8: RegraTipoProposicao(
        tipo_id_origem=8,
        descricao_origem="Projeto de Decreto Legislativo",
        codigo_normalizado="PROJETO_DECRETO_LEGISLATIVO",
        nome_exibicao="Projeto de Decreto Legislativo",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Matéria de competência exclusiva do Legislativo (tipo_id 8 no Nexlegis).",
    ),
    10: RegraTipoProposicao(
        tipo_id_origem=10,
        descricao_origem="Projeto de Lei Complementar",
        codigo_normalizado="PROJETO_LEI_COMPLEMENTAR",
        nome_exibicao="Projeto de Lei Complementar",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Proposição legislativa de lei complementar submetida ao Plenário (tipo_id 10).",
    ),
    12: RegraTipoProposicao(
        tipo_id_origem=12,
        descricao_origem="Projeto de Resolução",
        codigo_normalizado="PROJETO_RESOLUCAO",
        nome_exibicao="Projeto de Resolução",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Matéria destinada a regular matéria político-administrativa da Câmara (tipo_id 12).",
    ),
    14: RegraTipoProposicao(
        tipo_id_origem=14,
        descricao_origem="Veto",
        codigo_normalizado="VETO",
        nome_exibicao="Veto",
        categoria="ATO_EXECUTIVO_SUBMETIDO",
        eh_proposicao_parlamentar=False,
        contabilizar_producao_vereador=False,
        justificativa="Excluído da produção parlamentar (ADR-005, Decisão 4): ato do Executivo submetido à deliberação (tipo_id 14).",
    ),
    112: RegraTipoProposicao(
        tipo_id_origem=112,
        descricao_origem="Emenda",
        codigo_normalizado="EMENDA",
        nome_exibicao="Emenda",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Proposta acessória parlamentar para alterar texto de proposição (tipo_id 112).",
    ),
    113: RegraTipoProposicao(
        tipo_id_origem=113,
        descricao_origem="PROJETO DE LEI DO LEGISLATIVO",
        codigo_normalizado="PROJETO_LEI_LEGISLATIVO",
        nome_exibicao="Projeto de Lei do Legislativo",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Projeto de lei de autoria parlamentar (tipo_id 113 no Nexlegis).",
    ),
    144: RegraTipoProposicao(
        tipo_id_origem=144,
        descricao_origem="ATA DA SESSÃO",
        codigo_normalizado="ATA_DA_SESSAO",
        nome_exibicao="Ata da Sessão",
        categoria="ATO_ADMINISTRATIVO_SESSAO",
        eh_proposicao_parlamentar=False,
        contabilizar_producao_vereador=False,
        justificativa=(
            "Excluída da contagem de produção legislativa (ADR-005, Decisão 4): "
            "registro administrativo oficial da sessão plenária ordinária."
        ),
    ),
    145: RegraTipoProposicao(
        tipo_id_origem=145,
        descricao_origem="ATA DA SESSAO EXTRAORDINARIA",
        codigo_normalizado="ATA_DA_SESSAO_EXTRAORDINARIA",
        nome_exibicao="Ata da Sessão Extraordinária",
        categoria="ATO_ADMINISTRATIVO_SESSAO",
        eh_proposicao_parlamentar=False,
        contabilizar_producao_vereador=False,
        justificativa=(
            "Excluída da contagem de produção legislativa (ADR-005, Decisão 4): "
            "registro administrativo oficial de sessão extraordinária."
        ),
    ),
    210: RegraTipoProposicao(
        tipo_id_origem=210,
        descricao_origem="Veto ao Autógrafo de Lei",
        codigo_normalizado="VETO_AO_AUTOGRAFO_DE_LEI",
        nome_exibicao="Veto ao Autógrafo de Lei",
        categoria="ATO_EXECUTIVO_SUBMETIDO",
        eh_proposicao_parlamentar=False,
        contabilizar_producao_vereador=False,
        justificativa=(
            "Excluído da contagem de produção parlamentar (ADR-005, Decisão 4): "
            "ato do Poder Executivo submetido à apreciação do Plenário."
        ),
    ),
    211: RegraTipoProposicao(
        tipo_id_origem=211,
        descricao_origem="Julgamento de Contas",
        codigo_normalizado="JULGAMENTO_DE_CONTAS",
        nome_exibicao="Julgamento de Contas",
        categoria="JULGAMENTO_EXTERNO",
        eh_proposicao_parlamentar=False,
        contabilizar_producao_vereador=False,
        justificativa=(
            "Excluído da contagem de produção legislativa (ADR-005, Decisão 4): "
            "processo de julgamento de contas anuais do Executivo (TCM-GO)."
        ),
    ),
    213: RegraTipoProposicao(
        tipo_id_origem=213,
        descricao_origem="BALANÇO GERAL",
        codigo_normalizado="BALANCO_GERAL",
        nome_exibicao="Balanço Geral",
        categoria="PRESTACAO_DE_CONTAS",
        eh_proposicao_parlamentar=False,
        contabilizar_producao_vereador=False,
        justificativa=(
            "Excluído da contagem de produção legislativa (ADR-005, Decisão 4): "
            "prestação de contas / balanço contábil da Prefeitura Municipal."
        ),
    ),
    214: RegraTipoProposicao(
        tipo_id_origem=214,
        descricao_origem="Moção de Apoio",
        codigo_normalizado="MOCAO_DE_APOIO",
        nome_exibicao="Moção de Apoio",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Manifestação formal de apoio parlamentar (tipo_id 214 no Nexlegis).",
    ),
    243: RegraTipoProposicao(
        tipo_id_origem=243,
        descricao_origem="PROJETO DE LEI COMPLEMENTAR DO LEGISLATIVO",
        codigo_normalizado="PROJETO_LEI_COMPLEMENTAR_LEGISLATIVO",
        nome_exibicao="Projeto de Lei Complementar do Legislativo",
        categoria="PROPOSICAO_PARLAMENTAR",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Projeto de lei complementar de iniciativa parlamentar (tipo_id 243 no Nexlegis).",
    ),
    375: RegraTipoProposicao(
        tipo_id_origem=375,
        descricao_origem="MENSAGEM DO PREFEITO",
        codigo_normalizado="MENSAGEM_DO_PREFEITO",
        nome_exibicao="Mensagem do Prefeito",
        categoria="EXPEDIENTE_EXECUTIVO",
        eh_proposicao_parlamentar=False,
        contabilizar_producao_vereador=False,
        justificativa=(
            "Excluída da contagem de produção legislativa (ADR-005, Decisão 4): "
            "expediente/mensagem modificativa oriunda do Poder Executivo."
        ),
    ),
}


def classificar_tipo_proposicao(
    tipo_id_origem: int, descricao_origem: str | None
) -> RegraTipoProposicao:
    """Classifica uma matéria retornada pelo Nexlegis segundo as regras do ADR-005.

    - Preserva o registro no banco de dados.
    - Separa Atas (144), Julgamentos de Contas (211) e outros documentos administrativos
      da contagem de produção legislativa parlamentar.
    """
    if tipo_id_origem in MAPA_TIPOS_PROPOSICAO_PADRAO:
        return MAPA_TIPOS_PROPOSICAO_PADRAO[tipo_id_origem]

    desc_limpa = normalizar_texto(descricao_origem) or f"Tipo {tipo_id_origem}"
    chave = gerar_chave_busca(desc_limpa)

    # Heurística documentada para tipos novos não mapeados previamente
    termos_administrativos = (
        "ata",
        "julgamento de contas",
        "balanco geral",
        "veto ao autografo",
        "mensagem do prefeito",
        "oficio",
        "portaria",
        "ato da mesa",
    )
    if any(termo in chave for termo in termos_administrativos):
        return RegraTipoProposicao(
            tipo_id_origem=tipo_id_origem,
            descricao_origem=desc_limpa,
            codigo_normalizado=chave.upper().replace(" ", "_"),
            nome_exibicao=desc_limpa,
            categoria="OUTRO_ADMINISTRATIVO",
            eh_proposicao_parlamentar=False,
            contabilizar_producao_vereador=False,
            justificativa="Classificado como documento administrativo; requer revisão no catálogo de_para.",
        )

    return RegraTipoProposicao(
        tipo_id_origem=tipo_id_origem,
        descricao_origem=desc_limpa,
        codigo_normalizado=chave.upper().replace(" ", "_") or f"TIPO_{tipo_id_origem}",
        nome_exibicao=desc_limpa,
        categoria="PROPOSICAO_PARLAMENTAR_NAO_CATALOGADA",
        eh_proposicao_parlamentar=True,
        contabilizar_producao_vereador=True,
        justificativa="Proposição parlamentar não catalogada; incluída com sinalização para curadoria.",
    )


@dataclass(frozen=True)
class VereadorMestreSeed:
    vereador_id: str
    id_origem_nexlegis: int
    nome_civil: str | None
    nome_politico: str
    nome_exibicao: str
    slug: str
    partido_atual_sigla: str | None
    aliases: tuple[str, ...]


# Tabela mestre curada manualmente para os vereadores de Inhumas (Legislatura 2025-2028)
# a partir das fixtures reais de `nexlegis` e `transparencia` (servidores_cnt Lotação).
VEREADORES_MESTRE_INHUMAS: tuple[VereadorMestreSeed, ...] = (
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-2",
        id_origem_nexlegis=2,
        nome_civil="Adriano Moreira de Sousa",
        nome_politico="ADRIANO MOREIRA",
        nome_exibicao="Adriano Moreira",
        slug="adriano-moreira",
        partido_atual_sigla="PSD",
        aliases=(
            "ADRIANO MOREIRA",
            "Adriano Moreira de Sousa",
            "GAB. DO VEREADOR ADRIANO MOREIRA",
            "GAB. VEREADOR ADRIANO MOREIRA",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-5",
        id_origem_nexlegis=5,
        nome_civil="Edivaldo Ribeiro Dias Júnior",
        nome_politico="EDIVALDO JUNIOR",
        nome_exibicao="Edivaldo Júnior",
        slug="edivaldo-junior",
        partido_atual_sigla="PL",
        aliases=(
            "EDIVALDO JUNIOR",
            "Edivaldo Ribeiro Dias Júnior",
            "GAB. DO VEREADOR EDIVALDO JUNIOR",
            "GAB. VEREADOR EDIVALDO JUNIOR",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-6",
        id_origem_nexlegis=6,
        nome_civil="Gleiton Luiz Roque",
        nome_politico="TUMATE",
        nome_exibicao="Tumate",
        slug="tumate",
        partido_atual_sigla=None,
        aliases=(
            "TUMATE",
            "GLEITON LUIZ ROQUE",
            "GAB. DO VEREADOR TUMATE",
            "GAB. VEREADOR TUMATE",
            "GAB. DO VEREADOR GLEITON LUIZ ROQUE",
            "GAB. DO VEREADOR GLEITON ROQUE",
            "GAB. VEREADOR GLEITON ROQUE",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-7",
        id_origem_nexlegis=7,
        nome_civil="Hêdis Pereira da Silva",
        nome_politico="HEDES DO ESPORTE",
        nome_exibicao="Hêdis do Esporte",
        slug="hedes-do-esporte",
        partido_atual_sigla="PSB",
        aliases=(
            "HEDES DO ESPORTE",
            "Hêdis do Esporte",
            "Hêdis Pereira da Silva",
            "HEDES PEREIRA DA SILVA",
            "GAB. DO VEREADOR HEDES DO ESPORTE",
            "GAB. VEREADOR HEDES DO ESPORTE",
            "GAB. DO VEREADOR HEDES PEREIRA",
            "GAB. VEREADOR HEDES PEREIRA",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-9",
        id_origem_nexlegis=9,
        nome_civil="Leandro Vieira Essado",
        nome_politico="LEANDRO ESSADO",
        nome_exibicao="Leandro Essado",
        slug="leandro-essado",
        partido_atual_sigla="UNIAO",
        aliases=(
            "LEANDRO ESSADO",
            "Leandro Vieira Essado",
            "GAB. DO VEREADOR LEANDRO ESSADO",
            "GAB. VEREADOR LEANDRO ESSADO",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-11",
        id_origem_nexlegis=11,
        nome_civil="Reginaldo de Fátima Gomes Pacheco",
        nome_politico="PROFESSOR REGINALDO PACHECO",
        nome_exibicao="Prof. Reginaldo Pacheco",
        slug="professor-reginaldo-pacheco",
        partido_atual_sigla="PL",
        aliases=(
            "PROF°. REGINALDO PACHECO",
            "PROFESSOR REGINALDO PACHECO",
            "REGINALDO PACHECO",
            "REGINALDO DE FATIMA GOMES PACHECO",
            "Reginaldo de Fátima Gomes Pacheco",
            "GAB. DO VEREADOR REGINALDO PACHECO",
            "GAB. DO VEREADOR PROF. REGINALDO PACHECO",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-81",
        id_origem_nexlegis=81,
        nome_civil="Hugo Leonardo Pessoni",
        nome_politico="HUGO PESSONI",
        nome_exibicao="Hugo Pessoni",
        slug="hugo-pessoni",
        partido_atual_sigla="PP",
        aliases=(
            "HUGO PESSONI",
            "HUGO LEONARDO PESSONI",
            "Hugo Leonardo Pessoni",
            "GAB. DO VEREADOR HUGO PESSONI",
            "GAB. VEREADOR HUGO PESSONI",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-114",
        id_origem_nexlegis=114,
        nome_civil="Clodoaldo da Costa Ferreira",
        nome_politico="CLODOALDO COSTA",
        nome_exibicao="Clodoaldo Costa",
        slug="clodoaldo-costa",
        partido_atual_sigla="PL",
        aliases=(
            "CLODOALDO COSTA",
            "CLODOALDO DA COSTA FERREIRA",
            "Clodoaldo da Costa Ferreira",
            "GAB. DO VEREADOR CLODOALDO COSTA",
            "GAB. VEREADOR CLODOALDO COSTA",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-115",
        id_origem_nexlegis=115,
        nome_civil="Fernando de Andrade Gadia",
        nome_politico="FERNANDO GADIA",
        nome_exibicao="Fernando Gadia",
        slug="fernando-gadia",
        partido_atual_sigla="MDB",
        aliases=(
            "FERNANDO GADIA",
            "Fernando de Andrade Gadia",
            "GAB. VEREADOR FERNANDO GADIA",
            "GAB. DO VEREADOR FERNANDO GADIA",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-147",
        id_origem_nexlegis=147,
        nome_civil="Jôsy Militão Galdine",
        nome_politico="JÔSY MILITÃO",
        nome_exibicao="Jôsy Militão",
        slug="josy-militao",
        partido_atual_sigla="PP",
        aliases=(
            "JÔSY MILITÃO",
            "JOSY MILITAO",
            "Jôsy Militão Galdine",
            "JOSY MILITÃO GALDINE",
            "JOSY MILITAO GALDINE",
            "GAB. DA VEREADORA JOSY MILITAO",
            "GAB. VEREADORA JOSY MILITAO",
            "GAB. VEREADORA JOSY MILITÃO",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-148",
        id_origem_nexlegis=148,
        nome_civil="Julierme Vinícius de Castro Vieira",
        nome_politico="TCHULÃO",
        nome_exibicao="Tchulão",
        slug="tchulao",
        partido_atual_sigla=None,
        aliases=(
            "TCHULÃO",
            "TCHULAO",
            "JULIERME VINICIUS DE CASTRO VIEIRA",
            "Julierme Vinícius de Castro Vieira",
            "JULIERME VINICIUS",
            "GAB. DO VEREADOR TCHULAO",
            "GAB. VEREADOR TCHULAO",
            "GAB. VEREADOR JULIERME VINICIUS",
            "GAB. DO VEREADOR JULIERME VINICIUS",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-149",
        id_origem_nexlegis=149,
        nome_civil="Kelvy Pereira Fernandes",
        nome_politico="PROFESSOR KELVY FERNANDES",
        nome_exibicao="Prof. Kelvy Fernandes",
        slug="professor-kelvy-fernandes",
        partido_atual_sigla="MDB",
        aliases=(
            "PROF°.KELVY FERNANDES",
            "PROFESSOR KELVY FERNANDES",
            "Kelvy Pereira Fernandes",
            "KELVY PEREIRA FERNANDES",
            "GAB. DO VEREADOR KELVY FERNANDES",
            "GAB. VEREADOR KELVY FERNANDES",
            "GAB. VEREADOR KELVY PEREIRA FERNANDES",
            "GAB. DO VEREADOR KELVY PEREIRA FERNANDES",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-180",
        id_origem_nexlegis=180,
        nome_civil="Lucas Ribeiro Gontijo",
        nome_politico="LUCAS RIBEIRO",
        nome_exibicao="Lucas Ribeiro",
        slug="lucas-ribeiro",
        partido_atual_sigla="MDB",
        aliases=(
            "LUCAS RIBEIRO",
            "Lucas Ribeiro Gontijo",
            "GAB. DO VEREADOR LUCAS RIBEIRO",
            "GAB. VEREADOR LUCAS RIBEIRO",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-181",
        id_origem_nexlegis=181,
        nome_civil="Nanci Moreira Arataque Duarte",
        nome_politico="PROFESSORA NANCI ARATAQUE",
        nome_exibicao="Prof.ª Nanci Arataque",
        slug="professora-nanci-arataque",
        partido_atual_sigla="PP",
        aliases=(
            "PROF°. NANCI ARATAQUE",
            "PROFESSORA NANCI ARATAQUE",
            "Nanci Moreira Arataque Duarte",
            "GAB. DA VEREADORA NANCI ARATAQUE",
            "GAB. VEREADORA NANCI ARATAQUE",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-182",
        id_origem_nexlegis=182,
        nome_civil="Rubens Cardoso da Silva",
        nome_politico="RUBENS DA FARMÁCIA",
        nome_exibicao="Rubens da Farmácia",
        slug="rubens-da-farmacia",
        partido_atual_sigla="PSD",
        aliases=(
            "RUBENS DA FARMÁCIA",
            "RUBENS DA FARMACIA",
            "Rubens Cardoso da Silva",
            "RUBENS CARDOSO DA SILVA",
            "RUBENS CARSOSO DA SILVA",
            "GAB. DO VEREADOR RUBENS DA FARMACIA",
            "GAB. VEREADOR RUBENS DA FARMACIA",
            "GAB. VEREADOR RUBENS CARDOSO DA SILVA",
            "GAB. DO VEREADOR RUBENS CARDOSO DA SILVA",
        ),
    ),
    VereadorMestreSeed(
        vereador_id="inhumas-go-ver-246",
        id_origem_nexlegis=246,
        nome_civil="Weber Tiago Pires",
        nome_politico="WEBER ENXOVAIS",
        nome_exibicao="Weber Enxovais",
        slug="weber-enxovais",
        partido_atual_sigla=None,
        aliases=(
            "WEBER TIAGO PIRES",
            "WEBER ENXOVAIS",
            "GAB. DO VEREADOR WEBER TIAGO PIRES",
            "GAB. DO VEREADOR WEBER ENXOVAIS",
        ),
    ),
)


@dataclass(frozen=True)
class ResolucaoVereadorResultado:
    vereador_id: str | None
    confianca: str  # 'ALTA', 'BAIXA_REVISAO_HUMANA'
    motivo: str


class ResolvedorVereadores:
    """Resolve referências de vereadores por ID de origem ou alias curado, sem fusão automática silenciosa."""

    def __init__(
        self,
        municipio_id: str,
        sementes: tuple[VereadorMestreSeed, ...] = VEREADORES_MESTRE_INHUMAS,
    ) -> None:
        self.municipio_id = municipio_id
        self._por_id_nexlegis: dict[int, str] = {}
        self._por_alias_chave: dict[str, str] = {}

        for seed in sementes:
            self._por_id_nexlegis[seed.id_origem_nexlegis] = seed.vereador_id
            for alias in seed.aliases:
                chave_exata = gerar_chave_busca(alias, remover_titulos=False)
                chave_sem_titulo = gerar_chave_busca(alias, remover_titulos=True)
                if chave_exata:
                    self._por_alias_chave[chave_exata] = seed.vereador_id
                if chave_sem_titulo:
                    self._por_alias_chave[chave_sem_titulo] = seed.vereador_id

    def gerar_id_canonico(self, id_origem_nexlegis: int) -> str:
        if id_origem_nexlegis in self._por_id_nexlegis:
            return self._por_id_nexlegis[id_origem_nexlegis]
        return f"{self.municipio_id}-ver-{id_origem_nexlegis}"

    def resolver_por_nome_ou_lotacao(self, texto: str | None) -> ResolucaoVereadorResultado:
        """Resolve nome ou string de lotação ('GAB. DO VEREADOR X') apenas se houver alias curado."""
        if not texto:
            return ResolucaoVereadorResultado(None, "BAIXA_REVISAO_HUMANA", "Texto vazio.")

        for remover_titulos in (False, True):
            chave = gerar_chave_busca(texto, remover_titulos=remover_titulos)
            if chave in self._por_alias_chave:
                return ResolucaoVereadorResultado(
                    vereador_id=self._por_alias_chave[chave],
                    confianca="ALTA",
                    motivo=f"Correspondência exata em alias curado ('{chave}').",
                )

        return ResolucaoVereadorResultado(
            vereador_id=None,
            confianca="BAIXA_REVISAO_HUMANA",
            motivo=(
                f"Nenhum alias curado encontrado para '{texto}'. "
                "Fusão automática silenciosa proibida; requer revisão humana."
            ),
        )
