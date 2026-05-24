"""Yangi a'zo / bot qo'shilganda: avto-ban, CAPTCHA, welcome."""

from __future__ import annotations

import time

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated, Message, User
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.data import messages as msg
from bot.database import crud
from bot.database import engine as db_engine
from bot.filters.is_admin import is_user_admin
from bot.services import moderator
from bot.services.captcha import captcha_manager
from bot.services.optional_features import scan_profile_photo
from bot.services.settings_cache import get_cached_settings
from bot.utils.helpers import until_from_seconds, user_mention
from bot.utils.logger import logger

router = Router(name="new_member")

# Yaqinda qayta ishlangan qo'shilishlar — bir a'zo uchun new_chat_members xabari
# va chat_member update'i deyarli bir vaqtda kelishi mumkin; dublikat CAPTCHA'ni
# oldini olamiz. TTL qisqa: faqat shu ikki signal ustma-ust kelishini qoplaydi.
_recent_joins: dict[tuple[int, int], float] = {}
_JOIN_DEDUP_TTL = 15.0


def _recently_handled(chat_id: int, user_id: int) -> bool:
    """(chat_id, user_id) oxirgi TTL ichida ishlangan bo'lsa True; aks holda belgilab False."""
    now = time.monotonic()
    for key, ts in list(_recent_joins.items()):
        if now - ts > _JOIN_DEDUP_TTL:
            _recent_joins.pop(key, None)
    key = (chat_id, user_id)
    if key in _recent_joins:
        return True
    _recent_joins[key] = now
    return False


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.new_chat_members,
)
async def on_new_members(message: Message, session: AsyncSession) -> None:
    """Kimdir a'zo(lar)ni qo'shganda keladigan service xabari."""
    bot = message.bot
    assert bot is not None
    me = await bot.me()
    chat_id = message.chat.id

    await crud.get_or_create_group(session, chat_id, message.chat.title or "")
    gs = await get_cached_settings(session, chat_id)
    settings = get_settings()

    if gs.get("delete_service_messages"):
        await moderator.delete_message(bot, chat_id, message.message_id)

    adder = message.from_user
    adder_is_admin = bool(adder and await is_user_admin(bot, chat_id, adder.id))

    for new_user in message.new_chat_members:
        if new_user.id == me.id:
            # Botning o'zi qo'shildi
            await bot.send_message(chat_id, msg.START_GROUP)
            continue
        await _process_member(
            bot, session, chat_id, new_user,
            adder_is_admin=adder_is_admin, gs=gs, settings=settings,
        )


