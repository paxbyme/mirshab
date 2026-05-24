"""/start va /help buyruqlari."""

from __future__ import annotations

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data import messages as msg
from bot.database import crud

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(msg.START_PRIVATE, disable_web_page_preview=True)
    else:
        await crud.get_or_create_group(session, message.chat.id, message.chat.title or "")
        await message.answer(msg.START_GROUP)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(msg.HELP, disable_web_page_preview=True)
