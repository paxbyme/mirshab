"""Mirshab botini ishga tushirish — entry point."""

from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from pydantic import ValidationError

from bot.config import get_settings
from bot.database import engine as db_engine
from bot.handlers import get_routers
from bot.middlewares import DbSessionMiddleware, ThrottlingMiddleware
from bot.services.antiflood import FloodController
from bot.services.scheduler import setup_scheduler
from bot.utils.logger import logger, setup_logging

_PUBLIC_COMMANDS = [
    BotCommand(command="start", description="Bot haqida"),
    BotCommand(command="help", description="Yordam / buyruqlar"),
    BotCommand(command="settings", description="Sozlamalar (admin)"),
    BotCommand(command="stats", description="Statistika (admin)"),
    BotCommand(command="logs", description="Moderatsiya tarixi (admin)"),
]


async def _on_startup(bot: Bot) -> None:
    # Webhookni o'chirib, kutilayotgan eski update'larni tashlaymiz — qayta
    # deploy paytida instans toza "egallab oladi" va getUpdates konflikti
    # (TelegramConflictError) tezroq bartaraf bo'ladi.
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.me()
    await bot.set_my_commands(_PUBLIC_COMMANDS)
    logger.info(f"Bot ishga tushdi: @{me.username} (id={me.id})")


async def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Mirshab ishga tushmoqda...")

    # --- DB ---
    session_factory = db_engine.create_session_factory(settings.db_url)
    await db_engine.init_models()  # dev/SQLite uchun; prod'da Alembic
    logger.info(f"Ma'lumotlar bazasi tayyor ({'sqlite' if settings.is_sqlite else 'postgres'})")

    # --- Bot & Dispatcher ---
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # --- Middlewares ---
    # DB sessiya — barcha update turlari uchun (outer)
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    # Anti-flood — faqat xabarlar uchun
    flood = FloodController(
        window_seconds=settings.flood_window_seconds,
        max_messages=settings.flood_max_messages,
        redis_url=settings.redis_url,
    )
    dp.message.middleware(ThrottlingMiddleware(flood))

    # --- Routerlar ---
    for router in get_routers():
        dp.include_router(router)

    # --- Opsional ML imkoniyatlar holati (diagnostika) ---
    from bot.services.optional_features import features_status

    fs = features_status()
    logger.info(
        "Opsional ML: image_nsfw={img} (env={img_env}), ocr={ocr} (env={ocr_env})".format(
            img="o'rnatilgan" if fs["image_nsfw"] else "yo'q",
            img_env=settings.image_nsfw_enabled,
            ocr="o'rnatilgan" if fs["ocr"] else "yo'q",
            ocr_env=settings.ocr_enabled,
        )
    )
    if settings.image_nsfw_enabled and not fs["image_nsfw"]:
        logger.warning(
            "IMAGE_NSFW_ENABLED=true, lekin NudeNet o'rnatilmagan "
            "(pip install -r requirements-ml.txt / Docker INSTALL_ML=true)"
        )
    if settings.ocr_enabled and not fs["ocr"]:
        logger.warning(
            "OCR_ENABLED=true, lekin pytesseract/tesseract yo'q "
            "(pip install -r requirements-ml.txt + tesseract binari)"
        )

    # --- Scheduler ---
    scheduler = setup_scheduler(bot, session_factory)

    # --- Web dashboard (Faza 7, opsional) ---
    web_task: asyncio.Task | None = None
    if settings.web_enabled:
        try:
            from bot.web.server import start_web

            web_task = asyncio.create_task(start_web(session_factory))
            logger.info(f"Web dashboard: http://{settings.web_host}:{settings.web_port}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Web dashboard ishga tushmadi: {e}")

    dp.startup.register(_on_startup)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("To'xtatilmoqda...")
        scheduler.shutdown(wait=False)
        if web_task:
            web_task.cancel()
        await flood.close()
        await bot.session.close()
        await db_engine.dispose_engine()


_CONFIG_HELP = """
╭──────────────────────────────────────────────────────────────╮
│  ❌ Sozlama xatosi — bot ishga tusha olmadi.                   │
╰──────────────────────────────────────────────────────────────╯

Quyidagi maydon(lar) to'ldirilmagan: {fields}

Tuzatish:
  1) `.env` faylini yarating:        cp .env.example .env
  2) `.env` ichida BOT_TOKEN ni to'ldiring (@BotFather dan oling)
     va OWNER_IDS ni o'z user_id'ingiz bilan (@userinfobot dan).

Docker bilan:
  • `.env` fayli loyiha ildizida bo'lishi shart (compose uni o'qiydi).
  • yoki:  BOT_TOKEN=... OWNER_IDS=... docker compose up -d
"""


def main() -> None:
    # Sozlamalarni erta tekshiramiz — xom traceback o'rniga tushunarli xabar.
    try:
        get_settings()
    except ValidationError as e:
        fields = ", ".join(str(err["loc"][0]).upper() for err in e.errors())
        print(_CONFIG_HELP.format(fields=fields), file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    main()
