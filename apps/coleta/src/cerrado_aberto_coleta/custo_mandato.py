"""Regra de negócio do indicador 'Custo da Estrutura do Mandato' (ADR-005, Decisão 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from cerrado_aberto_coleta import NOTA_OFICIAL_CEAP


@dataclass(frozen=True)
class FolhaServidorItem:
    matricula: str
    nome_servidor: str
    lotacao: str
    vereador_id_atribuido: str | None
    competencia_ano: int
    competencia_mes: int
    proventos_brutos: Decimal | None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    tipo_folha: str = "MENSAL"


@dataclass(frozen=True)
class DiariaItem:
    diaria_id: str
    beneficiario_nome: str | None
    vereador_id_verificado: str | None
    identificacao_documental_verificavel: bool
    data_pagamento: date
    valor_empenhado_liquido: Decimal | None
    valor_liquidado: Decimal | None
    valor_pago: Decimal | None


@dataclass(frozen=True)
class ResultadoCustoEstruturaMandato:
    municipio_id: str
    vereador_id: str
    competencia_ano: int
    competencia_mes: int
    subsidio_bruto_vereador: Decimal | None
    folha_bruta_gabinete: Decimal | None
    diarias_atribuiveis_pagas: Decimal | None
    diarias_atribuiveis_empenhadas: Decimal | None
    diarias_atribuiveis_liquidadas: Decimal | None
    custo_estrutura_mandato_total: Decimal | None
    quantidade_servidores_gabinete: int | None
    nota_cota_parlamentar: str = NOTA_OFICIAL_CEAP
    periodo_declaracao_ceap: str = "2020–2026"
    fonte_url: str = ""
    metodologia_resumo: str = (
        "Custo da Estrutura do Mandato = Subsídio Bruto do Vereador + "
        "Folha Bruta do Gabinete (servidores oficialmente lotados na competência, sem duplicidade "
        "e sem encargos patronais não individualizados) + Diárias Atribuíveis (com identificação "
        "documental verificável do beneficiário). Dados ausentes permanecem nulos (nunca zero)."
    )
    avisos: list[str] = field(default_factory=list)


def calcular_custo_estrutura_mandato(
    *,
    municipio_id: str,
    vereador_id: str,
    competencia_ano: int,
    competencia_mes: int,
    subsidio_bruto_vereador: Decimal | None,
    itens_folha_gabinete: list[FolhaServidorItem] | None,
    itens_diarias: list[DiariaItem] | None,
    fonte_url: str,
) -> ResultadoCustoEstruturaMandato:
    """Calcula o Custo da Estrutura do Mandato respeitando todas as travas do ADR-005.

    Regras críticas:
    1. Dados ausentes (`None`) NÃO são convertidos em `Decimal('0.00')`.
       Se `subsidio_bruto_vereador` ou `itens_folha_gabinete` forem `None` (ex.: lacuna histórica
       pré-2026), o total permanece `None` (indicando dado indisponível para o período).
    2. Evita duplicidade de servidores na mesma competência usando a chave `(matricula, ano, mes)`.
    3. Respeita a vigência histórica da lotação quando `vigencia_inicio`/`vigencia_fim` estiverem presentes.
    4. Não atribui diárias sem `identificacao_documental_verificavel=True` e `vereador_id_verificado == vereador_id`.
    5. Nunca contabiliza a cota parlamentar inexistente como despesa, mas anexa a nota oficial.
    """
    avisos: list[str] = []
    ref_inicio_mes = date(competencia_ano, competencia_mes, 1)

    # 1. Folha Bruta do Gabinete (sem duplicidade por matrícula)
    folha_bruta_gabinete: Decimal | None = None
    qtd_servidores: int | None = None

    if itens_folha_gabinete is None:
        avisos.append(
            f"Folha de pagamento ausente para {competencia_mes:02d}/{competencia_ano}; "
            "valor mantido como nulo (não estimado)."
        )
    else:
        matriculas_vistas: set[str] = set()
        chaves_folha_vistas: set[tuple[str, str]] = set()
        soma_folha = Decimal("0.00")
        possui_valor_nulo = False

        for item in itens_folha_gabinete:
            if item.vereador_id_atribuido != vereador_id:
                continue
            if item.competencia_ano != competencia_ano or item.competencia_mes != competencia_mes:
                continue
            if item.vigencia_inicio is not None and (
                item.vigencia_inicio.year,
                item.vigencia_inicio.month,
            ) > (competencia_ano, competencia_mes):
                continue
            if item.vigencia_fim is not None and item.vigencia_fim < ref_inicio_mes:
                continue

            chave_servidor = item.matricula.strip()
            chave_folha = (chave_servidor, item.tipo_folha.strip().upper())
            if chave_folha in chaves_folha_vistas:
                avisos.append(
                    f"Servidor matrícula '{chave_servidor}' ({item.tipo_folha}) ignorado em duplicidade na competência "
                    f"{competencia_mes:02d}/{competencia_ano}."
                )
                continue

            chaves_folha_vistas.add(chave_folha)
            matriculas_vistas.add(chave_servidor)
            if item.proventos_brutos is None:
                possui_valor_nulo = True
            else:
                soma_folha += item.proventos_brutos.quantize(Decimal("0.01"))

        qtd_servidores = len(matriculas_vistas)
        folha_bruta_gabinete = None if possui_valor_nulo else soma_folha

    # 2. Diárias atribuíveis (diferenciando empenhado, liquidado e pago)
    diarias_pagas: Decimal | None = None
    diarias_empenhadas: Decimal | None = None
    diarias_liquidadas: Decimal | None = None

    if itens_diarias is None:
        avisos.append(
            f"Base de diárias ausente para {competencia_mes:02d}/{competencia_ano}; "
            "valor mantido como nulo."
        )
    else:
        soma_pago = Decimal("0.00")
        soma_emp = Decimal("0.00")
        soma_liq = Decimal("0.00")
        ids_diarias_vistos: set[str] = set()

        for diaria in itens_diarias:
            if not diaria.identificacao_documental_verificavel:
                avisos.append(
                    f"Diária '{diaria.diaria_id}' não atribuída por ausência de identificação "
                    "documental verificável do beneficiário."
                )
                continue
            if diaria.vereador_id_verificado != vereador_id:
                continue
            if (
                diaria.data_pagamento.year != competencia_ano
                or diaria.data_pagamento.month != competencia_mes
            ):
                continue
            if diaria.diaria_id in ids_diarias_vistos:
                continue
            ids_diarias_vistos.add(diaria.diaria_id)

            if diaria.valor_pago is not None:
                soma_pago += diaria.valor_pago.quantize(Decimal("0.01"))
            if diaria.valor_empenhado_liquido is not None:
                soma_emp += diaria.valor_empenhado_liquido.quantize(Decimal("0.01"))
            if diaria.valor_liquidado is not None:
                soma_liq += diaria.valor_liquidado.quantize(Decimal("0.01"))

        diarias_pagas = soma_pago
        diarias_empenhadas = soma_emp
        diarias_liquidadas = soma_liq

    # 3. Cálculo do total: só soma se todos os 3 componentes tiverem dados conhecidos (não nulos)
    custo_total: Decimal | None = None
    if (
        subsidio_bruto_vereador is not None
        and folha_bruta_gabinete is not None
        and diarias_pagas is not None
    ):
        custo_total = (
            subsidio_bruto_vereador.quantize(Decimal("0.01"))
            + folha_bruta_gabinete
            + diarias_pagas
        )
    else:
        avisos.append(
            "Custo total da estrutura do mandato não calculado porque ao menos um componente "
            "obrigatório está ausente (dados ausentes nunca são convertidos em zero)."
        )

    return ResultadoCustoEstruturaMandato(
        municipio_id=municipio_id,
        vereador_id=vereador_id,
        competencia_ano=competencia_ano,
        competencia_mes=competencia_mes,
        subsidio_bruto_vereador=subsidio_bruto_vereador,
        folha_bruta_gabinete=folha_bruta_gabinete,
        diarias_atribuiveis_pagas=diarias_pagas,
        diarias_atribuiveis_empenhadas=diarias_empenhadas,
        diarias_atribuiveis_liquidadas=diarias_liquidadas,
        custo_estrutura_mandato_total=custo_total,
        quantidade_servidores_gabinete=qtd_servidores,
        fonte_url=fonte_url,
        avisos=avisos,
    )
