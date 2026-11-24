"""Gerenciamento de conexão PostgreSQL 16 para a API FastAPI."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

_PG_SERVER_LOCAL: Any = None
_DB_URI_ATIVO: str | None = None
_DB_LOCK = threading.Lock()


def obter_raiz_repositorio() -> Path:
    return Path(__file__).resolve().parents[4]


def configurar_uri_banco(uri: str) -> None:
    """Permite injetar a URI do banco PostgreSQL (útil para testes e ambientes customizados)."""
    global _DB_URI_ATIVO
    _DB_URI_ATIVO = uri


def _preparar_pgdata_windows(pgdata_dir: Path) -> None:
    """Evita bloqueio de 30s no Windows por sharing violation em ./log durante fsync de recovery."""
    conf_path = pgdata_dir / "postgresql.conf"
    if conf_path.exists():
        texto = conf_path.read_text(encoding="utf-8", errors="ignore")
        if "\nfsync = off" not in texto:
            with conf_path.open("a", encoding="utf-8") as fp:
                fp.write("\nfsync = off\n")


def obter_uri_banco() -> str:
    """Retorna a URI PostgreSQL ativa (`DATABASE_URL` ou cluster local PostgreSQL 16 em `data/pgdata`)."""
    global _PG_SERVER_LOCAL, _DB_URI_ATIVO
    if _DB_URI_ATIVO:
        return _DB_URI_ATIVO

    with _DB_LOCK:
        if _DB_URI_ATIVO:
            return _DB_URI_ATIVO

        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            _DB_URI_ATIVO = env_url
            return env_url

        import pgserver
        from pgserver.postgres_server import PostgresServer
        from pgserver.utils import PostmasterInfo

        pgdata_dir = (obter_raiz_repositorio() / "data" / "pgdata").resolve()
        pgdata_dir.mkdir(parents=True, exist_ok=True)
        _preparar_pgdata_windows(pgdata_dir)

        if _PG_SERVER_LOCAL is None:
            try:
                _PG_SERVER_LOCAL = pgserver.get_server(str(pgdata_dir))
            except subprocess.TimeoutExpired:
                PostgresServer._instances.pop(pgdata_dir, None)
                for _ in range(40):
                    pinfo = PostmasterInfo.read_from_pgdata(pgdata_dir)
                    if pinfo is not None and pinfo.is_running() and pinfo.status == "ready":
                        break
                    time.sleep(1.0)
                _PG_SERVER_LOCAL = pgserver.get_server(str(pgdata_dir))

        _DB_URI_ATIVO = str(_PG_SERVER_LOCAL.get_uri())
        return _DB_URI_ATIVO


def obter_conexao_db() -> Generator[psycopg.Connection[dict[str, Any]], None, None]:
    """Dependência FastAPI que abre uma conexão PostgreSQL 16 somente leitura por requisição."""
    uri = obter_uri_banco()
    with psycopg.connect(uri, row_factory=dict_row) as conn:
        conn.read_only = True
        yield conn
