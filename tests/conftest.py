"""Shared test fixtures for Vocabulary Vault tests."""

import sqlite3
import tempfile

import pytest

from vocabulary_vault.db import init_schema


@pytest.fixture
def db_conn():
    """Provide a fresh in-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    init_schema(conn)

    yield conn
    conn.close()


@pytest.fixture
def vault_dir():
    """Provide a temporary directory for Markdown vault files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
