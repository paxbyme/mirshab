"""Faza 7 — FastAPI web dashboard (admin uchun ko'rish-only panel).

fastapi/uvicorn o'rnatilmagan bo'lsa import xatosi beradi va main.py uni
yutib yuboradi (bot baribir ishlaydi).
"""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from bot.config import get_settings
from bot.database import crud

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def create_app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Mirshab Dashboard", docs_url=None, redoc_url=None)

    def _check_key(key: str) -> bool:
        return not settings.web_secret or key == settings.web_secret

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request, key: str = Query(default="")) -> HTMLResponse:
        if not _check_key(key):
            return HTMLResponse("<h3>🔒 Kirish taqiqlangan. ?key=... talab qilinadi.</h3>", status_code=401)
        async with session_factory() as session:
            groups = await crud.all_groups(session)
            rows = []
            for g in groups:
                daily = await crud.daily_stats(session, g.id)
                rows.append(
                    {
                        "id": g.id,
                        "title": g.title or "—",
                        "members": await crud.total_members(session, g.id),
                        "banned": await crud.banned_count(session, g.id),
                        "deleted": daily.get("delete", 0),
                        "warns": daily.get("warn", 0),
                        "bans": daily.get("ban", 0),
                    }
                )
        return templates.TemplateResponse(
            "index.html", {"request": request, "groups": rows, "key": key}
        )

    @app.get("/group/{group_id}", response_class=HTMLResponse)
    async def group_detail(
        request: Request, group_id: int, key: str = Query(default="")
    ) -> HTMLResponse:
        if not _check_key(key):
            return HTMLResponse("<h3>🔒 Kirish taqiqlangan.</h3>", status_code=401)
        async with session_factory() as session:
            logs = await crud.recent_logs(session, group_id, limit=50)
            daily = await crud.daily_stats(session, group_id)
            log_rows = [
                {
                    "action": log.action,
                    "user_id": log.user_id,
                    "reason": log.reason,
                    "text": (log.message_text or "")[:120],
                    "time": log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else "",
                }
                for log in logs
            ]
        return templates.TemplateResponse(
            "group.html",
            {
                "request": request,
                "group_id": group_id,
                "logs": log_rows,
                "daily": daily,
                "key": key,
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


async def start_web(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Uvicorn serverini async kontekstda ishga tushiradi."""
    settings = get_settings()
    app = create_app(session_factory)
    config = uvicorn.Config(
        app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()
