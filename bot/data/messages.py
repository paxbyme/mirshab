"""Bot javob matnlari (o'zbek tilida). HTML parse_mode ishlatiladi."""

from __future__ import annotations

START_PRIVATE = (
    "👋 <b>Salom! Men Mirshab</b> — guruh moderator botiman.\n\n"
    "Men guruhingizni quyidagilardan himoya qilaman:\n"
    "🔗 Reklama va begona havolalar\n"
    "🔞 18+ kontent va shubhali kanallar\n"
    "🤖 Spam botlar va flood\n"
    "🛡 Yangi a'zolar uchun CAPTCHA\n\n"
    "<b>Qanday qo'shish kerak:</b>\n"
    "1️⃣ Meni guruhingizga qo'shing\n"
    "2️⃣ Menga <b>administrator</b> huquqini bering "
    "(xabar o'chirish va a'zolarni cheklash huquqlari bilan)\n"
    "3️⃣ Guruhda /settings yozib sozlamalarni moslang\n\n"
    "Yordam uchun: /help"
)

START_GROUP = (
    "👋 Salom! Men <b>Mirshab</b>. Guruhni himoya qilishga tayyorman.\n"
    "Meni administrator qiling va /settings orqali sozlang."
)

HELP = (
    "<b>📖 Mirshab — buyruqlar</b>\n\n"
    "<b>Hamma uchun:</b>\n"
    "/start — bot haqida\n"
    "/help — yordam\n\n"
    "<b>Faqat adminlar uchun (guruhda):</b>\n"
    "/settings — sozlamalar menyusi\n"
    "/whitelist add|remove|list <code>&lt;pattern&gt;</code> — ruxsat berilgan havolalar\n"
    "/blacklist add|remove|list <code>&lt;pattern&gt;</code> — taqiqlangan havolalar\n"
    "/warn — (javob qaytarib) ogohlantirish berish\n"
    "/mute [vaqt] — (javob qaytarib) ovozini o'chirish, masalan <code>/mute 1h</code>\n"
    "/unmute — mute'ni olib tashlash\n"
    "/ban — (javob qaytarib) ban qilish\n"
    "/unban <code>&lt;user_id&gt;</code> — ban'ni olib tashlash\n"
    "/stats — guruh statistikasi\n"
    "/logs — oxirgi moderatsiya harakatlari\n\n"
    "💡 <i>Vaqt formati:</i> <code>30</code> (daqiqa), <code>10m</code>, <code>2h</code>, <code>1d</code>"
)

NOT_ADMIN = "⛔️ Bu buyruq faqat guruh adminlari uchun."
ONLY_IN_GROUP = "ℹ️ Bu buyruq faqat guruhlarda ishlaydi."
BOT_NOT_ADMIN = (
    "⚠️ Men hali administrator emasman. Iltimos, menga xabar o'chirish va "
    "a'zolarni cheklash huquqlarini bering."
)

# --- Moderatsiya ---
LINK_DELETED = (
    "🔗 {user}, havolalar bu yerda taqiqlangan. Xabaringiz o'chirildi.\n"
    "Ogohlantirish: <b>{warnings}/{max}</b>"
)
NSFW_DELETED = (
    "🔞 {user}, nomaqbul kontent aniqlandi. Xabaringiz o'chirildi.\n"
    "Ogohlantirish: <b>{warnings}/{max}</b>"
)
WARNED = "⚠️ {user} ogohlantirildi. ({warnings}/{max})"
MUTED = "🔇 {user} {duration} davomida ovozsiz qilindi.\nSabab: {reason}"
UNMUTED = "🔊 {user} ovozi tiklandi."
BANNED = "🔨 {user} guruhdan chetlatildi (ban).\nSabab: {reason}"
UNBANNED = "✅ Foydalanuvchi ban'dan chiqarildi."
FLOOD_MUTED = "🚦 {user}, juda tez xabar yubormoqdasiz. {duration} kuting."
BOT_KICKED = "🤖 Ruxsatsiz qo'shilgan bot ({name}) chetlatildi."

