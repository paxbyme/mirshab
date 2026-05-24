"""APScheduler vazifalari: mute muddatini tekshirish va kunlik hisobot."""

from __future__ import annotations

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from bot.data import messages as msg
from bot.database import crud
from bot.services import moderator
from bot.utils.helpers import normalize_channel_id, now_utc
from bot.utils.logger import logger


async def _check_expired_mutes(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Mute muddati tugagan a'zolarni ozod qiladi."""
    async with session_factory() as session:
        expired = await crud.get_expired_mutes(session)
        for member in expired:
            await moderator.unmute_user(bot, member.group_id, member.user_id)
            await crud.set_muted(session, member.group_id, member.user_id, None)
            logger.info(f"Mute tugadi: {member.group_id}/{member.user_id}")
        await session.commit()


async def _daily_report(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Har bir guruh uchun log kanalga kunlik hisobot yuboradi."""
    async with session_factory() as session:
        groups = await crud.all_groups(session)
        for group in groups:
            settings = {**(group.settings or {})}
            log_channel = normalize_channel_id(settings.get("log_channel_id"))
            if not log_channel:
                continue
            daily = await crud.daily_stats(session, group.id)
            members = await crud.total_members(session, group.id)
            text = msg.DAILY_REPORT.format(
                title=group.title or "Guruh",
                date=now_utc().strftime("%Y-%m-%d"),
                delete=daily.get("delete", 0),
                warn=daily.get("warn", 0),
                mute=daily.get("mute", 0),
                ban=daily.get("ban", 0),
                members=members,
            )
            try:
                await bot.send_message(log_channel, text)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Kunlik hisobot yuborilmadi ({log_channel}): {e}")


def setup_scheduler(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIOScheduler:
    """Scheduler'ni sozlaydi va ishga tushiradi."""
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _check_expired_mutes,
        trigger="interval",
        minutes=1,
        args=(bot, session_factory),
        id="check_mutes",
        replace_existing=True,
    )
    scheduler.add_job(
        _daily_report,
        trigger="cron",
        hour=20,  # UTC 20:00 (Toshkent ~01:00)
        minute=0,
        args=(bot, session_factory),
        id="daily_report",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler ishga tushdi (mute-checker + kunlik hisobot)")
    return scheduler
