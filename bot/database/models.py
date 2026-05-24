"""SQLAlchemy 2.0 modellari (jadval ta'riflari)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.engine import Base


def default_group_settings() -> dict[str, Any]:
    """Yangi guruh uchun standart sozlamalar."""
    return {
        "link_filter_on": True,
        "nsfw_filter_on": True,
        "captcha_on": True,
        "antiflood_on": True,
        "spam_filter_on": False,  # Faza 7, heuristik (false-positive ehtimoli)
        "bait_filter_on": True,   # honeypot / profil-bait spam-botlar (yuqori ishonch)
        "ai_filter_on": True,     # AI tahlili (profilga jalb) — kalit bo'lsagina ishlaydi
        "image_nsfw_on": False,   # Faza 7, og'ir
        "ocr_on": False,          # Faza 7
        "welcome_on": True,
        "welcome_text": "",      # bo'sh => default matn ishlatiladi
        "log_channel_id": None,
        "delete_service_messages": False,
    }


class Group(Base):
    """Bot qo'shilgan guruh."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # chat_id
    title: Mapped[str] = mapped_column(Text, default="")
    settings: Mapped[dict[str, Any]] = mapped_column(
        Base.JSONType, default=default_group_settings
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    members: Mapped[list["GroupMember"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class User(Base):
    """Telegram foydalanuvchisi (global)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # user_id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(Text, default="")
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)


class GroupMember(Base):
    """Guruh ichidagi foydalanuvchi holati."""

    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user"),
        Index("ix_group_members_muted", "muted_until"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    muted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    group: Mapped["Group"] = relationship(back_populates="members")


class Whitelist(Base):
    """Ruxsat berilgan link/domen/username pattern'lari."""

    __tablename__ = "whitelist"
    __table_args__ = (
        UniqueConstraint("group_id", "pattern", name="uq_whitelist_group_pattern"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    pattern: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(16), default="domain")  # domain/username/regex
    added_by: Mapped[int] = mapped_column(BigInteger)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Blacklist(Base):
    """Taqiqlangan link/domen/username pattern'lari."""

    __tablename__ = "blacklist"
    __table_args__ = (
        UniqueConstraint("group_id", "pattern", name="uq_blacklist_group_pattern"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    pattern: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(16), default="domain")
    reason: Mapped[str] = mapped_column(Text, default="")
    added_by: Mapped[int] = mapped_column(BigInteger)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ModerationLog(Base):
    """Moderatsiya harakatlari tarixi."""

    __tablename__ = "moderation_logs"
    __table_args__ = (
        Index("ix_modlog_group_created", "group_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(16))  # delete/warn/mute/ban/unban/kick
    reason: Mapped[str] = mapped_column(Text, default="")
    message_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class NsfwKeyword(Base):
    """DB'da saqlanadigan qo'shimcha 18+ kalit so'zlar (global).

    Asosiy lug'at fayldan o'qiladi; bu jadval admin qo'shgan so'zlar uchun.
    """

    __tablename__ = "nsfw_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(128), unique=True)
    language: Mapped[str] = mapped_column(String(8), default="uz")
    severity: Mapped[int] = mapped_column(Integer, default=2)  # 1-3
