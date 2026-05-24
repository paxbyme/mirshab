"""Moderatsiya harakatlari: o'chirish, ogohlantirish, mute, ban, kick + loglash."""

from __future__ import annotations

from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatPermissions
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data import messages as msg
from bot.database import crud
from bot.utils.helpers import mention_by_id, now_utc
from bot.utils.logger import logger

# Mute paytida hamma narsa taqiqlanadi
_MUTED_PERMS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)
# Mute olib tashlanganda — normal huquqlar
_UNMUTED_PERMS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


async def delete_message(bot: Bot, chat_id: int, message_id: int) -> bool:
    """Xabarni o'chiradi. Muvaffaqiyat/yo'qligini qaytaradi."""
    try:
        await bot.delete_message(chat_id, message_id)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Xabarni o'chirib bo'lmadi ({chat_id}/{message_id}): {e}")
        return False


async def mute_user(
    bot: Bot, chat_id: int, user_id: int, until: datetime | None
) -> bool:
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=_MUTED_PERMS,
            until_date=until,
        )
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Mute muvaffaqiyatsiz ({chat_id}/{user_id}): {e}")
        return False


async def unmute_user(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id, user_id=user_id, permissions=_UNMUTED_PERMS
        )
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Unmute muvaffaqiyatsiz ({chat_id}/{user_id}): {e}")
        return False


async def ban_user(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Ban muvaffaqiyatsiz ({chat_id}/{user_id}): {e}")
        return False


async def unban_user(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        await bot.unban_chat_member(
            chat_id=chat_id, user_id=user_id, only_if_banned=True
        )
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Unban muvaffaqiyatsiz ({chat_id}/{user_id}): {e}")
        return False


async def kick_user(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Ban + darhol unban = guruhdan chiqarish (qayta kira oladi)."""
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Kick muvaffaqiyatsiz ({chat_id}/{user_id}): {e}")
        return False


async def log_action(
    bot: Bot,
    session: AsyncSession,
    group_id: int,
    action: str,
    *,
    user_id: int | None = None,
    user_name: str | None = None,
    reason: str = "",
    message_text: str = "",
    log_channel_id: int | None = None,
) -> None:
    """DB'ga yozadi va (sozlangan bo'lsa) log kanalga yuboradi."""
    await crud.add_log(
        session,
        group_id=group_id,
        action=action,
        user_id=user_id,
        reason=reason,
        message_text=message_text,
    )

    if not log_channel_id:
        return
    try:
        text = msg.LOG_ENTRY.format(
            action_emoji=msg.ACTION_EMOJI.get(action, "•"),
            action=action.upper(),
            user=mention_by_id(user_id, user_name) if user_id else "—",
            reason=reason or "—",
            text=(message_text or "—")[:200],
            time=now_utc().strftime("%Y-%m-%d %H:%M"),
        )
        await bot.send_message(log_channel_id, text, disable_web_page_preview=True)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Log kanalga yuborib bo'lmadi ({log_channel_id}): {e}")
