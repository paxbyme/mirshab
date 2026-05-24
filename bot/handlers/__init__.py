"""Barcha router'larni yig'ib, dispatcher'ga ulash uchun ro'yxat."""

from __future__ import annotations

from aiogram import Router

from bot.handlers import admin, callbacks, moderation, new_member, start


def get_routers() -> list[Router]:
    """Router'larni TO'G'RI tartibda qaytaradi.

    Tartib muhim: buyruqlar va a'zo hodisalari avval, umumiy moderatsiya oxirida
    (chunki moderation har qanday matnli xabarni ushlaydi).
    """
    return [
        start.router,
        admin.router,
        callbacks.router,
        new_member.router,
        moderation.router,  # eng oxirida — "catch-all" xabar tekshiruvi
    ]
