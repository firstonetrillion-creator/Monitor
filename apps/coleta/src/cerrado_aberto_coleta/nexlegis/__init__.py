"""Coletor da fonte Nexlegis (Fase 1) em 3 etapas: fetch → parse → load."""

from cerrado_aberto_coleta.nexlegis.fetcher import NexlegisFetcher
from cerrado_aberto_coleta.nexlegis.loader import (
    InMemoryNexlegisRepository,
    ResultadoCarga,
)
from cerrado_aberto_coleta.nexlegis.lote2 import ExecutorLote2Nexlegis
from cerrado_aberto_coleta.nexlegis.parser import LayoutQuebradoError, NexlegisParser
from cerrado_aberto_coleta.nexlegis.postgres_loader import (
    PostgresNexlegisRepository,
    ViolacaoLGPDError,
    carregar_bienio_2025_2026_no_postgres,
    carregar_lote1_2026_no_postgres,
    carregar_lote2_2025_no_postgres,
    validar_ausencia_cpf_em_valores,
)

__all__ = [
    "ExecutorLote2Nexlegis",
    "InMemoryNexlegisRepository",
    "LayoutQuebradoError",
    "NexlegisFetcher",
    "NexlegisParser",
    "PostgresNexlegisRepository",
    "ResultadoCarga",
    "ViolacaoLGPDError",
    "carregar_bienio_2025_2026_no_postgres",
    "carregar_lote1_2026_no_postgres",
    "carregar_lote2_2025_no_postgres",
    "validar_ausencia_cpf_em_valores",
]
