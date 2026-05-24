"""CRUD funksiyalar — barcha DB o'qish/yozish operatsiyalari shu yerda."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Blacklist,
    Group,
    GroupMember,
    ModerationLog,
    NsfwKeyword,
    User,
    Whitelist,
    default_group_settings,
)
from bot.utils.helpers import now_utc

# ----------------------------- Groups -----------------------------


async def get_or_create_group(
    session: AsyncSession, group_id: int, title: str = ""
) -> Group:
    group = await session.get(Group, group_id)
    if group is None:
        group = Group(id=group_id, title=title, settings=default_group_settings())
        session.add(group)
        await session.flush()
    elif title and group.title != title:
        group.title = title
    return group


async def update_group_settings(
    session: AsyncSession, group_id: int, **changes: Any
) -> dict[str, Any]:
    """Guruh sozlamalarini qisman yangilaydi va yangi dict'ni qaytaradi."""
    group = await get_or_create_group(session, group_id)
    # JSON ustunni o'rniga yangi dict berib yangilaymiz (mutatsiya kuzatilmasligi mumkin)
    new_settings = {**default_group_settings(), **(group.settings or {}), **changes}
    group.settings = new_settings
    await session.flush()
    return new_settings


async def get_group_settings(session: AsyncSession, group_id: int) -> dict[str, Any]:
    group = await get_or_create_group(session, group_id)
    return {**default_group_settings(), **(group.settings or {})}


# ----------------------------- Users -----------------------------


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: str | None = None,
    first_name: str = "",
    is_bot: bool = False,
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id, username=username, first_name=first_name, is_bot=is_bot
        )
        session.add(user)
        await session.flush()
    else:
        user.username = username
        if first_name:
            user.first_name = first_name
    return user


# -------------------------- Group members --------------------------