@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def on_member_join(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """Foydalanuvchi o'zi qo'shilganda (invite link / "Join").

    Katta yoki ommaviy superguruhlarda Telegram new_chat_members service xabarini
    yubormaydi — qo'shilish faqat chat_member update sifatida keladi. Buni olish
    uchun bot guruhda ADMIN bo'lishi shart.
    """
    bot = event.bot
    assert bot is not None
    me = await bot.me()
    chat_id = event.chat.id
    new_user = event.new_chat_member.user

    if new_user.id == me.id:
        return  # botning o'zi — my_chat_member orqali keladi, bu yerda emas

    logger.info(f"[{chat_id}] Yangi a'zo (chat_member) · user={new_user.id}")
    await crud.get_or_create_group(session, chat_id, event.chat.title or "")
    gs = await get_cached_settings(session, chat_id)
    settings = get_settings()

    adder = event.from_user
    adder_is_admin = bool(
        adder
        and adder.id != new_user.id  # o'zi qo'shilgan bo'lsa "adder admin" emas
        and await is_user_admin(bot, chat_id, adder.id)
    )

    await _process_member(
        bot, session, chat_id, new_user,
        adder_is_admin=adder_is_admin, gs=gs, settings=settings,
    )


async def _process_member(
    bot: Bot,
    session: AsyncSession,
    chat_id: int,
    new_user: User,
    *,
    adder_is_admin: bool,
    gs: dict,
    settings,
) -> None:
    """Bitta yangi a'zoni qayta ishlaydi: bot-ban yoki CAPTCHA/welcome.

    new_chat_members va chat_member ikkalasi ham ishga tushishi mumkin — dedup
    orqali bir a'zo ikki marta tekshirilmaydi.
    """
    if _recently_handled(chat_id, new_user.id):
        return

    await crud.get_or_create_user(
        session, new_user.id, new_user.username,
        new_user.full_name, new_user.is_bot,
    )

    # --- Bot bo'lsa: admin qo'shmagan bo'lsa darhol ban ---
    if new_user.is_bot:
        if adder_is_admin:
            logger.info(f"[{chat_id}] Admin botni qo'shdi: @{new_user.username}")
            return
        if await moderator.ban_user(bot, chat_id, new_user.id):
            await crud.set_banned(session, chat_id, new_user.id, True)
            await bot.send_message(
                chat_id, msg.BOT_KICKED.format(name=new_user.full_name)
            )
            await moderator.log_action(
                bot, session, group_id=chat_id, action="ban",
                user_id=new_user.id, user_name=new_user.full_name,
                reason="ruxsatsiz qo'shilgan bot",
                log_channel_id=gs.get("log_channel_id"),
            )
        return

    # --- Oddiy foydalanuvchi ---
    # Profil rasmi NSFW (opsional, og'ir) — bait/spam akkauntlarni kirishida ushlaydi
    pfp = await scan_profile_photo(bot, new_user.id, gs)
    if pfp is not None and pfp.is_flagged:
        if await moderator.ban_user(bot, chat_id, new_user.id):
            await crud.set_banned(session, chat_id, new_user.id, True)
            try:
                await bot.send_message(
                    chat_id,
                    msg.BANNED.format(
                        user=user_mention(new_user), reason="profil rasmi 18+"
                    ),
                )
            except Exception:  # noqa: BLE001
                pass
            await moderator.log_action(
                bot, session, group_id=chat_id, action="ban",
                user_id=new_user.id, user_name=new_user.full_name,
                reason="profil rasmi 18+ (yangi a'zo)",
                log_channel_id=gs.get("log_channel_id"),
            )
        return

    if gs.get("captcha_on", True):
        await _start_captcha(bot, chat_id, new_user, settings.captcha_timeout_seconds, gs)
    elif gs.get("welcome_on", True):
        await _send_welcome(bot, chat_id, new_user, gs)


async def _send_welcome(bot: Bot, chat_id: int, user: User, gs: dict) -> None:
    text = (gs.get("welcome_text") or "").strip() or msg.WELCOME_DEFAULT
    try:
        await bot.send_message(chat_id, text.format(user=user_mention(user)))
    except Exception:  # noqa: BLE001
        pass


async def _start_captcha(
    bot: Bot, chat_id: int, user: User, timeout: int, gs: dict
) -> None:
    """Foydalanuvchini vaqtincha mute qilib, CAPTCHA yuboradi."""
    # CAPTCHA paytida yozolmasin
    await moderator.mute_user(bot, chat_id, user.id, until=until_from_seconds(timeout + 30))

    question, answer, kb = captcha_manager.build_challenge(user.id)

    async def on_timeout() -> None:
        """Vaqt tugaganda: kick + tozalash."""
        entry = captcha_manager.cancel(chat_id, user.id)
        await moderator.kick_user(bot, chat_id, user.id)
        if entry and entry.message_id:
            await moderator.delete_message(bot, chat_id, entry.message_id)
        try:
            await bot.send_message(
                chat_id, msg.CAPTCHA_FAIL_KICK.format(user=user_mention(user))
            )
        except Exception:  # noqa: BLE001
            pass
        # Yangi sessiya — handler sessiyasi allaqachon yopilgan
        if db_engine.session_factory is not None:
            async with db_engine.session_factory() as s:
                await moderator.log_action(
                    bot, s, group_id=chat_id, action="kick",
                    user_id=user.id, user_name=user.full_name,
                    reason="CAPTCHA o'tilmadi",
                    log_channel_id=gs.get("log_channel_id"),
                )
                await s.commit()

    captcha_manager.register(chat_id, user.id, answer, question, timeout, on_timeout)

    try:
        sent = await bot.send_message(
            chat_id,
            f"{msg.CAPTCHA_PROMPT.format(user=user_mention(user), timeout=timeout)}\n\n"
            f"❓ <b>{question}</b>",
            reply_markup=kb,
        )
        captcha_manager.set_message_id(chat_id, user.id, sent.message_id)
        logger.info(f"[{chat_id}] CAPTCHA yuborildi · user={user.id}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"CAPTCHA yuborilmadi: {e}")
        captcha_manager.cancel(chat_id, user.id)
