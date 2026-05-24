"""Honeypot / "profil-bait" spam-bot aniqlash (matn asosida).

Kanal izoh (discussion) bo'limlarini bosadigan soxta akkauntlar uchun. Ular
havola yoki ochiq 18+ so'z ishlatmaydi — buning o'rniga odamni o'z profiliga
(rasm/havola) yoki shaxsiy yozishmaga jalb qiladi:

    "O'zimga yubka olmoqchi edim... haddan tashqari ochiq emasmi...
     Foto profilimda, halol fikring kerak 💞"

Strategiya: bir nechta "yumshoq" signal toifasini birlashtiramiz. Hech bir
toifa yolg'iz holda ban sababi bo'lmaydi — aynan kombinatsiya (ayniqsa
*profilga ishora* + yana bir signal) bu janrni haqiqiy suhbatdan ajratadi va
yolg'on ishlashni kamaytiradi.

Severity: 0 (toza) / 1 (shubhali, faqat log) / 3 (aniq bait → ban).
Dependency talab qilmaydi; uz (lotin) va ru tillarini qoplaydi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Signal toifalari ---
PROFILE_REF = "profile_ref"   # profilga / profil rasmiga ishora (asosiy "ilmoq")
DATING = "dating"             # tanishuv / yolg'izlik o'ljasi (asosiy "ilmoq")
DM_CTA = "dm_cta"             # shaxsiyga yozishga undash
OPINION = "opinion"           # "fikringizni / baho bering"
SUGGESTIVE = "suggestive"     # ochiq kiyim / tana / "juda ochiqmi"
EMOJI = "emoji"               # flirt emojilari

# Bir o'ljani anglatadigan toifalar (oddiy gap-so'zda kam uchraydi)
_ANCHORS = {PROFILE_REF, DATING, DM_CTA}

# Diagnostika uchun toifa og'irliklari (qaror toifalar to'plamiga asoslanadi)
_WEIGHTS = {
    PROFILE_REF: 0.5,
    DATING: 0.4,
    DM_CTA: 0.3,
    OPINION: 0.25,
    SUGGESTIVE: 0.25,
    EMOJI: 0.15,
}

# Normallashtirilgan (kichik harf, apostrof olib tashlangan, leet tozalangan)
# substringlar. Lotin uchun apostrofsiz yozamiz ("ko'ylak" -> "koylak").
_SIGNALS: dict[str, list[str]] = {
    PROFILE_REF: [
        # uz
        "profilimda", "profilimga", "profilimni", "profilim", "profilda",
        "profilga", "profildagi", "profilini", "profildan", "profimda",
        "foto profil", "profil foto", "profil rasm", "rasm profil",
        "rasmim profil", "profildagi rasm", "anketamda", "anketada", "anketam",
        "akkauntimda rasm", "avatarimda",
        # ru
        "в профиле", "фото в профиле", "профиле фото", "фото профиля",
        "в профайле", "профайле", "на аватарке", "аватарке", "в анкете",
        "анкете", "загляни в профиль", "смотри профиль", "зайди в профиль",
        "у меня в профиле", "профиль глянь", "глянь профиль",
        # ru lotin-translit
        "v profile", "v profil", "foto v profile", "na avatarke",
        "glyan profil", "zaydi v profil", "v ankete",
    ],
    DATING: [
        # uz
        "tanishaylik", "tanishamiz", "tanishuv", "tanishsak", "yolgizman",
        "yolgiz qoldim", "uyda yolgiz", "zerikdim", "zerikyapman",
        "sevgi izlayapman", "munosabat izlayapman", "juftlik izlayapman",
        "yaqinlashaylik", "yolgiz qizman",
        # ru
        "познакомимся", "познакомиться", "познакомлюсь", "давай познакомимся",
        "одна дома", "мне скучно", "скучно одной", "одинока", "ищу парня",
        "ищу мужчину", "для встреч", "ищу для встреч", "хочу пообщаться",
        # ru lotin-translit
        "poznakomimsya", "poznakomitsya", "davay poznakom", "odna doma",
        "skuchno odnoy", "mne skuchno", "ishu parnya", "dlya vstrech",
    ],
    DM_CTA: [
        # uz
        "lichkaga yoz", "lichkaga yozing", "lichkada yoz", "shaxsiyga yoz",
        "shaxsiyga yozing", "menga yozing", "menga yoz", "javob yozing",
        "yozib qoling",
        # ru
        "пиши в лс", "пиши в личку", "напиши в лс", "напиши в личку",
        "жду в личке", "пиши мне", "напиши мне", "в личку",
        # ru lotin-translit
        "pishi v lichku", "v lichku", "napishi mne", "pishi mne", "jdu v lichke",
    ],
    OPINION: [
        # uz
        "fikring kerak", "fikringiz kerak", "fikringizni", "fikr bildiring",
        "fikringiz qanday", "halol fikr", "rost fikr", "baho bering",
        "bahola", "yarashadimi", "yarashibdimi", "menga yarashadimi",
        "qanday korinadi", "tanladimmi", "maslahat bering", "maslahat kerak",
        # ru
        "честное мнение", "ваше мнение", "ваше честное мнение", "оцените",
        "как вам", "что скажете", "посоветуйте", "нужен совет", "как думаете",
        "мне идет", "мне идёт",
        # ru lotin-translit
        "chestnoe mnenie", "vashe mnenie", "ocenite", "mne idet",
    ],
    SUGGESTIVE: [
        # uz
        "juda ochiq", "ochiq emasmi", "ochiqmi", "haddan tashqari ochiq",
        "kalta yubka", "yubka", "koylak", "kombinezon", "kupalnik",
        "figuram", "tanim", "tanam", "badanim", "issiq rasm",
        # ru
        "слишком откровенно", "откровенно", "вырез", "коротк", "купальник",
        "фигур", "тело моё", "тело мое", "вульгарно", "пошло ли",
    ],
}

# Flirt emojilari (raw matnda tekshiriladi)
_FLIRTY_EMOJI = "💞💕❤🩷💗💓💖💘💝💋😘😍🥰😏🔥👅🍑🍒😈💦💃"

_APOSTROPHES = "'ʻ`´’ʼ‘"
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s"})
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Kichik harf + leet tozalash + apostrof olib tashlash + bo'sh joy siqish."""
    t = text.lower().translate(_LEET)
    for ch in _APOSTROPHES:
        t = t.replace(ch, "")
    return _WS_RE.sub(" ", t)


