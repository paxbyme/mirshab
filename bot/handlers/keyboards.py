"""Inline klaviaturalar (sozlamalar menyusi va h.k.)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

SETTINGS_PREFIX = "set"

# (sozlama_kaliti, ko'rsatiladigan nom)
_TOGGLES: list[tuple[str, str]] = [
    ("link_filter_on", "🔗 Havola filtri"),
    ("nsfw_filter_on", "🔞 18+ filtri"),
    ("captcha_on", "🛡 CAPTCHA"),
    ("antiflood_on", "🚦 Anti-flood"),
    ("spam_filter_on", "📢 Spam filtri (beta)"),
    ("bait_filter_on", "🎣 Spam-bot / bait filtri"),
    ("welcome_on", "👋 Salomlashish"),
    ("delete_service_messages", "🧹 Xizmat xabarlarini o'chirish"),
    ("image_nsfw_on", "🖼 Rasm NSFW (ML)"),
    ("ocr_on", "🔍 OCR (rasmdagi matn)"),
]


def build_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    rows = []
    for key, label in _TOGGLES:
        on = bool(settings.get(key))
        mark = "✅" if on else "❌"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {label}",
                    callback_data=f"{SETTINGS_PREFIX}:{key}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="🔒 Yopish", callback_data=f"{SETTINGS_PREFIX}:close")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


SETTINGS_TITLE = (
    "<b>⚙️ Guruh sozlamalari</b>\n"
    "Yoqish/o'chirish uchun tugmalarni bosing.\n"
    "✅ — yoqilgan, ❌ — o'chirilgan\n\n"
    "📋 Log kanal: <code>{log_channel}</code>\n"
    "<i>Log kanalni ulash: /setlog (kanalga botni admin qiling) yoki /setlog &lt;channel_id&gt;</i>"
)
