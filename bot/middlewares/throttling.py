"""Anti-flood middleware: tez-tez xabar yuborgan a'zoni vaqtincha mute qiladi."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.data import messages as msg
from bot.database import crud
from bot.filters.is_admin import is_user_admin
from bot.services import moderator
from bot.services.antiflood import FloodController
from bot.services.settings_cache import get_cached_settings
from bot.utils.helpers import human_duration, until_from_seconds, user_mention


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, controller: FloodController) -> None:
        super().__init__()
        self.controller = controller
        self.settings = get_settings()

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        # Faqat guruh xabarlari uchun
        if (
            not isinstance(event, Message)
            or event.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP)
            or event.from_user is None
            or event.from_user.is_bot
        ):
            return await handler(event, data)

        session: AsyncSession | None = data.get("session")
        if session is None:
            return await handler(event, data)

        group_settings = await get_cached_settings(session, event.chat.id)
        if not group_settings.get("antiflood_on", True):
            return await handler(event, data)

        chat_id, user_id = event.chat.id, event.from_user.id
        flooding = await self.controller.hit(chat_id, user_id)
        if not flooding:
            return await handler(event, data)

        # Adminlarni floodga uchratmaymiz
        if event.bot and await is_user_admin(event.bot, chat_id, user_id):
            return await handler(event, data)

        # Flood => mute
        await self.controller.reset(chat_id, user_id)
        seconds = self.settings.flood_mute_seconds
        until = until_from_seconds(seconds)
        if event.bot and await moderator.mute_user(event.bot, chat_id, user_id, until):
            await crud.set_muted(session, chat_id, user_id, until)
            await moderator.log_action(
                event.bot,
                session,
                group_id=chat_id,
                action="mute",
                user_id=user_id,
                user_name=event.from_user.full_name,
                reason="anti-flood",
                log_channel_id=group_settings.get("log_channel_id"),
            )
            try:
                await event.answer(
                    msg.FLOOD_MUTED.format(
                        user=user_mention(event.from_user),
                        duration=human_duration(seconds),
                    )
                )
            except Exception:  # noqa: BLE001
                pass
        # Xabarni handler'ga o'tkazmaymiz (flood to'xtatildi)
        return None