# --- CAPTCHA / yangi a'zo ---
CAPTCHA_PROMPT = (
    "👋 Xush kelibsiz, {user}!\n\n"
    "Siz odam ekanligingizni tasdiqlang — quyidagi tugmani <b>{timeout} soniya</b> "
    "ichida bosing. Aks holda guruhdan chiqarilasiz."
)
CAPTCHA_OK = "✅ Rahmat, {user}! Guruhga xush kelibsiz. 🎉"
CAPTCHA_FAIL_KICK = "⏱ {user} CAPTCHA'ni o'tmadi va chetlatildi."
CAPTCHA_WRONG_USER = "Bu tugma siz uchun emas."
WELCOME_DEFAULT = "🎉 Xush kelibsiz, {user}! Guruh qoidalariga rioya qiling."

# --- Whitelist / Blacklist ---
WL_ADDED = "✅ <code>{pattern}</code> oq ro'yxatga qo'shildi."
WL_EXISTS = "ℹ️ <code>{pattern}</code> allaqachon oq ro'yxatda."
WL_REMOVED = "🗑 <code>{pattern}</code> oq ro'yxatdan o'chirildi."
WL_NOT_FOUND = "❓ <code>{pattern}</code> oq ro'yxatda topilmadi."
WL_EMPTY = "📭 Oq ro'yxat bo'sh."
WL_LIST_HEADER = "<b>✅ Oq ro'yxat:</b>\n"

BL_ADDED = "✅ <code>{pattern}</code> qora ro'yxatga qo'shildi."
BL_EXISTS = "ℹ️ <code>{pattern}</code> allaqachon qora ro'yxatda."
BL_REMOVED = "🗑 <code>{pattern}</code> qora ro'yxatdan o'chirildi."
BL_NOT_FOUND = "❓ <code>{pattern}</code> qora ro'yxatda topilmadi."
BL_EMPTY = "📭 Qora ro'yxat bo'sh."
BL_LIST_HEADER = "<b>⛔️ Qora ro'yxat:</b>\n"

LIST_USAGE = (
    "Foydalanish: <code>/{cmd} add|remove|list [pattern]</code>\n"
    "Masalan: <code>/{cmd} add example.com</code>"
)

# --- Buyruq xatolari ---
REPLY_REQUIRED = "↩️ Bu buyruqni foydalanuvchi xabariga <b>javob qaytarib</b> yuboring."
CANT_TOUCH_ADMIN = "🛡 Boshqa adminga nisbatan bu amalni bajara olmayman."
USER_NOT_FOUND = "❓ Foydalanuvchi topilmadi."

# --- Stats / logs ---
STATS_TEMPLATE = (
    "<b>📊 {title} — statistika</b>\n\n"
    "👥 Kuzatuvdagi a'zolar: <b>{members}</b>\n"
    "🚫 Ban qilinganlar: <b>{banned}</b>\n\n"
    "<b>Oxirgi 24 soat:</b>\n"
    "🗑 O'chirilgan xabarlar: <b>{delete}</b>\n"
    "⚠️ Ogohlantirishlar: <b>{warn}</b>\n"
    "🔇 Mute'lar: <b>{mute}</b>\n"
    "🔨 Ban'lar: <b>{ban}</b>"
)
LOGS_HEADER = "<b>🗂 Oxirgi moderatsiya harakatlari:</b>\n"
LOGS_EMPTY = "📭 Hozircha hech qanday harakat qayd etilmagan."

# --- Log kanal ---
LOG_ENTRY = (
    "<b>{action_emoji} {action}</b>\n"
    "👤 Foydalanuvchi: {user}\n"
    "💬 Sabab: {reason}\n"
    "📝 Matn: <i>{text}</i>\n"
    "🕒 {time}"
)

DAILY_REPORT = (
    "<b>📈 Kunlik hisobot — {title}</b>\n"
    "📅 {date}\n\n"
    "🗑 O'chirilgan: <b>{delete}</b>\n"
    "⚠️ Ogohlantirish: <b>{warn}</b>\n"
    "🔇 Mute: <b>{mute}</b>\n"
    "🔨 Ban: <b>{ban}</b>\n"
    "👥 Jami a'zolar: <b>{members}</b>"
)

ACTION_EMOJI = {
    "delete": "🗑",
    "warn": "⚠️",
    "mute": "🔇",
    "unmute": "🔊",
    "ban": "🔨",
    "unban": "✅",
    "kick": "👢",
    "captcha_fail": "⏱",
}
