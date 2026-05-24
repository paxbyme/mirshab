"""Foydalanuvchi profilini tekshirish: bio'dagi havola + profil kanali (personal_chat).

Profilga jalb qiluvchi spam-botlar odamlarni o'z profili/biosidagi havolaga yoki
profil kanaliga yo'naltiradi. Bu modul `get_chat(user_id)` orqali shu "jalb
maqsadi" bor-yo'qligini aniqlaydi. Natija foydalanuvchi bo'yicha keshlanadi
(bio kam o'zgaradi), shuning uchun har bir xabarda qayta so'ralmaydi.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.services.link_detector import extract_links
from bot.utils.logger import logger

_TTL = 3600.0  # 1 soat — bio kam o'zgaradi
_cache: dict[int, tuple[float, "ProfileInfo"]] = {}


@dataclass
class ProfileInfo:
    """Foydalanuvchi profilidagi "jalb maqsadi" haqida ma'lumot."""

    bio: str = ""
    bio_links: list[str] = field(default_factory=list)       # bio'dagi URL/@username
    personal_channel: str | None = None                       # profil kanali (@username yoki nomi)
    has_target: bool = False                                  # jalb qilinadigan manzil bormi

    def summary(self) -> str:
        """AI uchun qisqa kontekst satri."""
        parts = []
        if self.bio:
            parts.append(f"bio: {self.bio[:200]}")
        if self.bio_links:
            parts.append(f"bio havolalari: {', '.join(self.bio_links[:5])}")
        if self.personal_channel:
            parts.append(f"profil kanali: {self.personal_channel}")
        return " | ".join(parts) if parts else "profil bo'sh"


def _cache_get(user_id: int) -> ProfileInfo | None:
    entry = _cache.get(user_id)
    if entry and entry[0] > time.monotonic():
        return entry[1]
    return None


def invalidate(user_id: int) -> None:
    _cache.pop(user_id, None)


async def get_profile(bot: Bot, user_id: int) -> ProfileInfo:
    """Foydalanuvchi profilini (keshdan yoki get_chat orqali) qaytaradi.

    Xatolik/maxfiylik holatida bo'sh ProfileInfo (has_target=False) qaytadi.
    """
    cached = _cache_get(user_id)
    if cached is not None:
        return cached

    info = ProfileInfo()
    try:
        chat = await bot.get_chat(user_id)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.debug(f"get_chat({user_id}) muvaffaqiyatsiz: {e}")
        chat = None
    except Exception as e:  # noqa: BLE001
        logger.debug(f"get_chat({user_id}) xatosi: {e}")
        chat = None

    if chat is not None:
        bio = (getattr(chat, "bio", None) or "").strip()
        info.bio = bio
        if bio:
            scan = extract_links(bio)
            info.bio_links = list(scan.urls) + [f"@{u}" for u in scan.usernames]

        personal = getattr(chat, "personal_chat", None)
        if personal is not None:
            info.personal_channel = (
                f"@{personal.username}" if personal.username
                else (personal.title or "kanal")
            )

    info.has_target = bool(info.bio_links or info.personal_channel)
    _cache[user_id] = (time.monotonic() + _TTL, info)
    return info
