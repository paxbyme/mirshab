"""Umumiy yordamchi funksiyalar."""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone

from aiogram.types import User


def now_utc() -> datetime:
    """UTC vaqtni timezone-aware ko'rinishda qaytaradi."""
    return datetime.now(timezone.utc)


def user_mention(user: User) -> str:
    """Foydalanuvchiga HTML mention (linkli) qaytaradi."""
    name = html.escape(user.full_name or str(user.id))
    return f'<a href="tg://user?id={user.id}">{name}</a>'


def user_name(user: User) -> str:
    """Foydalanuvchi ismini oddiy (linksiz, ping'siz) HTML-xavfsiz matn qaytaradi."""
    return html.escape(user.full_name or str(user.id))


def mention_by_id(user_id: int, name: str | None = None) -> str:
    """user_id bo'yicha HTML mention."""
    label = html.escape(name) if name else str(user_id)
    return f'<a href="tg://user?id={user_id}">{label}</a>'


_DURATION_UNITS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "soat": 3600,
    "kun": 86400,
    "daqiqa": 60,
}


def normalize_channel_id(value: int | str | None) -> int | str | None:
    """Telegram kanal/superguruh ID'sini normallashtiradi.

    - ``-100...`` ko'rinishidagi to'liq ID         => o'zgarmaydi
    - prefikssiz musbat ID (masalan 3911652365)   => -1003911652365
    - ``@username`` yoki ``t.me/username``         => '@username'
    - None / bo'sh / noto'g'ri                     => None
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.startswith("@"):
            return text
        if "t.me/" in text.lower():
            uname = text.rstrip("/").split("/")[-1].lstrip("@")
            return f"@{uname}" if uname else None
        try:
            value = int(text)
        except ValueError:
            return None
    if value == 0:
        return None
    # Kanal/superguruh ID'lari -100... bo'ladi; prefikssiz musbat sonni tuzatamiz.
    if value > 0:
        return int(f"-100{value}")
    return value


def parse_duration(text: str | None) -> int | None:
    """`10m`, `2h`, `1d`, `30` (daqiqa) ko'rinishidagi muddatni soniyaga aylantiradi.

    None yoki noto'g'ri format => None (cheksiz).
    """
    if not text:
        return None
    text = text.strip().lower()
    # Sof son => daqiqa deb qabul qilamiz
    if text.isdigit():
        return int(text) * 60
    num = ""
    i = 0
    while i < len(text) and text[i].isdigit():
        num += text[i]
        i += 1
    if not num:
        return None
    unit = text[i:].strip()
    mult = _DURATION_UNITS.get(unit, 60)
    return int(num) * mult


def human_duration(seconds: int | None) -> str:
    """Soniyani odam o'qiy oladigan matnga: 3600 -> '1 soat'."""
    if not seconds:
        return "cheksiz"
    parts: list[str] = []
    for unit_sec, name in ((86400, "kun"), (3600, "soat"), (60, "daqiqa"), (1, "soniya")):
        if seconds >= unit_sec:
            qty, seconds = divmod(seconds, unit_sec)
            parts.append(f"{qty} {name}")
    return " ".join(parts) if parts else "0 soniya"


def until_from_seconds(seconds: int | None) -> datetime | None:
    """Hozirdan boshlab N soniyadan keyingi UTC vaqt (None => None)."""
    if not seconds:
        return None
    return now_utc() + timedelta(seconds=seconds)
