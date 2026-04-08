"""DB resolver: maps user_id to per-user SQLite vault database."""

from __future__ import annotations

import os
import sqlite3
from typing import Generator

from fastapi import Depends, Request

from app.config import settings

from readloot.db import get_db_connection


def get_user_db(user_id: int) -> sqlite3.Connection:
    """Return a sqlite3.Connection for the given user's vault database."""
    vault_dir = os.path.join(settings.DATA_DIR, "vaults", str(user_id))
    os.makedirs(vault_dir, exist_ok=True)
    db_path = os.path.join(vault_dir, "vault.db")
    return get_db_connection(db_path)


def get_db(request: Request) -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency that provides a DB connection and auto-closes it."""
    from app.auth import get_current_user
    user = get_current_user(request)
    conn = get_user_db(user["user_id"])
    try:
        yield conn
    finally:
        conn.close()