@dataclass
class BaitVerdict:
    """Bait tahlili natijasi."""

    severity: int = 0  # 0 = toza, 1 = shubhali (log), 3 = aniq bait (ban)
    categories: list[str] = field(default_factory=list)
    matches: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def is_flagged(self) -> bool:
        return self.severity > 0


def analyze(text: str | None) -> BaitVerdict:
    """Matnni tahlil qilib bait-verdict qaytaradi."""
    verdict = BaitVerdict()
    if not text:
        return verdict

    norm = _normalize(text)
    cats: set[str] = set()
    matches: list[str] = []

    for category, words in _SIGNALS.items():
        for w in words:
            if w in norm:
                cats.add(category)
                matches.append(w)
                break  # toifa uchun bitta hit yetarli

    if any(e in text for e in _FLIRTY_EMOJI):
        cats.add(EMOJI)
        matches.append("flirt-emoji")

    verdict.categories = sorted(cats)
    verdict.matches = matches
    verdict.score = round(min(sum(_WEIGHTS[c] for c in cats), 1.0), 2)

    # --- Qaror ---
    # Profilga ishora bu janrning "qotil" signali: u + yana bir signal => ban.
    # Tanishuv o'ljasi + aniq ilmoq (ochiq kiyim / shaxsiyga yoz / profil) => ban.
    profile_combo = PROFILE_REF in cats and (cats - {PROFILE_REF})
    dating_combo = DATING in cats and (cats & {SUGGESTIVE, DM_CTA, PROFILE_REF})

    if profile_combo or dating_combo:
        verdict.severity = 3
    elif (
        PROFILE_REF in cats
        or DATING in cats
        or (cats & _ANCHORS and len(cats) >= 2)
        or len(cats) >= 3
    ):
        verdict.severity = 1

    return verdict


def is_bait(text: str | None) -> bool:
    """Yuqori ishonchli bait bo'lsa True (ban darajasi)."""
    return analyze(text).severity >= 3