async def get_member(
    session: AsyncSession, group_id: int, user_id: int
) -> GroupMember | None:
    stmt = select(GroupMember).where(
        GroupMember.group_id == group_id, GroupMember.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_or_create_member(
    session: AsyncSession, group_id: int, user_id: int
) -> GroupMember:
    member = await get_member(session, group_id, user_id)
    if member is None:
        member = GroupMember(group_id=group_id, user_id=user_id)
        session.add(member)
        await session.flush()
    return member


async def add_warning(
    session: AsyncSession, group_id: int, user_id: int, amount: int = 1
) -> int:
    """Ogohlantirish qo'shadi va yangi umumiy sonni qaytaradi."""
    member = await get_or_create_member(session, group_id, user_id)
    member.warnings += amount
    await session.flush()
    return member.warnings


async def reset_warnings(session: AsyncSession, group_id: int, user_id: int) -> None:
    member = await get_or_create_member(session, group_id, user_id)
    member.warnings = 0
    await session.flush()


async def set_muted(
    session: AsyncSession,
    group_id: int,
    user_id: int,
    until: datetime | None,
) -> None:
    member = await get_or_create_member(session, group_id, user_id)
    member.muted_until = until
    await session.flush()


async def set_banned(
    session: AsyncSession, group_id: int, user_id: int, banned: bool
) -> None:
    member = await get_or_create_member(session, group_id, user_id)
    member.is_banned = banned
    if not banned:
        member.warnings = 0
    await session.flush()


async def get_expired_mutes(session: AsyncSession) -> list[GroupMember]:
    """Mute muddati o'tgan, lekin hali tozalanmagan a'zolar."""
    stmt = select(GroupMember).where(
        GroupMember.muted_until.is_not(None),
        GroupMember.muted_until <= now_utc(),
    )
    return list((await session.execute(stmt)).scalars().all())


# ----------------------------- Whitelist -----------------------------


async def add_whitelist(
    session: AsyncSession,
    group_id: int,
    pattern: str,
    added_by: int,
    type_: str = "domain",
) -> bool:
    """Qaytaradi: True — qo'shildi, False — allaqachon mavjud."""
    pattern = pattern.strip().lower()
    exists = await session.execute(
        select(Whitelist.id).where(
            Whitelist.group_id == group_id, Whitelist.pattern == pattern
        )
    )
    if exists.scalar_one_or_none() is not None:
        return False
    session.add(
        Whitelist(group_id=group_id, pattern=pattern, type=type_, added_by=added_by)
    )
    await session.flush()
    return True


async def remove_whitelist(session: AsyncSession, group_id: int, pattern: str) -> bool:
    pattern = pattern.strip().lower()
    result = await session.execute(
        delete(Whitelist).where(
            Whitelist.group_id == group_id, Whitelist.pattern == pattern
        )
    )
    await session.flush()
    return result.rowcount > 0


async def list_whitelist(session: AsyncSession, group_id: int) -> list[Whitelist]:
    stmt = select(Whitelist).where(Whitelist.group_id == group_id).order_by(Whitelist.pattern)
    return list((await session.execute(stmt)).scalars().all())


# ----------------------------- Blacklist -----------------------------


async def add_blacklist(
    session: AsyncSession,
    group_id: int,
    pattern: str,
    added_by: int,
    type_: str = "domain",
    reason: str = "",
) -> bool:
    pattern = pattern.strip().lower()
    exists = await session.execute(
        select(Blacklist.id).where(
            Blacklist.group_id == group_id, Blacklist.pattern == pattern
        )
    )
    if exists.scalar_one_or_none() is not None:
        return False
    session.add(
        Blacklist(
            group_id=group_id,
            pattern=pattern,
            type=type_,
            reason=reason,
            added_by=added_by,
        )
    )
    await session.flush()
    return True


async def remove_blacklist(session: AsyncSession, group_id: int, pattern: str) -> bool:
    pattern = pattern.strip().lower()
    result = await session.execute(
        delete(Blacklist).where(
            Blacklist.group_id == group_id, Blacklist.pattern == pattern
        )
    )
    await session.flush()
    return result.rowcount > 0


async def list_blacklist(session: AsyncSession, group_id: int) -> list[Blacklist]:
    stmt = select(Blacklist).where(Blacklist.group_id == group_id).order_by(Blacklist.pattern)
    return list((await session.execute(stmt)).scalars().all())


# -------------------------- Moderation logs --------------------------


async def add_log(
    session: AsyncSession,
    group_id: int,
    action: str,
    user_id: int | None = None,
    reason: str = "",
    message_text: str = "",
) -> ModerationLog:
    log = ModerationLog(
        group_id=group_id,
        user_id=user_id,
        action=action,
        reason=reason,
        message_text=(message_text or "")[:1000],
    )
    session.add(log)
    await session.flush()
    return log


async def recent_logs(
    session: AsyncSession, group_id: int, limit: int = 10
) -> list[ModerationLog]:
    stmt = (
        select(ModerationLog)
        .where(ModerationLog.group_id == group_id)
        .order_by(ModerationLog.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def stats_since(
    session: AsyncSession, group_id: int, since: datetime
) -> dict[str, int]:
    """`since` dan beri harakatlar bo'yicha statistika (action => count)."""
    stmt = (
        select(ModerationLog.action, func.count())
        .where(
            ModerationLog.group_id == group_id,
            ModerationLog.created_at >= since,
        )
        .group_by(ModerationLog.action)
    )
    rows = (await session.execute(stmt)).all()
    return {action: count for action, count in rows}


async def daily_stats(session: AsyncSession, group_id: int) -> dict[str, int]:
    return await stats_since(session, group_id, now_utc() - timedelta(days=1))


async def total_members(session: AsyncSession, group_id: int) -> int:
    stmt = select(func.count()).select_from(GroupMember).where(
        GroupMember.group_id == group_id
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def banned_count(session: AsyncSession, group_id: int) -> int:
    stmt = select(func.count()).select_from(GroupMember).where(
        GroupMember.group_id == group_id, GroupMember.is_banned.is_(True)
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def all_groups(session: AsyncSession) -> list[Group]:
    return list((await session.execute(select(Group))).scalars().all())


# ----------------------------- NSFW keywords -----------------------------


async def list_nsfw_keywords(session: AsyncSession) -> list[NsfwKeyword]:
    return list((await session.execute(select(NsfwKeyword))).scalars().all())


async def add_nsfw_keyword(
    session: AsyncSession, keyword: str, language: str = "uz", severity: int = 2
) -> bool:
    keyword = keyword.strip().lower()
    exists = await session.execute(
        select(NsfwKeyword.id).where(NsfwKeyword.keyword == keyword)
    )
    if exists.scalar_one_or_none() is not None:
        return False
    session.add(NsfwKeyword(keyword=keyword, language=language, severity=severity))
    await session.flush()
    return True
