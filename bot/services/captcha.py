"""CAPTCHA — yangi a'zo bot emasligini tasdiqlash (matematik savol + tugmalar)."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# callback_data format: capt:<user_id>:<chosen_answer>
CALLBACK_PREFIX = "capt"


@dataclass
class CaptchaEntry:
    user_id: int
    answer: int
    question: str
    message_id: int | None = None
    timeout_task: asyncio.Task | None = field(default=None, repr=False)


class CaptchaManager:
    """Faol CAPTCHA'larni (chat_id, user_id) bo'yicha kuzatadi."""

    def __init__(self) -> None:
        self._pending: dict[tuple[int, int], CaptchaEntry] = {}

    @staticmethod
    def _make_question() -> tuple[str, int]:
        a, b = random.randint(2, 9), random.randint(2, 9)
        op = random.choice(["+", "-", "×"])
        if op == "+":
            answer = a + b
        elif op == "-":
            if a < b:
                a, b = b, a
            answer = a - b
        else:
            answer = a * b
        return f"{a} {op} {b} = ?", answer

    def build_challenge(self, user_id: int) -> tuple[str, int, InlineKeyboardMarkup]:
        """Savol matni, to'g'ri javob va variantli klaviatura qaytaradi."""
        question, answer = self._make_question()
        options = {answer}
        while len(options) < 4:
            delta = random.randint(-5, 5)
            cand = answer + delta
            if cand >= 0:
                options.add(cand)
        opts = list(options)
        random.shuffle(opts)
        buttons = [
            InlineKeyboardButton(
                text=str(o), callback_data=f"{CALLBACK_PREFIX}:{user_id}:{o}"
            )
            for o in opts
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
        return question, answer, kb

    def register(
        self,
        chat_id: int,
        user_id: int,
        answer: int,
        question: str,
        timeout: int,
        on_timeout: Callable[[], Awaitable[None]],
    ) -> None:
        """CAPTCHA'ni ro'yxatga oladi va timeout taymerini ishga tushiradi."""
        self.cancel(chat_id, user_id)  # eski bo'lsa tozalash

        async def _timeout_runner() -> None:
            try:
                await asyncio.sleep(timeout)
            except asyncio.CancelledError:
                return
            # Hali ham kutilayotgan bo'lsa — timeout amalga oshadi
            if (chat_id, user_id) in self._pending:
                self._pending.pop((chat_id, user_id), None)
                await on_timeout()

        task = asyncio.create_task(_timeout_runner())
        self._pending[(chat_id, user_id)] = CaptchaEntry(
            user_id=user_id, answer=answer, question=question, timeout_task=task
        )

    def set_message_id(self, chat_id: int, user_id: int, message_id: int) -> None:
        entry = self._pending.get((chat_id, user_id))
        if entry:
            entry.message_id = message_id

    def is_pending(self, chat_id: int, user_id: int) -> bool:
        return (chat_id, user_id) in self._pending

    def check(self, chat_id: int, user_id: int, chosen: int) -> str:
        """'ok' | 'wrong' | 'unknown' qaytaradi. To'g'ri bo'lsa tozalaydi."""
        entry = self._pending.get((chat_id, user_id))
        if entry is None:
            return "unknown"
        if chosen == entry.answer:
            self.cancel(chat_id, user_id)
            return "ok"
        return "wrong"

    def cancel(self, chat_id: int, user_id: int) -> CaptchaEntry | None:
        """CAPTCHA'ni bekor qiladi (taymerni ham). Mavjud entry'ni qaytaradi."""
        entry = self._pending.pop((chat_id, user_id), None)
        if entry and entry.timeout_task and not entry.timeout_task.done():
            entry.timeout_task.cancel()
        return entry


# Global menejer (bitta bot instansiyasi uchun)
captcha_manager = CaptchaManager()
