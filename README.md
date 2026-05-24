# 🛡 Qo'riqchi — Telegram guruh moderator boti

Ommaviy Telegram guruhlarni **reklama, 18+ kontent va spam**dan avtomatik
himoya qiluvchi bot. Havolalarni o'chiradi, shubhali a'zolarni cheklaydi,
yangi a'zolarni CAPTCHA bilan tekshiradi va adminlarga statistika beradi.

> Texnologiya: Python 3.12+ · [aiogram 3](https://docs.aiogram.dev) ·
> SQLAlchemy 2.0 (async) · SQLite/PostgreSQL · APScheduler · (opsional) Redis, FastAPI

---

## ✨ Imkoniyatlar

| Imkoniyat | Tavsif |
|-----------|--------|
| 🔗 **Havola filtri** | URL, `t.me/`, `@username`, `tg://` aniqlash; oq/qora ro'yxat |
| 🔞 **18+ filtri** | Kalit so'zlar lug'ati (uz/ru/en) + username/forward pattern'lari; severity tizimi |
| 🛡 **CAPTCHA** | Yangi a'zo uchun matematik tekshiruv (timeout'da kick) |
| 🤖 **Bot himoyasi** | Admin qo'shmagan botlar avtomatik ban |
| 🚦 **Anti-flood** | Tez xabar yuborgan a'zoni vaqtincha mute |
| ⚖️ **Warning tizimi** | N ogohlantirishdan keyin avtomatik ban |
| ⚙️ **Admin panel** | Inline `/settings` menyu, guruh bo'yicha sozlamalar |
| 📊 **Statistika va log** | `/stats`, `/logs`, log kanal, kunlik hisobot |
| 🖼 **(opsional) Rasm NSFW** | NudeNet bilan rasm tekshiruvi |
| 🔍 **(opsional) OCR** | Rasm ichidagi matnda havola/reklama aniqlash |
| 📢 **(opsional) Spam classifier** | Heuristik + scikit-learn |
| 🌐 **(opsional) Web dashboard** | FastAPI ko'rish-only panel |

---

## 🚀 Tezkor boshlash (dev, SQLite)

```bash
# 1. Virtual muhit
python3 -m venv .venv && source .venv/bin/activate

# 2. Bog'liqliklar
pip install -r requirements.txt

# 3. Sozlamalar
cp .env.example .env
#   .env ichida BOT_TOKEN va OWNER_IDS ni to'ldiring

# 4. Ishga tushirish
python -m bot.main
```

`BOT_TOKEN` ni [@BotFather](https://t.me/BotFather) dan, o'z `OWNER_IDS`
(user_id) ni [@userinfobot](https://t.me/userinfobot) dan oling.

> ⚠️ BotFather'da botning **Group Privacy** rejimini **o'chiring**
> (`/setprivacy` → Disable), aks holda bot guruhdagi barcha xabarlarni
> ko'ra olmaydi.

---

## 🤖 Botni guruhga ulash

1. Botni guruhingizga qo'shing.
2. Unga **administrator** huquqini bering — kamida:
   - *Xabarlarni o'chirish*
   - *Foydalanuvchilarni cheklash / ban qilish*
3. Guruhda `/settings` yozib, kerakli filtrlarni yoqing.
4. (ixtiyoriy) Log kanal yarating, botni unga admin qiling va
   `/setlog <channel_id>` bilan ulang.

---

## 💬 Buyruqlar

**Hamma uchun:** `/start`, `/help`

**Adminlar uchun (guruhda):**

| Buyruq | Vazifa |
|--------|--------|
| `/settings` | Inline sozlamalar menyusi |
| `/setlog <id>` | Log kanalni ulash/uzish |
| `/whitelist add\|remove\|list <pattern>` | Ruxsat berilgan havolalar |
| `/blacklist add\|remove\|list <pattern>` | Taqiqlangan havolalar |
| `/warn` | (reply) ogohlantirish |
| `/mute [vaqt]` | (reply) ovozini o'chirish — `/mute 1h` |
| `/unmute` | (reply) mute'ni olib tashlash |
| `/ban` | (reply) ban qilish |
| `/unban <user_id>` | ban'ni bekor qilish |
| `/stats` | Guruh statistikasi |
| `/logs` | Oxirgi moderatsiya harakatlari |

**Vaqt formati:** `30` (daqiqa), `10m`, `2h`, `1d`.

---

## 🐳 Deploy (Docker + PostgreSQL + Redis)

```bash
cp .env.example .env        # BOT_TOKEN, OWNER_IDS to'ldiring
export POSTGRES_PASSWORD=kuchli-parol
docker compose up -d --build
docker compose logs -f bot
```

`docker-compose.yml` bot, PostgreSQL va Redis'ni birga ishga tushiradi.
`DB_URL` va `REDIS_URL` compose ichida avtomatik o'rnatiladi.

---

## 🗃 Migratsiyalar (PostgreSQL/prod)

Dev/SQLite'da jadvallar avtomatik yaratiladi. Prod uchun Alembic:

```bash
# Birinchi migratsiyani generatsiya qilish
alembic revision --autogenerate -m "initial"
# Qo'llash
alembic upgrade head
```

---

## ⚙️ Opsional imkoniyatlar (Faza 7)

Og'ir paketlar alohida o'rnatiladi — **ularsiz ham bot to'liq ishlaydi**:

```bash
pip install -r requirements-ml.txt
# OCR uchun tizim binari ham kerak:
#   macOS:  brew install tesseract
#   Debian: apt install tesseract-ocr
```

`.env` da yoqing:

```ini
IMAGE_NSFW_ENABLED=true   # NudeNet
OCR_ENABLED=true          # pytesseract
WEB_ENABLED=true          # FastAPI dashboard -> http://localhost:8080
WEB_SECRET=maxfiy-kalit   # dashboard'ga ?key=maxfiy-kalit bilan kiriladi
```

Keyin har bir guruhda `/settings` orqali mos toggle'ni yoqing.

---

## 🧪 Testlar

```bash
pip install pytest pytest-asyncio
pytest -q
```

---

## 📁 Loyiha tuzilishi

```
bot/
├── main.py            # entry point
├── config.py          # pydantic-settings
├── handlers/          # start, admin, moderation, new_member, callbacks
├── middlewares/       # db_session, throttling, admin_check
├── filters/           # is_admin, has_link, is_nsfw
├── services/          # link_detector, nsfw_detector, moderator, captcha,
│                      #   stats, antiflood, scheduler, spam_classifier,
│                      #   optional_features, settings_cache
├── database/          # engine, models, crud
├── data/              # nsfw_keywords.txt, blacklist_domains.txt, messages.py
├── web/               # FastAPI dashboard (opsional)
└── utils/             # logger, helpers
```

---

## 📜 Litsenziya

Shaxsiy/o'quv loyihasi. Telegram va platforma qoidalariga rioya qiling.
# mirshab
