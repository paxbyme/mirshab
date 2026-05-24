"""Havola aniqlash: URL, t.me/, @username, tg:// va domen ajratish.

Mustahkamlangan: de-obfuskatsiya (`[.]`, `(dot)`, bo'shliqli nuqtalar), keng TLD
ro'yxati + yo'l-signalli umumiy domen, inline tugma URL'lari.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from aiogram.types import InlineKeyboardMarkup, Message

# Keng tarqalgan TLD'lar (gTLD + ccTLD). Yangi/noma'lum TLD'lar yo'l-signali
# orqali (pastdagi _PATH_DOMAIN_RE) ushlanadi.
_TLDS = frozenset(
    """
    com net org info biz name pro mobi asia tel
    app dev page web site online store shop club xyz top vip win bet cam fun
    live news blog tech space world icu cyou link click buzz rest bond sbs cfd
    io ai co me tv cc to ws gg sh fm so id pw
    us uk ca au de fr es it nl ru ua by kz kg uz tj tm az ge am tr ir cn jp kr
    in pk my sg th vn ph br mx ar cl pe pl cz sk ro bg gr pt se no fi dk ee lv
    lt hu at ch be ie il sa ae eg ng za ke рф
    """.split()
)
# Uzunroq TLD'lar oldinda turishi shart (com'ni co'dan oldin tekshirish uchun)
_TLD_ALT = "|".join(sorted(_TLDS, key=len, reverse=True))

_DOMAIN_LABEL = r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"

# http(s):// yoki www. bilan boshlanadigan URL'lar
_URL_RE = re.compile(r"(?:(?:https?://)|(?:www\.))[^\s<>\"']+", re.IGNORECASE)
# t.me/kanal, telegram.me/, telegram.dog/
_TME_RE = re.compile(
    r"(?:https?://)?(?:t(?:elegram)?\.(?:me|dog))/(?P<name>[a-zA-Z0-9_+/]+)",
    re.IGNORECASE,
)
# @username (Telegram qoidasi: kamida 5 belgi)
_MENTION_RE = re.compile(r"(?<![\w@])@([a-zA-Z][a-zA-Z0-9_]{4,31})")
# tg://resolve?domain=...
_TG_SCHEME_RE = re.compile(r"tg://[^\s<>\"']+", re.IGNORECASE)
# Ma'lum TLD'li yalang'och domen (yo'l ixtiyoriy)
_KNOWN_TLD_RE = re.compile(
    r"(?<![@/\w.])(" + _DOMAIN_LABEL + r"(?:" + _TLD_ALT + r"))(?![a-z0-9-])"
    r"(?:/[^\s<>\"']*)?",
    re.IGNORECASE,
)
# Noma'lum TLD, lekin /yo'l bor => kuchli URL signali (FP'ni kamaytiradi)
_PATH_DOMAIN_RE = re.compile(
    r"(?<![@/\w.])(" + _DOMAIN_LABEL + r"[a-z]{2,24})(/[^\s<>\"']+)",
    re.IGNORECASE,
)

# --- De-obfuskatsiya pattern'lari ---
_OBF_BRACKET_DOT = re.compile(r"[\[\(\{]\s*\.\s*[\]\)\}]")  # [.] (.) {.}
_OBF_WORD_DOT = re.compile(
    r"(?<=\w)\s*[\(\[\{<]?\s*(?:dot|nuqta|nukta|to'?chka|точка|тчк)\s*[\)\]\}>]?\s*(?=\w)",
    re.IGNORECASE,
)
_OBF_SPACED_DOT = re.compile(r"(?<=\w)\s+\.\s+(?=\w)")  # "example . com" (ikki tomon bo'sh)


def _deobfuscate(text: str) -> str:
    """Atayin yashirilgan domenlarni normal ko'rinishga keltiradi."""
    t = _OBF_BRACKET_DOT.sub(".", text)
    t = _OBF_WORD_DOT.sub(".", t)
    t = _OBF_SPACED_DOT.sub(".", t)
    return t


@dataclass
class LinkScan:
    """Xabardagi havolalar tahlili natijasi."""

    urls: list[str] = field(default_factory=list)
    domains: set[str] = field(default_factory=set)
    usernames: set[str] = field(default_factory=set)  # @siz, kichik harfda

    @property
    def has_any(self) -> bool:
        return bool(self.urls or self.usernames)


