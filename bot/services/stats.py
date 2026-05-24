"""Statistika hisoblash va matn shakllantirish."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.data import messages as msg
from bot.database import crud


async def group_stats_text(session: AsyncSession, group_id: int, title: str) -> str:
    """`/stats` uchun tayyor matn."""
    daily = await crud.daily_stats(session, group_id)
    members = await crud.total_members(session, group_id)
    banned = await crud.banned_count(session, group_id)
    return msg.STATS_TEMPLATE.format(
        title=title or "Guruh",
        members=members,
        banned=banned,
        delete=daily.get("delete", 0),
        warn=daily.get("warn", 0),
        mute=daily.get("mute", 0),
        ban=daily.get("ban", 0),
    )


async def logs_text(session: AsyncSession, group_id: int, limit: int = 10) -> str:
    """`/logs` uchun oxirgi harakatlar matni."""
    logs = await crud.recent_logs(session, group_id, limit=limit)
    if not logs:
        return msg.LOGS_EMPTY
    lines = [msg.LOGS_HEADER]
    for log in logs:
        emoji = msg.ACTION_EMOJI.get(log.action, "•")
        when = log.created_at.strftime("%m-%d %H:%M") if log.created_at else "—"
        uid = f"<code>{log.user_id}</code>" if log.user_id else "—"
        reason = (log.reason or "")[:60]
        lines.append(f"{emoji} <b>{log.action}</b> · {uid} · {when}\n   <i>{reason}</i>")
    return "\n".join(lines)
