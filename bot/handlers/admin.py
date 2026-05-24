"""Admin buyruqlari: /settings, /whitelist, /blacklist, /warn, /mute, /ban, ..."""

from __future__ import annotations

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data import messages as msg
from bot.database import crud
from bot.filters.is_admin import is_user_admin
from bot.handlers.keyboards import SETTINGS_TITLE, build_settings_keyboard
from bot.middlewares.admin_check import AdminCheckMiddleware
from bot.services import moderator, stats
from bot.services.link_detector import extract_links
from bot.services.settings_cache import invalidate
from bot.utils.helpers import (
    human_duration,
    mention_by_id,
    parse_duration,
    until_from_seconds,
    user_mention,
)

router = Router(name="admin")
# Barcha admin buyruqlari faqat adminlar uchun (markazlashgan tekshiruv)
router.message.middleware(AdminCheckMiddleware())


# ----------------------------- /settings -----------------------------


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    gs = await crud.get_group_settings(session, message.chat.id)
    await message.answer(
        SETTINGS_TITLE.format(log_channel=gs.get("log_channel_id") or "ulanmagan"),
        reply_markup=build_settings_keyboard(gs),
    )


@router.message(Command("setlog"))
async def cmd_setlog(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    """Log kanal ID'sini o'rnatadi. Argument: channel_id (manfiy son)."""
    arg = (command.args or "").strip()
    if not arg:
        await crud.update_group_settings(session, message.chat.id, log_channel_id=None)
        invalidate(message.chat.id)
        await message.answer("📋 Log kanal uzildi. Ulash uchun: <code>/setlog -100...</code>")
        return
    try:
        channel_id = int(arg)
    except ValueError:
        await message.answer("❌ Noto'g'ri ID. Masalan: <code>/setlog -1001234567890</code>")
        return
    await crud.update_group_settings(session, message.chat.id, log_channel_id=channel_id)
    invalidate(message.chat.id)
    await message.answer(f"✅ Log kanal o'rnatildi: <code>{channel_id}</code>")


# --------------------------- /whitelist ---------------------------


@router.message(Command("whitelist"))
async def cmd_whitelist(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    await _handle_list_command(message, command, session, is_whitelist=True)


@router.message(Command("blacklist"))
async def cmd_blacklist(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    await _handle_list_command(message, command, session, is_whitelist=False)


async def _handle_list_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    *,
    is_whitelist: bool,
) -> None:
    cmd_name = "whitelist" if is_whitelist else "blacklist"
    args = (command.args or "").split(maxsplit=1)
    action = args[0].lower() if args else ""
    pattern = args[1].strip() if len(args) > 1 else ""
    group_id = message.chat.id
    by = message.from_user.id if message.from_user else 0

    if action == "list":
        items = (
            await crud.list_whitelist(session, group_id)
            if is_whitelist
            else await crud.list_blacklist(session, group_id)
        )
        if not items:
            await message.answer(msg.WL_EMPTY if is_whitelist else msg.BL_EMPTY)
            return
        header = msg.WL_LIST_HEADER if is_whitelist else msg.BL_LIST_HEADER
        lines = [header]
        for it in items:
            extra = f" — <i>{it.reason}</i>" if not is_whitelist and it.reason else ""
            lines.append(f"• <code>{it.pattern}</code> ({it.type}){extra}")
        await message.answer("\n".join(lines), disable_web_page_preview=True)
        return

    if action in ("add", "remove") and pattern:
        # Pattern turini aniqlash
        ptype = "username" if pattern.lstrip().startswith("@") else "domain"
        if pattern.startswith("re:"):
            ptype = "regex"
        else:
            # domen ko'rinishini normallashtirish
            scan = extract_links(pattern)
            if scan.domains:
                pattern = next(iter(scan.domains))
            elif scan.usernames:
                pattern = next(iter(scan.usernames))
                ptype = "username"

        if action == "add":
            if is_whitelist:
                ok = await crud.add_whitelist(session, group_id, pattern, by, ptype)
                await message.answer(
                    (msg.WL_ADDED if ok else msg.WL_EXISTS).format(pattern=pattern)
                )
            else:
                ok = await crud.add_blacklist(session, group_id, pattern, by, ptype)
                await message.answer(
                    (msg.BL_ADDED if ok else msg.BL_EXISTS).format(pattern=pattern)
                )
        else:  # remove
            if is_whitelist:
                ok = await crud.remove_whitelist(session, group_id, pattern)
                await message.answer(
                    (msg.WL_REMOVED if ok else msg.WL_NOT_FOUND).format(pattern=pattern)
                )
            else:
                ok = await crud.remove_blacklist(session, group_id, pattern)
                await message.answer(
                    (msg.BL_REMOVED if ok else msg.BL_NOT_FOUND).format(pattern=pattern)
                )
        return

    await message.answer(msg.LIST_USAGE.format(cmd=cmd_name))


# --------------------- /warn /mute /unmute /ban ---------------------


async def _target_from_reply(message: Message) -> tuple[int, str] | None:
    """Reply qilingan xabardan (user_id, name) ni oladi. Yo'q bo'lsa None."""
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.full_name
    return None


async def _guard_target(message: Message, target_id: int) -> bool:
    """Nishon admin bo'lsa — to'xtatadi va False qaytaradi."""
    if message.bot and await is_user_admin(message.bot, message.chat.id, target_id):
        await message.answer(msg.CANT_TOUCH_ADMIN)
        return False
    return True


@router.message(Command("warn"))
async def cmd_warn(message: Message, session: AsyncSession) -> None:
    target = await _target_from_reply(message)
    if target is None:
        await message.answer(msg.REPLY_REQUIRED)
        return
    target_id, name = target
    if not await _guard_target(message, target_id):
        return
    gs = await crud.get_group_settings(session, message.chat.id)
    from bot.config import get_settings

    max_w = get_settings().max_warnings
    warnings = await crud.add_warning(session, message.chat.id, target_id)
    action = "warn"
    if warnings >= max_w:
        if await moderator.ban_user(message.bot, message.chat.id, target_id):
            await crud.set_banned(session, message.chat.id, target_id, True)
            await crud.reset_warnings(session, message.chat.id, target_id)
            await message.answer(
                msg.BANNED.format(
                    user=mention_by_id(target_id, name),
                    reason=f"{max_w} ogohlantirish",
                )
            )
            action = "ban"
    else:
        await message.answer(
            msg.WARNED.format(user=mention_by_id(target_id, name), warnings=warnings, max=max_w)
        )
        action = "warn"
    await moderator.log_action(
        message.bot, session, group_id=message.chat.id, action=action,
        user_id=target_id, user_name=name, reason="qo'lda (admin)",
        log_channel_id=gs.get("log_channel_id"),
    )


@router.message(Command("mute"))
async def cmd_mute(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    target = await _target_from_reply(message)
    if target is None:
        await message.answer(msg.REPLY_REQUIRED)
        return
    target_id, name = target
    if not await _guard_target(message, target_id):
        return
    seconds = parse_duration(command.args)
    until = until_from_seconds(seconds)
    if await moderator.mute_user(message.bot, message.chat.id, target_id, until):
        await crud.set_muted(session, message.chat.id, target_id, until)
        gs = await crud.get_group_settings(session, message.chat.id)
        await message.answer(
            msg.MUTED.format(
                user=mention_by_id(target_id, name),
                duration=human_duration(seconds),
                reason="admin buyrug'i",
            )
        )
        await moderator.log_action(
            message.bot, session, group_id=message.chat.id, action="mute",
            user_id=target_id, user_name=name, reason="qo'lda (admin)",
            log_channel_id=gs.get("log_channel_id"),
        )


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, session: AsyncSession) -> None:
    target = await _target_from_reply(message)
    if target is None:
        await message.answer(msg.REPLY_REQUIRED)
        return
    target_id, name = target
    if await moderator.unmute_user(message.bot, message.chat.id, target_id):
        await crud.set_muted(session, message.chat.id, target_id, None)
        await message.answer(msg.UNMUTED.format(user=mention_by_id(target_id, name)))


@router.message(Command("ban"))
async def cmd_ban(message: Message, session: AsyncSession) -> None:
    target = await _target_from_reply(message)
    if target is None:
        await message.answer(msg.REPLY_REQUIRED)
        return
    target_id, name = target
    if not await _guard_target(message, target_id):
        return
    if await moderator.ban_user(message.bot, message.chat.id, target_id):
        await crud.set_banned(session, message.chat.id, target_id, True)
        gs = await crud.get_group_settings(session, message.chat.id)
        await message.answer(
            msg.BANNED.format(user=mention_by_id(target_id, name), reason="admin buyrug'i")
        )
        await moderator.log_action(
            message.bot, session, group_id=message.chat.id, action="ban",
            user_id=target_id, user_name=name, reason="qo'lda (admin)",
            log_channel_id=gs.get("log_channel_id"),
        )


@router.message(Command("unban"))
async def cmd_unban(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    # Reply orqali yoki ID argument orqali
    target_id: int | None = None
    name = ""
    target = await _target_from_reply(message)
    if target:
        target_id, name = target
    elif command.args and command.args.strip().lstrip("-").isdigit():
        target_id = int(command.args.strip())
    if target_id is None:
        await message.answer("Foydalanish: javob qaytaring yoki <code>/unban &lt;user_id&gt;</code>")
        return
    if await moderator.unban_user(message.bot, message.chat.id, target_id):
        await crud.set_banned(session, message.chat.id, target_id, False)
        gs = await crud.get_group_settings(session, message.chat.id)
        await message.answer(msg.UNBANNED)
        await moderator.log_action(
            message.bot, session, group_id=message.chat.id, action="unban",
            user_id=target_id, user_name=name, reason="qo'lda (admin)",
            log_channel_id=gs.get("log_channel_id"),
        )


# --------------------------- /stats /logs ---------------------------


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    text = await stats.group_stats_text(session, message.chat.id, message.chat.title or "")
    await message.answer(text)


@router.message(Command("logs"))
async def cmd_logs(message: Message, session: AsyncSession) -> None:
    text = await stats.logs_text(session, message.chat.id, limit=10)
    await message.answer(text, disable_web_page_preview=True)
