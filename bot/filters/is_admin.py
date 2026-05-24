"""Admin tekshiruvi — filter va yordamchi funksiya."""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.config import get_settings

_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


async def is_user_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Foydalanuvchi guruh admini (yoki bot egasi) ekanligini tekshiradi."""
    settings = get_settings()
    if user_id in settings.owner_ids:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramBadRequest:
        return False
    return member.status in _ADMIN_STATUSES


class IsAdmin(BaseFilter):
    """Xabar yuboruvchi guruh admini bo'lsa — o'tkazadi."""

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.bot is None:
            return False
        # Anonim admin (guruh nomidan yozish)
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            return True
        return await is_user_admin(
            message.bot, message.chat.id, message.from_user.id
        )
