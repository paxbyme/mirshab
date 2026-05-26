"""Inline tugma callback'lari: CAPTCHA javoblari va sozlama toggle'lari."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data import messages as msg
from bot.database import crud
from bot.filters.is_admin import is_user_admin
from bot.handlers.keyboards import (
    SETTINGS_PREFIX,
    SETTINGS_TITLE,
    build_settings_keyboard,
)
from bot.services import moderator
from bot.services.captcha import CALLBACK_PREFIX as CAPT_PREFIX
from bot.services.captcha import captcha_manager
from bot.services.settings_cache import get_cached_settings, invalidate
from bot.utils.helpers import user_mention

router = Router(name="callbacks")


# ----------------------------- CAPTCHA -----------------------------


@router.callback_query(F.data.startswith(f"{CAPT_PREFIX}:"))
async def on_captcha_answer(query: CallbackQuery, session: AsyncSession) -> None:
    parts = (query.data or "").split(":")
    if len(parts) != 3:
        await query.answer()
        return
    _, target_id_s, chosen_s = parts
    try:
        target_id, chosen = int(target_id_s), int(chosen_s)
    except ValueError:
        await query.answer()
        return

    # Faqat o'sha foydalanuvchi javob bera oladi
    if query.from_user.id != target_id:
        await query.answer(msg.CAPTCHA_WRONG_USER, show_alert=False)
        return

    chat_id = query.message.chat.id if query.message else None
    if chat_id is None:
        await query.answer()
        return

    result = captcha_manager.check(chat_id, target_id, chosen)
    bot = query.bot
    if result == "ok":
        await moderator.unmute_user(bot, chat_id, target_id)
        if query.message:
            await moderator.delete_message(bot, chat_id, query.message.message_id)
        await query.answer("✅")
        # Tasdiqdan o'tgach — endi mention qilib, guruh qoidalari bilan tanishtiramiz
        gs = await get_cached_settings(session, chat_id)
        rules = (gs.get("welcome_text") or "").strip() or msg.WELCOME_DEFAULT
        try:
            await bot.send_message(
                chat_id,
                f"{msg.CAPTCHA_OK}\n\n"
                f"{rules.format(user=user_mention(query.from_user))}",
            )
        except Exception:  # noqa: BLE001
            pass
    elif result == "wrong":
        await query.answer("❌ Noto'g'ri. Qayta urinib ko'ring.", show_alert=False)
    else:
        await query.answer()


# ----------------------------- Sozlamalar -----------------------------


@router.callback_query(F.data.startswith(f"{SETTINGS_PREFIX}:"))
async def on_settings_toggle(query: CallbackQuery, session: AsyncSession) -> None:
    if query.message is None or query.bot is None:
        await query.answer()
        return
    chat_id = query.message.chat.id

    # Faqat adminlar
    if not await is_user_admin(query.bot, chat_id, query.from_user.id):
        await query.answer(msg.NOT_ADMIN, show_alert=True)
        return

    key = (query.data or "").split(":", 1)[1]
    if key == "close":
        await query.message.delete()
        await query.answer()
        return

    current = await crud.get_group_settings(session, chat_id)
    if key not in current:
        await query.answer()
        return

    new_value = not bool(current.get(key))
    updated = await crud.update_group_settings(session, chat_id, **{key: new_value})
    invalidate(chat_id)

    await query.message.edit_text(
        SETTINGS_TITLE.format(log_channel=updated.get("log_channel_id") or "ulanmagan"),
        reply_markup=build_settings_keyboard(updated),
    )
    await query.answer("✅ Saqlandi" if new_value else "❌ O'chirildi")
