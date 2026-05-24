"""Asosiy moderatsiya: har bir guruh xabarini tekshirish va qaror qabul qilish."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.data import messages as msg
from bot.database import crud
from bot.filters.is_admin import is_user_admin
from bot.services import moderator
from bot.services.account_heuristics import analyze_account
from bot.services.bait_detector import analyze as analyze_bait
from bot.services.link_detector import matches_patterns, scan_message
from bot.services.nsfw_detector import get_detector
from bot.services.optional_features import scan_media, scan_profile_photo
from bot.services.settings_cache import get_cached_settings
from bot.utils.helpers import user_mention
from bot.utils.logger import logger

router = Router(name="moderation")

# Global qora ro'yxat domenlari fayldan bir marta yuklanadi
from pathlib import Path

_BL_FILE = Path(__file__).resolve().parent.parent / "data" / "blacklist_domains.txt"


def _load_global_blacklist() -> list[str]:
    if not _BL_FILE.exists():
        return []
    out: list[str] = []
    for raw in _BL_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lower()
        if line and not line.startswith("#"):
            out.append(line)
    return out


_GLOBAL_BLACKLIST = _load_global_blacklist()


_GROUP_FILTERS = (
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.from_user.is_not(None),
)


@router.message(*_GROUP_FILTERS)
async def moderate(message: Message, session: AsyncSession) -> None:
    """Catch-all: guruhdagi har bir xabarni moderatsiya qiladi."""
    if message.bot is None or message.from_user is None:
        return
    # Anonim adminlar (guruh nomidan) va kanal postlari — tegmaymiz
    if message.sender_chat is not None:
        return

    chat_id = message.chat.id
    user = message.from_user

    # Adminlarga tegmaymiz
    if await is_user_admin(message.bot, chat_id, user.id):
        return

    settings = get_settings()
    gs = await get_cached_settings(session, chat_id)
    log_channel = gs.get("log_channel_id")

    # DB yozuvlarini ta'minlash
    await crud.get_or_create_group(session, chat_id, message.chat.title or "")
    await crud.get_or_create_user(
        session, user.id, user.username, user.full_name, user.is_bot
    )
    await crud.get_or_create_member(session, chat_id, user.id)

    body = " ".join(filter(None, [message.text, message.caption]))

    # ---------- 1) LINK FILTRI ----------
    if gs.get("link_filter_on", True):
        scan = scan_message(message)
        if scan.has_any:
            wl = [w.pattern for w in await crud.list_whitelist(session, chat_id)]
            bl = [b.pattern for b in await crud.list_blacklist(session, chat_id)]
            bl_all = bl + _GLOBAL_BLACKLIST

            bl_hit = matches_patterns(scan, bl_all)
            if bl_hit:
                await _punish(
                    message, session, settings, gs,
                    reason=f"qora ro'yxat: {bl_hit}",
                    notice=msg.LINK_DELETED, delete=True, severity=3,
                    log_channel=log_channel,
                )
                return
            # Whitelistda bo'lmagan har qanday havola — o'chiriladi
            wl_hit = matches_patterns(scan, wl) if wl else None
            if wl_hit is None:
                await _punish(
                    message, session, settings, gs,
                    reason="ruxsatsiz havola",
                    notice=msg.LINK_DELETED, delete=True, severity=2,
                    log_channel=log_channel,
                )
                return

    # ---------- 2) 18+ FILTRI ----------
    if gs.get("nsfw_filter_on", True):
        detector = get_detector()
        verdict = detector.check_text(body)
        # Yuboruvchi username'i
        uname_v = detector.check_username(user.username)
        if uname_v.severity > verdict.severity:
            verdict = uname_v
        # Forward manbasi
        if message.forward_from_chat is not None:
            fwd = detector.check_forward(
                message.forward_from_chat.title,
                message.forward_from_chat.username,
            )
            if fwd.severity > verdict.severity:
                verdict = fwd

        if verdict.is_flagged:
            if verdict.severity == 1:
                # Shubhali — faqat log
                await moderator.log_action(
                    message.bot, session, group_id=chat_id, action="warn",
                    user_id=user.id, user_name=user.full_name,
                    reason=f"18+ shubha: {', '.join(verdict.matches[:3])}",
                    message_text=body, log_channel_id=log_channel,
                )
                return
            await _punish(
                message, session, settings, gs,
                reason=f"18+ kontent: {', '.join(verdict.matches[:3])}",
                notice=msg.NSFW_DELETED, delete=True,
                severity=verdict.severity, log_channel=log_channel,
            )
            return

    # ---------- 2.5) BAIT / HONEYPOT SPAM-BOT FILTRI ----------
    # Kanal izohlariga "Foto profilimda, halol fikring kerak 💞" kabi xabar
    # tashlab, odamlarni profil/shaxsiyga jalb qiladigan soxta akkauntlar.
    if gs.get("bait_filter_on", True) and body:
        bait = analyze_bait(body)
        if bait.is_flagged:
            severity = bait.severity
            reasons = list(bait.matches[:3])

            # Chegaradagi (sev=1) holatni kuchaytiruvchi qo'shimcha signallar:
            # 1) Shubhali akkaunt (ismda emoji, username yo'q, ochiq so'z)
            if severity < 3:
                acct = analyze_account(user.full_name, user.username)
                if acct.is_suspicious:
                    severity = 3
                    reasons += [f"akkaunt: {s}" for s in acct.signals[:2]]
            # 2) Profil rasmi NSFW (opsional, og'ir — faqat yoqilgan bo'lsa)
            if severity < 3:
                pv = await scan_profile_photo(message.bot, user.id, gs)
                if pv is not None and pv.is_flagged:
                    severity = 3
                    reasons.append("profil rasmi 18+")

            if severity >= 3:
                await _punish(
                    message, session, settings, gs,
                    reason=f"spam-bot (bait): {', '.join(reasons)}",
                    notice=msg.BAIT_DELETED, delete=True, severity=3,
                    log_channel=log_channel,
                )
                return
            # Hali ham chegaradagi shubha — faqat log, ban qilinmaydi
            await moderator.log_action(
                message.bot, session, group_id=chat_id, action="warn",
                user_id=user.id, user_name=user.full_name,
                reason=f"bait shubhasi (skor={bait.score:.2f}): {', '.join(reasons)}",
                message_text=body, log_channel_id=log_channel,
            )
            return

    # ---------- 3) SPAM FILTRI (Faza 7, beta — faqat log) ----------
    if gs.get("spam_filter_on") and body:
        from bot.services.spam_classifier import classify

        score = classify(body)
        if score >= 0.8:
            await moderator.log_action(
                message.bot, session, group_id=chat_id, action="warn",
                user_id=user.id, user_name=user.full_name,
                reason=f"spam shubhasi (skor={score:.2f})",
                message_text=body, log_channel_id=log_channel,
            )
            # Konservativ: yuqori skorda o'chiramiz, lekin ban qilmaymiz
            if score >= 0.9:
                await _punish(
                    message, session, settings, gs,
                    reason=f"spam (skor={score:.2f})",
                    notice=msg.LINK_DELETED, delete=True, severity=2,
                    log_channel=log_channel,
                )
            return

    # ---------- 4) RASM NSFW / OCR (Faza 7, opsional) ----------
    if gs.get("image_nsfw_on") or gs.get("ocr_on"):
        media = await scan_media(message, gs)
        if media is not None and media.is_flagged:
            await _punish(
                message, session, settings, gs,
                reason=media.reason,
                notice=msg.NSFW_DELETED, delete=True,
                severity=media.severity, log_channel=log_channel,
            )
            return


async def _punish(
    message: Message,
    session: AsyncSession,
    settings,
    gs: dict,
    *,
    reason: str,
    notice: str,
    delete: bool,
    severity: int,
    log_channel: int | None,
) -> None:
    """Buzilishga javob: o'chirish + ogohlantirish/ban + log."""
    bot = message.bot
    user = message.from_user
    assert bot is not None and user is not None
    chat_id = message.chat.id
    body = " ".join(filter(None, [message.text, message.caption]))

    if delete:
        await moderator.delete_message(bot, chat_id, message.message_id)

    action = "delete"
    # Severity 3 => darhol ban
    if severity >= 3:
        if await moderator.ban_user(bot, chat_id, user.id):
            await crud.set_banned(session, chat_id, user.id, True)
            action = "ban"
            try:
                await bot.send_message(
                    chat_id,
                    msg.BANNED.format(user=user_mention(user), reason=reason),
                )
            except Exception:  # noqa: BLE001
                pass
    else:
        warnings = await crud.add_warning(session, chat_id, user.id)
        max_w = settings.max_warnings
        if warnings >= max_w:
            if await moderator.ban_user(bot, chat_id, user.id):
                await crud.set_banned(session, chat_id, user.id, True)
                await crud.reset_warnings(session, chat_id, user.id)
                action = "ban"
                try:
                    await bot.send_message(
                        chat_id,
                        msg.BANNED.format(
                            user=user_mention(user),
                            reason=f"{reason} ({max_w} ogohlantirish)",
                        ),
                    )
                except Exception:  # noqa: BLE001
                    pass
        else:
            try:
                await bot.send_message(
                    chat_id,
                    notice.format(
                        user=user_mention(user), warnings=warnings, max=max_w
                    ),
                )
            except Exception:  # noqa: BLE001
                pass

    await moderator.log_action(
        bot, session, group_id=chat_id, action=action,
        user_id=user.id, user_name=user.full_name,
        reason=reason, message_text=body, log_channel_id=log_channel,
    )
    logger.info(f"[{chat_id}] {action} · user={user.id} · {reason}")


# Tahrirlangan xabarlarni ham bir xil moderatsiyadan o'tkazamiz
# (toza xabar yuborib, keyin edit orqali havola qo'shishning oldini oladi).
router.edited_message.register(moderate, *_GROUP_FILTERS)
