"""Etapa 3 (Load) do coletor Nexlegis: persistência idempotente com versionamento de alterações."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self, TypeVar

from pydantic import BaseModel

from cerrado_aberto_coleta.nexlegis.schemas import (
    AutoriaRegistro,
    PacoteMateriasParseado,
    PacoteSessaoDetalheParseado,
    PautaItemRegistro,
    PresencaRegistro,
    ProposicaoRegistro,
    SessaoRegistro,
    TramitacaoRegistro,
    VereadorRegistro,
    VotacaoRegistro,
    VotoNominalRegistro,
)

T = TypeVar("T", bound=BaseModel)


@dataclass
class ResultadoCarga:
    lidos: int = 0
    novos: int = 0
    alterados: int = 0
    inalterados: int = 0

    def __iadd__(self, outro: ResultadoCarga) -> Self:
        self.lidos += outro.lidos
        self.novos += outro.novos
        self.alterados += outro.alterados
        self.inalterados += outro.inalterados
        return self


@dataclass
class TabelaVersionada[T: BaseModel]:
    """Armazena registros ativos e mantém histórico de versões anteriores quando o conteúdo muda."""

    ativos: dict[str, T] = field(default_factory=dict)
    historico_versoes: list[T] = field(default_factory=list)

    def _assinatura_sem_timestamp(self, registro: T) -> dict:
        dados = registro.model_dump()
        dados.pop("coletado_em", None)
        return dados

    def upsert(self, chave: str, registro: T) -> str:
        if chave not in self.ativos:
            self.ativos[chave] = registro
            return "NOVO"

        atual = self.ativos[chave]
        if self._assinatura_sem_timestamp(atual) == self._assinatura_sem_timestamp(registro):
            return "INALTERADO"

        self.historico_versoes.append(atual)
        self.ativos[chave] = registro
        return "ALTERADO"


class InMemoryNexlegisRepository:
    """Repositório idempotente com semântica idêntica ao banco PostgreSQL para execução e testes."""

    def __init__(self) -> None:
        self.vereadores: TabelaVersionada[VereadorRegistro] = TabelaVersionada()
        self.sessoes: TabelaVersionada[SessaoRegistro] = TabelaVersionada()
        self.presencas: TabelaVersionada[PresencaRegistro] = TabelaVersionada()
        self.proposicoes: TabelaVersionada[ProposicaoRegistro] = TabelaVersionada()
        self.autorias: TabelaVersionada[AutoriaRegistro] = TabelaVersionada()
        self.tramitacoes: TabelaVersionada[TramitacaoRegistro] = TabelaVersionada()
        self.pauta_itens: TabelaVersionada[PautaItemRegistro] = TabelaVersionada()
        self.votacoes: TabelaVersionada[VotacaoRegistro] = TabelaVersionada()
        self.votos: TabelaVersionada[VotoNominalRegistro] = TabelaVersionada()

        # Índice auxiliar de chave natural de sessão para evitar duplicação (ex.: IDs 969 e 1002)
        self._chave_natural_sessao_para_id: dict[tuple, str] = {}

    def _contabilizar(self, status: str, res: ResultadoCarga) -> None:
        res.lidos += 1
        if status == "NOVO":
            res.novos += 1
        elif status == "ALTERADO":
            res.alterados += 1
        else:
            res.inalterados += 1

    def carregar_vereadores(self, registros: list[VereadorRegistro]) -> ResultadoCarga:
        res = ResultadoCarga()
        for r in registros:
            status = self.vereadores.upsert(r.vereador_id, r)
            self._contabilizar(status, res)
        return res

    def carregar_sessoes(self, registros: list[SessaoRegistro]) -> ResultadoCarga:
        res = ResultadoCarga()
        for r in registros:
            chave_nat = (r.municipio_id, r.tipo_id_origem, r.numero, r.ano, r.data_abertura)
            sessao_id_alvo = self._chave_natural_sessao_para_id.get(chave_nat, r.sessao_id)
            if sessao_id_alvo != r.sessao_id:
                existente = self.sessoes.ativos[sessao_id_alvo]
                dups = tuple(
                    sorted(set(existente.ids_origem_duplicados + (r.id_origem_nexlegis,)))
                )
                r_atualizado = existente.model_copy(update={"ids_origem_duplicados": dups})
                status = self.sessoes.upsert(sessao_id_alvo, r_atualizado)
            else:
                self._chave_natural_sessao_para_id[chave_nat] = r.sessao_id
                status = self.sessoes.upsert(r.sessao_id, r)
            self._contabilizar(status, res)
        return res

    def carregar_pacote_sessao_detalhe(
        self, pacote: PacoteSessaoDetalheParseado
    ) -> ResultadoCarga:
        res = self.carregar_sessoes([pacote.sessao])
        for p in pacote.presencas:
            self._contabilizar(self.presencas.upsert(p.presenca_id, p), res)
        for prop in pacote.proposicoes_pauta:
            self._contabilizar(self.proposicoes.upsert(prop.proposicao_id, prop), res)
        for item in pacote.pauta_itens:
            self._contabilizar(self.pauta_itens.upsert(item.pauta_item_id, item), res)
        for vot in pacote.votacoes:
            self._contabilizar(self.votacoes.upsert(vot.votacao_id, vot), res)
        for voto in pacote.votos_nominais:
            self._contabilizar(self.votos.upsert(voto.voto_id, voto), res)
        return res

    def carregar_pacote_materias(self, pacote: PacoteMateriasParseado) -> ResultadoCarga:
        res = ResultadoCarga()
        for prop in pacote.proposicoes:
            self._contabilizar(self.proposicoes.upsert(prop.proposicao_id, prop), res)
        for aut in pacote.autorias:
            self._contabilizar(self.autorias.upsert(aut.autoria_id, aut), res)
        for tram in pacote.tramitacoes:
            self._contabilizar(self.tramitacoes.upsert(tram.tramitacao_id, tram), res)
        return res

    def contar_producao_legislativa_por_vereador(self) -> dict[str, int]:
        """Contabiliza apenas proposições parlamentares (`contabilizar_producao_vereador=True`).

        Regra ADR-005 (Decisão 4): Atas da Sessão (`tipo_id=144`), Julgamentos de Contas (`tipo_id=211`)
        e outros documentos administrativos permanecem em `self.proposicoes`, mas são excluídos da
        contagem de produção legislativa parlamentar.
        """
        contagem: dict[str, int] = {}
        for autoria in self.autorias.ativos.values():
            if autoria.vereador_id is None:
                continue
            prop = self.proposicoes.ativos.get(autoria.proposicao_id)
            if prop is None or not prop.contabilizar_producao_vereador:
                continue
            contagem[autoria.vereador_id] = contagem.get(autoria.vereador_id, 0) + 1
        return contagem
