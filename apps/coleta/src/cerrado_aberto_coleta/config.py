"""Configuração multi-município parametrizada (sem constantes acopladas no código de coleta)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cerrado_aberto_coleta import VERSAO_COLETOR_PADRAO


@dataclass(frozen=True)
class FonteConfig:
    fonte_id: str
    url_base: str
    crawl_delay_segundos: float = 3.0
    timeout_segundos: float = 20.0
    max_tentativas: int = 3


@dataclass(frozen=True)
class MunicipioConfig:
    municipio_id: str
    codigo_ibge: str
    nome: str
    uf: str
    user_agent: str = (
        "CerradoAbertoBot/0.1 (+https://cerradoaberto.org.br; contato@cerradoaberto.org.br)"
    )
    versao_coletor: str = VERSAO_COLETOR_PADRAO
    raw_dir: Path = field(default_factory=lambda: Path("data/raw"))
    fontes: dict[str, FonteConfig] = field(default_factory=dict)

    def obter_fonte(self, fonte_id: str) -> FonteConfig:
        if fonte_id not in self.fontes:
            raise KeyError(
                f"Fonte '{fonte_id}' não configurada para o município '{self.municipio_id}'."
            )
        return self.fontes[fonte_id]


def criar_config_municipio_padrao(raw_dir: Path | None = None) -> MunicipioConfig:
    """Retorna a configuração parametrizada do município inicial (Inhumas/GO)."""
    return MunicipioConfig(
        municipio_id="inhumas-go",
        codigo_ibge="5210000",
        nome="Inhumas",
        uf="GO",
        raw_dir=raw_dir or Path("data/raw"),
        fontes={
            "nexlegis": FonteConfig(
                fonte_id="nexlegis",
                url_base="https://inhumas.nexlegis.com.br/api",
                crawl_delay_segundos=3.0,
            ),
            "transparencia_centi": FonteConfig(
                fonte_id="transparencia_centi",
                url_base="https://acessoainformacao.inhumas.go.leg.br/api/centi",
                crawl_delay_segundos=5.0,
            ),
            "transparencia_nucleogov": FonteConfig(
                fonte_id="transparencia_nucleogov",
                url_base="https://acessoainformacao.inhumas.go.leg.br/api",
                crawl_delay_segundos=5.0,
            ),
            "legislacao_nucleogov": FonteConfig(
                fonte_id="legislacao_nucleogov",
                url_base="https://acessoainformacao.inhumas.go.leg.br/api",
                crawl_delay_segundos=5.0,
            ),
        },
    )
