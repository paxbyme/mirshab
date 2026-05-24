"""DB URL normalizatsiyasi uchun testlar (Railway/Heroku formatlar)."""

import pytest

from bot.config import Settings, normalize_db_url


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Railway/Heroku eski sxema
        (
            "postgres://u:p@host:5432/db",
            "postgresql+asyncpg://u:p@host:5432/db",
        ),
        # Standart postgresql sxema
        (
            "postgresql://u:p@host:5432/db",
            "postgresql+asyncpg://u:p@host:5432/db",
        ),
        # Allaqachon to'g'ri — tegilmaydi
        (
            "postgresql+asyncpg://u:p@host/db",
            "postgresql+asyncpg://u:p@host/db",
        ),
        # SQLite — tegilmaydi
        (
            "sqlite+aiosqlite:///mirshab.db",
            "sqlite+aiosqlite:///mirshab.db",
        ),
    ],
)
def test_scheme_normalization(raw, expected):
    assert normalize_db_url(raw) == expected


def test_sslmode_require_becomes_ssl():
    out = normalize_db_url("postgres://u:p@host:5432/db?sslmode=require")
    assert out.startswith("postgresql+asyncpg://")
    assert "sslmode" not in out
    assert "ssl=require" in out


def test_sslmode_disable_dropped_without_ssl():
    out = normalize_db_url("postgresql://u:p@host/db?sslmode=disable")
    assert "sslmode" not in out
    assert "ssl=" not in out


def test_other_query_params_preserved():
    out = normalize_db_url(
        "postgresql://u:p@host/db?sslmode=require&application_name=mirshab"
    )
    assert "application_name=mirshab" in out
    assert "ssl=require" in out


def test_settings_reads_database_url(monkeypatch):
    """Railway `DATABASE_URL` ni o'qib, asyncpg uchun normallashtirsin."""
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:5432/railway?sslmode=require")
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.db_url == "postgresql+asyncpg://u:p@host:5432/railway?ssl=require"
    assert s.is_sqlite is False


def test_db_url_takes_precedence_over_database_url(monkeypatch):
    monkeypatch.setenv("DB_URL", "sqlite+aiosqlite:///mirshab.db")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.is_sqlite is True
