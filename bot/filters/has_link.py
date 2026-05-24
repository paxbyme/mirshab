"""Routing filtri: xabarda biror havola bormi?"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.services.link_detector import scan_message


class HasLink(BaseFilter):
    """Xabarda URL / @username / t.me havolasi bo'lsa True.

    Topilgan natijani handler'ga `link_scan` argumenti sifatida uzatadi.
    """

    async def __call__(self, message: Message) -> bool | dict:
        scan = scan_message(message)
        if scan.has_any:
            return {"link_scan": scan}
        return False