def _normalize_domain(host: str) -> str:
    host = host.lower().strip().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def _scan_into(text: str, scan: LinkScan) -> None:
    """Bir matn bo'lagini tahlil qilib, natijani `scan`ga qo'shadi."""
    if not text:
        return

    # 1) tg:// sxemasi
    for m in _TG_SCHEME_RE.finditer(text):
        url = m.group(0)
        scan.urls.append(url)
        dm = re.search(r"domain=([a-zA-Z0-9_]+)", url)
        if dm:
            scan.usernames.add(dm.group(1).lower())

    # 2) t.me/ havolalari
    for m in _TME_RE.finditer(text):
        scan.urls.append(m.group(0))
        name = m.group("name").split("/")[0].lstrip("+")
        if name:
            scan.usernames.add(name.lower())
        scan.domains.add("t.me")

    # 3) Oddiy http(s)/www URL'lar
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(".,);!?")
        scan.urls.append(url)
        parsed = urlparse(url if "://" in url else f"http://{url}")
        if parsed.hostname:
            scan.domains.add(_normalize_domain(parsed.hostname))

    # 4) Yalang'och domenlar — ma'lum TLD
    for m in _KNOWN_TLD_RE.finditer(text):
        scan.domains.add(_normalize_domain(m.group(1)))
        scan.urls.append(m.group(0))

    # 5) Noma'lum TLD, lekin /yo'l bilan
    for m in _PATH_DOMAIN_RE.finditer(text):
        scan.domains.add(_normalize_domain(m.group(1)))
        scan.urls.append(m.group(0))

    # 6) @username mention'lar
    for m in _MENTION_RE.finditer(text):
        scan.usernames.add(m.group(1).lower())


def extract_links(text: str) -> LinkScan:
    """Matndan barcha havola turlarini ajratib oladi (de-obfuskatsiya bilan)."""
    scan = LinkScan()
    if not text:
        return scan

    _scan_into(text, scan)
    # Yashirilgan ko'rinishni ham tekshiramiz (faqat farq bo'lsa)
    deobf = _deobfuscate(text)
    if deobf != text:
        _scan_into(deobf, scan)

    # URL takrorlarini olib tashlash (tartibni saqlab)
    seen: set[str] = set()
    scan.urls = [u for u in scan.urls if not (u in seen or seen.add(u))]
    return scan


def scan_message(message: Message) -> LinkScan:
    """Xabar matni + caption + entity + inline tugmalardan havolalarni yig'adi."""
    parts: list[str] = []
    if message.text:
        parts.append(message.text)
    if message.caption:
        parts.append(message.caption)

    scan = extract_links("\n".join(parts))

    # Entity'lardagi yashirin URL'lar (matn ko'rinmaydigan linklar)
    for entity in list(message.entities or []) + list(message.caption_entities or []):
        if entity.type == "text_link" and entity.url:
            scan.urls.append(entity.url)
            parsed = urlparse(entity.url)
            if parsed.hostname:
                scan.domains.add(_normalize_domain(parsed.hostname))
        elif entity.type == "url":
            base = message.text or message.caption or ""
            raw = base[entity.offset : entity.offset + entity.length]
            sub = extract_links(raw)
            scan.urls.extend(sub.urls)
            scan.domains |= sub.domains
            scan.usernames |= sub.usernames

    # Inline tugmalardagi URL'lar (masalan forward qilingan reklama xabari)
    markup = message.reply_markup
    if isinstance(markup, InlineKeyboardMarkup):
        for row in markup.inline_keyboard:
            for btn in row:
                url = btn.url or (btn.login_url.url if btn.login_url else None)
                if not url:
                    continue
                scan.urls.append(url)
                if url.startswith("tg://"):
                    dm = re.search(r"domain=([a-zA-Z0-9_]+)", url)
                    if dm:
                        scan.usernames.add(dm.group(1).lower())
                else:
                    parsed = urlparse(url)
                    if parsed.hostname:
                        scan.domains.add(_normalize_domain(parsed.hostname))

    seen: set[str] = set()
    scan.urls = [u for u in scan.urls if not (u in seen or seen.add(u))]
    return scan


def _domain_matches(domain: str, pattern: str) -> bool:
    """example.com pattern'i sub.example.com'ga ham mos keladi."""
    domain = domain.lower()
    pattern = pattern.lower().lstrip("*.")
    return domain == pattern or domain.endswith("." + pattern)


def matches_patterns(scan: LinkScan, patterns: list[str]) -> str | None:
    """Scan ichidagi biror element pattern'lardan biriga mos kelsa — o'shani qaytaradi.

    Pattern domen, @siz username yoki regex (`re:` prefiks bilan) bo'lishi mumkin.
    """
    for pattern in patterns:
        p = pattern.strip().lower()
        if not p:
            continue
        if p.startswith("re:"):
            try:
                rx = re.compile(p[3:], re.IGNORECASE)
            except re.error:
                continue
            for value in list(scan.domains) + list(scan.usernames) + scan.urls:
                if rx.search(value):
                    return pattern
            continue

        plain = p.lstrip("@")
        # Domen mosligi
        for domain in scan.domains:
            if _domain_matches(domain, plain):
                return pattern
        # Username mosligi
        if plain in scan.usernames:
            return pattern
        # URL ichida xom moslik
        for url in scan.urls:
            if plain in url.lower():
                return pattern
    return None
