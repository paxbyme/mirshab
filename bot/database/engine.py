"""SQLAlchemy async engine va sessiya fabrikasi."""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# SQLite'da JSON, PostgreSQL'da JSONB ishlatadigan ustun turi.
JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Barcha modellar uchun asosiy klass."""

    # Modellarda `Base.JSONType` deb ishlatish qulay bo'lsin uchun:
    JSONType = JSONType


_engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(db_url: str, echo: bool = False) -> AsyncEngine:
    """Global engine'ni yaratadi (yoki mavjudini qaytaradi)."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(db_url, echo=echo, pool_pre_ping=True)
    return _engine


def create_session_factory(db_url: str, echo: bool = False) -> async_sessionmaker[AsyncSession]:
    """Sessiya fabrikasini sozlaydi va global o'zgaruvchiga yozadi."""
    global session_factory
    engine = get_engine(db_url, echo=echo)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return session_factory


async def init_models() -> None:
    """Jadvallarni yaratadi (dev/SQLite uchun; prod'da Alembic ishlatiladi)."""
    # models import qilinishi shart — aks holda Base.metadata bo'sh bo'ladi.
    from bot.database import models  # noqa: F401

    assert _engine is not None, "engine yaratilmagan"
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Engine'ni yopadi (graceful shutdown)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
