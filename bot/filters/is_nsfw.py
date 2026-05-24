"""Routing filtri: xabarda 18+ / nomaqbul matn bormi?"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.services.nsfw_detector import get_detector


class IsNsfw(BaseFilter):
    """Matn/caption NSFW deb topilsa True va `nsfw_verdict` uzatiladi."""

    async def __call__(self, message: Message) -> bool | dict:
        detector = get_detector()
        text = " ".join(filter(None, [message.text, message.caption]))
        verdict = detector.check_text(text)
        if verdict.is_flagged:
            return {"nsfw_verdict": verdict}
        return False
