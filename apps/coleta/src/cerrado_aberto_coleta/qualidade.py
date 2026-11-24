"""Verificações e relatório de qualidade de dados (skill qualidade-de-dados)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from cerrado_aberto_coleta.nexlegis.loader import InMemoryNexlegisRepository


@dataclass(frozen=True)
class RelatorioQualidadeNexlegis:
    municipio_id: str
    total_vereadores: int
    total_sessoes: int
    total_presencas: int
    total_proposicoes_armazenadas: int
    total_proposicoes_parlamentares: int
    total_documentos_administrativos_separados: int
    total_votacoes: int
    total_votos_nominais: int
    data_sessao_mais_antiga: date | None
    data_sessao_mais_recente: date | None
    data_materia_mais_antiga: date | None
    data_materia_mais_recente: date | None
    proveniencia_100_porcento: bool
    inconsistencias_cruzadas: list[str] = field(default_factory=list)
    aprovado_para_publicacao: bool = True


def avaliar_qualidade_repositorio(
    repo: InMemoryNexlegisRepository, *, municipio_id: str
) -> RelatorioQualidadeNexlegis:
    """Executa bateria de qualidade (schema, proveniência, separação de atas e consistência cruzada)."""
    inconsistencias: list[str] = []

    todas_colecoes = (
        list(repo.vereadores.ativos.values())
        + list(repo.sessoes.ativos.values())
        + list(repo.presencas.ativos.values())
        + list(repo.proposicoes.ativos.values())
        + list(repo.autorias.ativos.values())
        + list(repo.tramitacoes.ativos.values())
        + list(repo.pauta_itens.ativos.values())
        + list(repo.votacoes.ativos.values())
        + list(repo.votos.ativos.values())
    )

    proveniencia_ok = True
    for reg in todas_colecoes:
        if (
            not reg.municipio_id
            or not reg.fonte_url
            or not reg.coletado_em
            or len(reg.hash_conteudo) != 64
            or not reg.versao_coletor
        ):
            proveniencia_ok = False
            inconsistencias.append(f"Registro sem proveniência completa: {reg!r}")

    # Consistência: Atas (144) e Julgamentos de Contas (211) nunca podem ter contabilizar_producao_vereador=True
    for prop in repo.proposicoes.ativos.values():
        if prop.tipo_id_origem in (144, 211) and prop.contabilizar_producao_vereador:
            inconsistencias.append(
                f"Proposição {prop.proposicao_id} (tipo_id={prop.tipo_id_origem}) marcada "
                "indevidamente para contabilizar na produção parlamentar."
            )

    # Consistência cruzada: toda votação deve apontar para uma sessão existente
    for vot in repo.votacoes.ativos.values():
        if vot.sessao_id not in repo.sessoes.ativos:
            inconsistencias.append(
                f"Votação {vot.votacao_id} referencia sessão inexistente {vot.sessao_id}."
            )

    datas_sessoes = [s.data_abertura for s in repo.sessoes.ativos.values()]
    datas_materias = [
        p.data_publicacao for p in repo.proposicoes.ativos.values() if p.data_publicacao is not None
    ]

    props_parlamentares = sum(
        1 for p in repo.proposicoes.ativos.values() if p.eh_proposicao_parlamentar
    )
    docs_admin = len(repo.proposicoes.ativos) - props_parlamentares

    aprovado = proveniencia_ok and len(inconsistencias) == 0

    return RelatorioQualidadeNexlegis(
        municipio_id=municipio_id,
        total_vereadores=len(repo.vereadores.ativos),
        total_sessoes=len(repo.sessoes.ativos),
        total_presencas=len(repo.presencas.ativos),
        total_proposicoes_armazenadas=len(repo.proposicoes.ativos),
        total_proposicoes_parlamentares=props_parlamentares,
        total_documentos_administrativos_separados=docs_admin,
        total_votacoes=len(repo.votacoes.ativos),
        total_votos_nominais=len(repo.votos.ativos),
        data_sessao_mais_antiga=min(datas_sessoes) if datas_sessoes else None,
        data_sessao_mais_recente=max(datas_sessoes) if datas_sessoes else None,
        data_materia_mais_antiga=min(datas_materias) if datas_materias else None,
        data_materia_mais_recente=max(datas_materias) if datas_materias else None,
        proveniencia_100_porcento=proveniencia_ok,
        inconsistencias_cruzadas=inconsistencias,
        aprovado_para_publicacao=aprovado,
    )
