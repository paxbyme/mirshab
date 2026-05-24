# 🛡 Mirshab — Telegram guruh qo'riqchisi

Guruhingizni **reklama, havola, 18+ kontent, spam va botlar**dan avtomatik
tozalab turadi. Yangi a'zolarni CAPTCHA bilan tekshiradi, qoidabuzarlarni
ogohlantiradi yoki bloklaydi — siz tinch turasiz.

---

## ⚡ 3 qadamda ishga tushirish

1. **Botni guruhga qo'shing.**
2. Unga **administrator** huquqini bering (kamida: *xabar o'chirish* va
   *foydalanuvchini cheklash/ban qilish*).
3. Guruhda **`/settings`** yozib, kerakli himoyalarni yoqing. Tamom! ✅

> 💡 Bot guruhdagi xabarlarni ko'ra olishi uchun, agar o'zingiz yaratgan
> bo'lsangiz, [@BotFather](https://t.me/BotFather)'da **Group Privacy**'ni
> o'chiring (`/setprivacy` → Disable).

---

## ✨ Nimalardan himoya qiladi

| | Imkoniyat |
|--|-----------|
| 🔗 | **Havola/reklama** — ruxsatsiz link, `t.me/`, `@username` o'chiriladi |
| 🔞 | **18+ kontent** — shubhali so'z va kanallar bloklanadi |
| 🛡 | **CAPTCHA** — yangi a'zo bot emasligini tekshiradi |
| 🤖 | **Bot himoyasi** — ruxsatsiz qo'shilgan botlar avto-ban |
| 🎣 | **Spam-bot / bait** — "profilimga qaring 💞" kabi jalb qiluvchi izohlar (uz/ru) |
| 🧠 | **AI tahlil (opsional)** — Claude xabar + profil bio/kanalini o'qib, profilga jalb qiluvchi spam'ni aniqlab xabarni o'chiradi |
| 🚦 | **Anti-flood** — xabar bilan bostirganlar vaqtincha mute |
| ⚖️ | **Ogohlantirish** — bir necha buzilishdan keyin avtomatik ban |
| 📊 | **Statistika va log** — barcha harakatlar yoziladi |

---

## 💬 Buyruqlar

**Hamma uchun:** `/start`, `/help`

**Adminlar uchun (guruh ichida):**

| Buyruq | Vazifa |
|--------|--------|
| `/settings` | Himoyalarni yoqish/o'chirish (menyu) |
| `/whitelist` · `/blacklist` | Ruxsat berilgan / taqiqlangan havolalar |
| `/warn` | (javob qilib) ogohlantirish |
| `/mute [vaqt]` · `/unmute` | Ovozini o'chirish / qaytarish — `/mute 1h` |
| `/ban` · `/unban <id>` | Ban qilish / bekor qilish |
| `/stats` · `/logs` | Statistika va so'nggi harakatlar |
| `/setlog <id>` | Log kanalni ulash |

> ⏱ Vaqt formati: `30` (daqiqa), `10m`, `2h`, `1d`.

---

## 🛠 O'zingiz ishga tushirmoqchimisiz? (dasturchilar uchun)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # BOT_TOKEN va OWNER_IDS ni to'ldiring
python -m bot.main
```

`BOT_TOKEN` — [@BotFather](https://t.me/BotFather)dan, `OWNER_IDS` (sizning
user_id'ingiz) — [@userinfobot](https://t.me/userinfobot)dan olinadi.

**Docker bilan** (bot + PostgreSQL + Redis):

```bash
cp .env.example .env
docker compose up -d --build
```

<details>
<summary>Qo'shimcha: opsional imkoniyatlar, testlar, migratsiya</summary>

**Opsional og'ir imkoniyatlar** (ularsiz ham bot to'liq ishlaydi) —
rasm NSFW tekshiruvi, OCR, spam classifier, web dashboard:

```bash
pip install -r requirements-ml.txt   # OCR uchun: brew install tesseract
```
`.env` da `IMAGE_NSFW_ENABLED`, `OCR_ENABLED`, `WEB_ENABLED` ni yoqing.
Docker/Railway'da og'ir ML paketlar uchun build arg: `INSTALL_ML=true`.

**AI moderatsiya (Claude):** profilga jalb qiluvchi spam-botlarni aniqlash uchun
`.env` da `ANTHROPIC_API_KEY` va `AI_MODERATION_ENABLED=true` ni qo'ying
(`AI_MODEL` standart `claude-haiku-4-5`). Kalit bo'lsa, bot har bir xabarni —
yuboruvchining bio/profil kanali kontekstida — o'qib, profilga jalb qiluvchi
scam'ni topsa **xabarni o'chiradi**. Kalit yo'q bo'lsa kalit-so'z heuristikasiga
(`bait_detector`) fallback qiladi. `anthropic` paketi `requirements.txt` da bor.

**Testlar:** `pytest -q`

**Migratsiya (prod/PostgreSQL):** `alembic upgrade head`
(dev/SQLite'da jadvallar avtomatik yaratiladi).

</details>

---

## 🧰 Texnologiya

Python 3.12 · [aiogram 3](https://docs.aiogram.dev) · SQLAlchemy 2.0 (async) ·
SQLite/PostgreSQL · APScheduler · (opsional) Redis, FastAPI, NudeNet

> Shaxsiy/o'quv loyihasi. Telegram va platforma qoidalariga rioya qiling.
