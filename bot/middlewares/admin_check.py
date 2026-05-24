"""Admin router uchun: faqat guruh adminlari buyruqni bajara olishini ta'minlaydi."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message

from bot.data import messages as msg
from bot.filters.is_admin import is_user_admin


class AdminCheckMiddleware(BaseMiddleware):
    """Admin komandalar router'iga ulanadi."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        if event.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await event.answer(msg.ONLY_IN_GROUP)
            return None

        # Anonim admin (guruh nomidan)
        is_anon = bool(event.sender_chat and event.sender_chat.id == event.chat.id)
        is_admin = is_anon or (
            event.from_user is not None
            and event.bot is not None
            and await is_user_admin(event.bot, event.chat.id, event.from_user.id)
        )
        if not is_admin:
            await event.answer(msg.NOT_ADMIN)
            return None

        data["is_admin"] = True
        return await handler(event, data)
