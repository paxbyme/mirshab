"""Telegram'siz tezkor smoke-test: DB, dispatcher, moderatsiya logikasi."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.database import engine as dbe
from bot.handlers import get_routers
from bot.middlewares import DbSessionMiddleware, ThrottlingMiddleware
from bot.services.antiflood import FloodController
from bot.services.link_detector import extract_links
from bot.services.nsfw_detector import get_detector


async def main() -> None:
    sf = dbe.create_session_factory("sqlite+aiosqlite:///:memory:")
    await dbe.init_models()
    print("OK  DB jadvallari yaratildi")

    bot = Bot("123:dummy", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(DbSessionMiddleware(sf))
    dp.message.middleware(ThrottlingMiddleware(FloodController(5, 5, "")))
    for r in get_routers():
        dp.include_router(r)
    used = dp.resolve_used_update_types()
    print("OK  Dispatcher qurildi. Update turlari:", used)

    det = get_detector()
    cases = [
        ("Salom dostlar, qalaysiz?", "toza xabar"),
        ("Mana kanal: t.me/reklama_kanal", "tg havola"),
        ("Eng zor kazino, 1xbet.com ga kiring", "blacklist domen + nsfw"),
        ("18+ kontent shu yerda", "nsfw matn"),
    ]
    print("Moderatsiya qarorlari:")
    for text, label in cases:
        scan = extract_links(text)
        v = det.check_text(text)
        if v.severity >= 2:
            verdict = f"NSFW(sev={v.severity}) -> ochiriladi"
        elif scan.has_any:
            verdict = "HAVOLA -> tekshiriladi/ochiriladi"
        else:
            verdict = "TOZA -> otkaziladi"
        targets = list(scan.domains) + list(scan.usernames)
        print(f"  [{label:24}] {verdict:34} links={targets or '-'} nsfw={v.severity}")

    await bot.session.close()
    await dbe.dispose_engine()
    print("OK  Smoke-test xatosiz tugadi")


if __name__ == "__main__":
    asyncio.run(main())
