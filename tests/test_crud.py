"""crud uchun integratsion testlar (in-memory SQLite)."""

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database.engine import Base
from bot.database import crud, models  # noqa: F401


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_group_create_and_settings(session):
    g = await crud.get_or_create_group(session, 100, "Test guruh")
    assert g.id == 100
    updated = await crud.update_group_settings(session, 100, link_filter_on=False)
    assert updated["link_filter_on"] is False
    assert updated["nsfw_filter_on"] is True  # default saqlanadi


@pytest.mark.asyncio
async def test_warning_flow(session):
    await crud.get_or_create_group(session, 1, "g")
    n1 = await crud.add_warning(session, 1, 555)
    n2 = await crud.add_warning(session, 1, 555)
    assert (n1, n2) == (1, 2)
    await crud.reset_warnings(session, 1, 555)
    m = await crud.get_member(session, 1, 555)
    assert m.warnings == 0


@pytest.mark.asyncio
async def test_whitelist_crud(session):
    await crud.get_or_create_group(session, 1, "g")
    assert await crud.add_whitelist(session, 1, "Example.com", by := 1) is True
    # ikkinchi marta — dublikat
    assert await crud.add_whitelist(session, 1, "example.com", by) is False
    items = await crud.list_whitelist(session, 1)
    assert items[0].pattern == "example.com"
    assert await crud.remove_whitelist(session, 1, "example.com") is True


@pytest.mark.asyncio
async def test_concurrent_group_create_no_crash(tmp_path):
    """Bot guruhga qo'shilganda bir nechta update bir vaqtda kelib, har biri
    o'z sessiyasida shu guruhni yaratmoqchi bo'ladi. Avval bu
    `UNIQUE constraint failed: groups.id` xatosini berardi."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'race.db'}"
    # busy timeout — bir nechta yozuvchi connection lock uchun kutib tursin
    engine = create_async_engine(url, connect_args={"timeout": 30})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def worker() -> int:
        async with factory() as s:
            g = await crud.get_or_create_group(s, 999, "race")
            await s.commit()
            return g.id

    ids = await asyncio.gather(*(worker() for _ in range(8)))
    assert set(ids) == {999}

    async with factory() as s:
        rows = await crud.all_groups(s)
    assert len([r for r in rows if r.id == 999]) == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_logs_and_stats(session):
    await crud.get_or_create_group(session, 1, "g")
    await crud.add_log(session, 1, "delete", user_id=9, reason="link")
    await crud.add_log(session, 1, "ban", user_id=9, reason="spam")
    stats = await crud.daily_stats(session, 1)
    assert stats.get("delete") == 1 and stats.get("ban") == 1
    logs = await crud.recent_logs(session, 1, limit=5)
    assert len(logs) == 2
