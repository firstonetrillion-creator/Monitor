"""Fixtures compartilhadas da suíte de testes de apps/coleta."""

from __future__ import annotations

from pathlib import Path

import pgserver
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def pg_uri() -> str:
    """Inicializa o cluster PostgreSQL 16 local uma única vez por sessão de testes."""
    pgdata_dir = REPO_ROOT / "data" / "pgdata"
    pgdata_dir.mkdir(parents=True, exist_ok=True)
    srv = pgserver.get_server(str(pgdata_dir))
    return str(srv.get_uri())
