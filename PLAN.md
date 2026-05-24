# Qo'riqchi — Telegram Guruh Moderator Boti

## 1. Loyihaning maqsadi

Telegram ommaviy guruhlarda tarqaladigan reklamalar, 18+ kontent havolalari va spam yuboruvchi foydalanuvchilar/botlarni **avtomatik aniqlash, o'chirish va cheklash**. Guruh adminiga qo'l mehnatini kamaytirib, toza muhitni saqlab turish.

---

## 2. Asosiy funksiyalar (MVP)

### 2.1 Link/Reklama filtri
- Xabardagi har qanday **URL** (`http://`, `https://`, `t.me/`, `@username`, `tg://`) ni aniqlash
- **Whitelist** (oq ro'yxat) — guruh admini ruxsat bergan domenlar va kanallar
- **Blacklist** (qora ro'yxat) — taqiqlangan domen/kanallar (18+ saytlar, reklama agentliklari)
- Whitelist'da bo'lmagan har qanday havola — avtomatik o'chiriladi
- Telegram ichidagi havolalar uchun ham (forward'lar, mention'lar) tekshirish

### 2.2 18+ kontent filtri
- Xabar matnida **kalit so'zlar lug'ati** (uzbek + rus + ingliz tillarida)
- Username/kanal nomida shubhali pattern'lar (`@adult_*`, `@xxx_*`, va h.k.)
- Forward qilingan kanal manbasini blacklist bilan solishtirish
- Rasm/video uchun **NSFW detection** (keyingi bosqichda — opsional)
- Sticker pack nomi tekshiruvi

### 2.3 Foydalanuvchi/Bot boshqaruvi
- Yangi qo'shilgan foydalanuvchini **CAPTCHA** orqali tekshirish (bot emasligini)
- Profil rasmi yo'q + username shubhali bo'lsa — kuzatuvga olish
- Spam yuborgan user'ni **avto-mute** (3 marta ogohlantirish → ban)
- Faqat adminlar tomonidan qo'shilgan botlar qoladi, boshqalari avto-o'chiriladi
- **Anti-flood** — 1 user 5 soniyada 5+ xabar yuborsa, vaqtincha mute

### 2.4 Admin paneli (bot ichida)
- `/start` — botni guruhga qo'shish yo'riqnomasi
- `/settings` — guruh sozlamalari (faqat admin uchun)
- `/whitelist add|remove|list` — ruxsat berilgan link'lar
- `/blacklist add|remove|list` — taqiqlangan link'lar
- `/warn @user` — qo'lda ogohlantirish
- `/ban @user`, `/mute @user [vaqt]`, `/unban @user`
- `/stats` — guruh statistikasi (qancha xabar o'chirildi, kim ban qilindi)
- `/logs` — oxirgi moderatsiya harakatlari

### 2.5 Loglash va hisobot
- Har bir o'chirilgan xabar log kanalga yuboriladi (admin ko'rishi uchun)
- Kunlik/haftalik hisobot: nechta spam, nechta ban, faol foydalanuvchilar

---

## 3. Texnik stack

| Komponent | Tanlov | Sabab |
|-----------|--------|-------|
| Til | **Python 3.12+** | User talabi |
| Bot framework | **aiogram 3.x** | Modern, async, Telegram Bot API to'liq qo'llab-quvvatlaydi |
| DB (dev) | **SQLite** | Sodda, fayl asosida, deploy oson |
| DB (prod) | **PostgreSQL** | Ko'p guruh, ko'p user uchun |
| ORM | **SQLAlchemy 2.0 (async)** | Type-safe, async qo'llab-quvvatlash |
| Migration | **Alembic** | DB schema versiyalash |
| Cache | **Redis** (opsional) | Anti-flood counter, rate limiting |
| Config | **pydantic-settings** + `.env` | Type-safe sozlamalar |
| Logging | **loguru** | Sodda va kuchli |
| Deploy | **Docker + VPS** (yoki Railway) | Doimiy ishlab turish |
| Scheduler | **APScheduler** | Kunlik hisobot, mute muddatini tekshirish |

---

## 4. Loyiha tuzilishi

```
Qo'riqchi/
├── bot/
│   ├── __init__.py
│   ├── main.py                  # Botni ishga tushirish entry point
│   ├── config.py                # Pydantic settings (.env'dan o'qiydi)
│   │
│   ├── handlers/                # Xabar/komanda handler'lari
│   │   ├── __init__.py
│   │   ├── start.py             # /start, /help
│   │   ├── admin.py             # /settings, /whitelist, /ban, va h.k.
│   │   ├── moderation.py        # Asosiy: har bir xabarni tekshirish
│   │   ├── new_member.py        # Yangi user/bot kelganda CAPTCHA
│   │   └── callbacks.py         # Inline button callback'lari
│   │
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── throttling.py        # Anti-flood
│   │   ├── admin_check.py       # Admin komandalari uchun
│   │   └── db_session.py        # Har bir update'ga DB session bog'lash
│   │
│   ├── filters/
│   │   ├── __init__.py
│   │   ├── is_admin.py
│   │   ├── has_link.py          # Xabarda link bormi?
│   │   └── is_nsfw.py           # 18+ kontent filtri
│   │
│   ├── services/                # Asosiy biznes logika
│   │   ├── __init__.py
│   │   ├── link_detector.py     # URL, @username, t.me/ aniqlash
│   │   ├── nsfw_detector.py     # 18+ kalit so'z + pattern matching
│   │   ├── moderator.py         # O'chirish, mute, ban harakatlari
│   │   ├── captcha.py           # Yangi user uchun CAPTCHA
│   │   └── stats.py             # Statistika hisoblash
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── engine.py            # SQLAlchemy engine + session
│   │   ├── models.py            # Jadval modellari
│   │   └── crud.py              # CRUD funksiyalar
│   │
│   ├── data/                    # Statik ma'lumotlar
│   │   ├── nsfw_keywords.txt    # 18+ kalit so'zlar (uz/ru/en)
│   │   ├── blacklist_domains.txt
│   │   └── messages.py          # Bot javob matnlari (uzbek)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── helpers.py
│
├── alembic/                     # DB migration fayllar
├── tests/                       # Unit testlar
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 5. Database schema (asosiy jadvallar)

### `groups`
| Ustun | Tur | Izoh |
|-------|-----|------|
| id (PK) | BIGINT | Telegram chat_id |
| title | TEXT | Guruh nomi |
| settings | JSONB | Sozlamalar (link_filter_on, nsfw_filter_on, captcha_on, log_channel_id) |
| added_at | TIMESTAMP | Bot qachon qo'shilgan |

### `users`
| Ustun | Tur | Izoh |
|-------|-----|------|
| id (PK) | BIGINT | Telegram user_id |
| username | TEXT | |
| first_name | TEXT | |
| is_bot | BOOLEAN | |

### `group_members`
| Ustun | Tur | Izoh |
|-------|-----|------|
| group_id (FK) | BIGINT | |
| user_id (FK) | BIGINT | |
| warnings | INT | Ogohlantirishlar soni (default 0) |
| muted_until | TIMESTAMP NULL | |
| is_banned | BOOLEAN | |

### `whitelist`
| group_id | pattern | type (domain/username/regex) | added_by | added_at |

### `blacklist`
| group_id | pattern | type | reason | added_by | added_at |

### `moderation_logs`
| id | group_id | user_id | action (delete/warn/mute/ban) | reason | message_text | created_at |

### `nsfw_keywords` (global)
| keyword | language | severity (1-3) |

---

## 6. Asosiy oqim (workflow)

### 6.1 Yangi xabar kelganda:
```
1. Middleware: anti-flood tekshiruvi (Redis counter)
2. Filter: xabar matni/caption olinadi
3. Service: link_detector → URL'lar topiladi
4. Service: nsfw_detector → 18+ kontent tekshiriladi
5. DB: whitelist/blacklist solishtirish
6. Qaror:
   - Tozami → o'tkazib yuborish
   - Shubhali → ogohlantirish + log
   - Yaroqsiz → o'chirish + warning++
   - 3+ warning → mute/ban
7. Log kanalga harakat haqida yozish
```

### 6.2 Yangi a'zo qo'shilganda:
```
1. Agar bot bo'lsa va admin qo'shmagan bo'lsa → darhol ban
2. Agar user bo'lsa:
   - CAPTCHA yuboriladi (60 soniya muddat)
   - Javob bermasa → kick
   - To'g'ri javob → ruxsat
3. Welcome message (sozlanadigan)
```

---

## 7. 18+ aniqlash strategiyasi (matn asosida — birinchi versiya)

1. **Kalit so'zlar lug'ati** — `data/nsfw_keywords.txt` (uz/ru/en)
2. **Regex pattern'lari** — masalan `r"(18\+|porn|sex|xxx|adult|seks)"`
3. **Username pattern'lari** — `@*_18`, `@adult_*`, `@xxx*`
4. **Forward source** — agar kanal nomi/bio'da shubhali so'zlar bo'lsa
5. **Severity tizimi**:
   - 1-daraja (shubhali) → log + ogohlantirish
   - 2-daraja (aniq) → o'chirish + warning
   - 3-daraja (qattiq) → o'chirish + darhol ban

> Rasm/video uchun ML-asosli NSFW detection — keyingi fazada (NudeNet yoki OpenCV asosida)

---

## 8. Xavfsizlik va chegaralar

- Botni faqat **guruh adminlari** sozlay oladi (har bir komanda oldidan tekshiruv)
- Bot o'zi ban qilolmaydigan kishilarni (boshqa adminlar) tegmasligi
- Rate limiting: 1 admin 1 daqiqada 30+ komanda yubora olmaydi
- DB'da SQL injection'dan himoya (SQLAlchemy ORM)
- `.env` faylida BOT_TOKEN, DB credentials saqlanadi, git'ga tushmaydi
- Foydalanuvchi shaxsiy ma'lumotlari minimal saqlanadi (GDPR-friendly)

---

## 9. Ishlab chiqish bosqichlari (Phases)

### Faza 1 — Asos (1-hafta)
- [ ] Loyiha tuzilishi, virtualenv, requirements
- [ ] aiogram bot skeleton, `/start`, `/help`
- [ ] DB schema + Alembic migration
- [ ] Config + logging
- [ ] Botni guruhga qo'shish va admin tekshirish

### Faza 2 — Link filtri (2-hafta)
- [ ] `link_detector` service (regex + URL parsing)
- [ ] Whitelist/Blacklist CRUD
- [ ] `/whitelist`, `/blacklist` komandalari
- [ ] Avtomatik link o'chirish + log

### Faza 3 — 18+ filtri (3-hafta)
- [ ] `nsfw_detector` service
- [ ] Kalit so'zlar lug'atini to'plash
- [ ] Severity-based action
- [ ] Forward manbasini tekshirish

### Faza 4 — User boshqaruvi (4-hafta)
- [ ] CAPTCHA new member uchun
- [ ] Anti-flood middleware
- [ ] Warning → mute → ban tizimi
- [ ] Bot avto-ban (admin tasdiqlamasdan qo'shilgan)
- [ ] `/warn`, `/mute`, `/ban`, `/unban`

### Faza 5 — Admin paneli va stats (5-hafta)
- [ ] `/settings` inline menyu
- [ ] `/stats`, `/logs`
- [ ] Log kanalga ulanish
- [ ] Kunlik hisobot (APScheduler)

### Faza 6 — Deploy va polish (6-hafta)
- [ ] Docker + docker-compose
- [ ] VPS yoki Railway'ga deploy
- [ ] README, foydalanish qo'llanmasi
- [ ] Test guruhda sinov

### Faza 7 (keyinroq, opsional)
- [ ] Rasm/video NSFW detection (NudeNet)
- [ ] OCR — rasm ichidagi matnda link/reklama
- [ ] ML-based spam classifier (oddiy reklama vs normal xabar)
- [ ] Web dashboard (FastAPI) — admin uchun

---

## 10. Kerakli paketlar (`requirements.txt` boshlanishi)

```
aiogram==3.13.1
sqlalchemy[asyncio]==2.0.35
aiosqlite==0.20.0
asyncpg==0.29.0
alembic==1.13.3
pydantic-settings==2.5.2
loguru==0.7.2
redis==5.0.8
apscheduler==3.10.4
python-dotenv==1.0.1
```

---

## 11. Keyingi qadam

Reja tasdiqlangach, **Faza 1** dan boshlaymiz:
1. `requirements.txt`, `.env.example`, `.gitignore` yaratish
2. `bot/config.py`, `bot/main.py` — minimal ishlovchi bot
3. DB modellari va birinchi migration
4. `/start` komandasi ishlashini tekshirish

Tayyor bo'lsangiz, "boshla" deng — coding qismiga o'tamiz.
