"""Akkaunt/profil heuristikasi — spam-bot akkauntlarining qo'shimcha signallari.

Bu modul rasm yoki tarmoq talab qilmaydi: faqat foydalanuvchining ko'rinadigan
ismi va username'iga qarab "shubhalilik" skorini qaytaradi. Yolg'iz holda ban
sababi BO'LMAYDI — moderatsiyada chegaradagi bait xabarini kuchaytirish uchun
ishlatiladi (bait shubhasi + shubhali akkaunt => ban).

Spam-botlar uchun tipik belgilar: ismda flirt emoji ("Anna 💋"), username yo'qligi,
ism/usernameda ochiq so'zlar, username oxirida ko'p raqam ("anna_45219").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Ismda uchraydigan flirt emojilari (botlar e'tibor tortish uchun ishlatadi)
_FLIRTY_EMOJI = "💞💕❤🩷💗💓💖💘💝💋😘😍🥰😏🔥👅🍑🍒😈💦💃👄"

# Ism yoki usernamedagi ochiq/tanishuv so'zlari (uz/ru/translit)
_SUGGESTIVE_NAME_RE = re.compile(
    r"(?:escort|эскорт|intim|интим|seks|секс|\bsex\b|xxx|porn|порн|nude|"
    r"dosug|досуг|znakomstv|знакомств|свидан|massaj|массаж|relax|"
    r"девочк|малышк|крошк|sweet|baby|kiss)",
    re.I,
)
_TRAILING_DIGITS_RE = re.compile(r"\d{4,}$")


@dataclass
class AccountVerdict:
    """Akkaunt heuristikasi natijasi."""

    score: float = 0.0
    signals: list[str] = field(default_factory=list)

    @property
    def is_suspicious(self) -> bool:
        # Konservativ chegara: bitta kuchli signal (emoji/ochiq so'z) yetarli,
        # ammo yolg'iz "username yo'q" yetarli emas (ko'p haqiqiy foydalanuvchi).
        return self.score >= 0.5


def analyze_account(full_name: str | None, username: str | None) -> AccountVerdict:
    """Ko'rinadigan ism + username asosida shubhalilik skorini hisoblaydi."""
    verdict = AccountVerdict()
    name = (full_name or "").strip()
    uname = (username or "").strip()

    if not uname:
        verdict.score += 0.25
        verdict.signals.append("username yo'q")

    if any(e in name for e in _FLIRTY_EMOJI):
        verdict.score += 0.5
        verdict.signals.append("ismda flirt emoji")

    if _SUGGESTIVE_NAME_RE.search(name) or (uname and _SUGGESTIVE_NAME_RE.search(uname)):
        verdict.score += 0.6
        verdict.signals.append("ism/usernameda shubhali so'z")

    if uname and _TRAILING_DIGITS_RE.search(uname):
        verdict.score += 0.2
        verdict.signals.append("usernameda ketma-ket raqamlar")

    verdict.score = round(min(verdict.score, 1.0), 2)
    return verdict
