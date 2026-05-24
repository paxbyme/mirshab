"""Guruh sozlamalari uchun qisqa muddatli xotira keshi (DB yukini kamaytiradi)."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud

_TTL = 60.0  # soniya
_cache: dict[int, tuple[float, dict[str, Any]]] = {}


async def get_cached_settings(session: AsyncSession, group_id: int) -> dict[str, Any]:
    """Guruh sozlamalarini keshdan yoki DB'dan qaytaradi."""
    now = time.monotonic()
    cached = _cache.get(group_id)
    if cached and cached[0] > now:
        return cached[1]
    settings = await crud.get_group_settings(session, group_id)
    _cache[group_id] = (now + _TTL, settings)
    return settings


def invalidate(group_id: int) -> None:
    """Sozlama o'zgargach keshni tozalash."""
    _cache.pop(group_id, None)


def clear() -> None:
    _cache.clear()
