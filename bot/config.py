"""Ilova sozlamalari — `.env` faylidan o'qiladi (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# asyncpg tushunmaydigan libpq-ga xos query parametrlari (Railway public URL'da uchraydi)
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "gssencmode", "target_session_attrs"}
# SSL talab qiladigan sslmode qiymatlari
_SSL_REQUIRED = {"require", "verify-ca", "verify-full"}


def normalize_db_url(url: str) -> str:
    """DB URL'ini SQLAlchemy async-asyncpg uchun moslashtiradi.

    Railway/Heroku `postgres://...` yoki `postgresql://...?sslmode=require`
    beradi; asyncpg uchun `postgresql+asyncpg://` kerak va `sslmode` o'rniga
    `ssl` ishlatiladi.
    """
    url = url.strip()
    if not url:
        return url

    # 1) Drayver sxemasini to'g'rilash
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    # 2) Postgres bo'lmasa — tegmaymiz (sqlite va h.k.)
    if not url.startswith("postgresql+asyncpg://"):
        return url

    # 3) libpq-ga xos query paramlarni asyncpg tushunadiganiga o'tkazamiz
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    cleaned: list[tuple[str, str]] = []
    needs_ssl = False
    for key, value in query:
        if key.lower() == "sslmode":
            if value.lower() in _SSL_REQUIRED:
                needs_ssl = True
            continue  # sslmode'ni olib tashlaymiz
        if key.lower() in _LIBPQ_ONLY_PARAMS:
            continue
        cleaned.append((key, value))
    if needs_ssl and not any(k.lower() == "ssl" for k, _ in cleaned):
        cleaned.append(("ssl", "require"))

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(cleaned), parts.fragment)
    )


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
    # `DB_URL` (yoki Railway/Heroku avtomatik beradigan `DATABASE_URL`) dan o'qiladi.
    db_url: str = Field(
        default="sqlite+aiosqlite:///mirshab.db",
        validation_alias=AliasChoices("DB_URL", "DATABASE_URL"),
    )

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

    # --- AI moderatsiya (Claude — profilga jalb qiluvchi spam-botlar) ---
    # Kalit bo'lsa va yoqilgan bo'lsa ishlaydi; aks holda heuristikaga fallback.
    anthropic_api_key: str = ""
    ai_moderation_enabled: bool = False
    ai_model: str = "claude-haiku-4-5"

    @property
    def use_ai_moderation(self) -> bool:
        return self.ai_moderation_enabled and bool(self.anthropic_api_key)

    @field_validator("db_url", mode="after")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        return normalize_db_url(v)

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
