"""Tests for the auth module: register, login, logout, JWT validation."""

import sqlite3

from app.auth import COOKIE_NAME
from app.config import settings


class TestRegister:
    def test_register_returns_cookie(self, client):
        resp = client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "alice"
        assert COOKIE_NAME in resp.cookies

    def test_register_duplicate_username(self, client):
        client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        resp = client.post("/api/auth/register", json={"username": "alice", "password": "otherpass123"})
        assert resp.status_code == 400

    def test_password_is_hashed(self, client):
        client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        db_path = f"{settings.DATA_DIR}/users.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT password_hash FROM users WHERE username = 'alice'").fetchone()
        conn.close()
        assert row is not None
        assert row["password_hash"] != "pass1234"
        assert row["password_hash"].startswith("$2b$")


class TestLogin:
    def test_login_valid(self, client):
        client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        resp = client.post("/api/auth/login", json={"username": "alice", "password": "pass1234"})
        assert resp.status_code == 200
        assert COOKIE_NAME in resp.cookies

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        resp = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "password123"})
        assert resp.status_code == 401


class TestLogout:
    def test_logout_clears_cookie(self, client):
        client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        resp = client.post("/api/auth/logout")
        # After logout the cookie should be deleted (max-age=0 or empty)
        cookie_header = resp.headers.get("set-cookie", "")
        assert COOKIE_NAME in cookie_header
        assert 'Max-Age=0' in cookie_header or '=""' in cookie_header


class TestProtectedEndpoints:
    def test_no_cookie_returns_401(self, client):
        resp = client.get("/api/stats/profile")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        client.cookies.set(COOKIE_NAME, "garbage.token.value")
        resp = client.get("/api/stats/profile")
        assert resp.status_code == 401
