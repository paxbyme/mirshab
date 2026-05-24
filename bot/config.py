"""Ilova sozlamalari — `.env` faylidan o'qiladi (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe sozlamalar. `.env` yoki muhit o'zgaruvchilaridan o'qiydi."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Telegram ---
    bot_token: str = Field(..., description="@BotFather token")
    owner_ids: list[int] = Field(default_factory=list)

    # --- Ma'lumotlar bazasi ---
    db_url: str = "sqlite+aiosqlite:///qoriqchi.db"

    # --- Redis (opsional) ---
    redis_url: str = ""

    # --- Moderatsiya ---
    max_warnings: int = 3
    flood_window_seconds: int = 5
    flood_max_messages: int = 5
    flood_mute_seconds: int = 300
    captcha_timeout_seconds: int = 60

    # --- Loglash ---
    log_level: str = "INFO"

    # --- Web dashboard (Faza 7) ---
    web_enabled: bool = False
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    web_secret: str = ""

    # --- Rasm NSFW / OCR (Faza 7) ---
    image_nsfw_enabled: bool = False
    ocr_enabled: bool = False

    @field_validator("owner_ids", mode="before")
    @classmethod
    def _parse_owner_ids(cls, v: object) -> list[int]:
        """`OWNER_IDS=1,2,3` ko'rinishidagi qatorni ro'yxatga aylantiradi."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, (list, tuple)):
            return [int(x) for x in v]
        return [int(v)]  # type: ignore[arg-type]

    @property
    def is_sqlite(self) -> bool:
        return self.db_url.startswith("sqlite")

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)


@lru_cache
def get_settings() -> Settings:
    """Sozlamalarni bir marta o'qib, keshlab qaytaradi."""
    return Settings()  # type: ignore[call-arg]
