"""18+ / nomaqbul kontent aniqlash (matn asosida).

Strategiya: kalit so'zlar lug'ati + regex pattern + username pattern + forward manbasi.
Severity: 1 (shubhali) / 2 (aniq) / 3 (qattiq).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_KEYWORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "nsfw_keywords.txt"

# Shubhali username pattern'lari (severity 2)
_USERNAME_PATTERNS = [
    re.compile(r"^(?:adult|xxx|porn|sex|seks|porno|escort|nude|intim)[\w_]*$", re.I),
    re.compile(r"[\w_]*(?:_18|18plus|_xxx|_porn|_sex|porno)$", re.I),
    re.compile(r"^(?:onlyfans|camgirl|webcam)[\w_]*$", re.I),
]

# Regex signallari (so'z lug'atidan tashqari). (pattern, severity)
_REGEX_SIGNALS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\b18\s*\+", re.I), 2),
    (re.compile(r"\bxxx+\b", re.I), 3),
    (re.compile(r"п[оo]рн", re.I), 3),
]


@dataclass
class NsfwVerdict:
    """NSFW tahlil natijasi."""

    severity: int = 0  # 0 = toza
    matches: list[str] = field(default_factory=list)

    @property
    def is_flagged(self) -> bool:
        return self.severity > 0


def _normalize(text: str) -> str:
    """Kichik harf + ba'zi obfuskatsiyalarni tozalash (p0rn -> porn)."""
    text = text.lower()
    # leetspeak almashtirishlari
    trans = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s"})
    return text.translate(trans)


class NsfwDetector:
    """Kalit so'zlar lug'atini yuklab, matnni tahlil qiladi."""

    def __init__(self, keywords: dict[str, int] | None = None) -> None:
        # keyword (normallashtirilgan) -> severity
        self._keywords: dict[str, int] = keywords or {}
        if not self._keywords:
            self._load_from_file()

    def _load_from_file(self) -> None:
        if not _KEYWORDS_FILE.exists():
            return
        for raw in _KEYWORDS_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            word = parts[0]
            severity = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 2
            if word:
                self._keywords[_normalize(word)] = severity

    def add_keyword(self, word: str, severity: int = 2) -> None:
        self._keywords[_normalize(word)] = severity

    def load_db_keywords(self, items: list[tuple[str, int]]) -> None:
        """DB'dan qo'shimcha kalit so'zlarni qo'shadi."""
        for word, severity in items:
            self.add_keyword(word, severity)

    def check_text(self, text: str | None) -> NsfwVerdict:
        verdict = NsfwVerdict()
        if not text:
            return verdict
        norm = _normalize(text)

        for word, severity in self._keywords.items():
            if word in norm:
                verdict.matches.append(word)
                verdict.severity = max(verdict.severity, severity)

        for pattern, severity in _REGEX_SIGNALS:
            if pattern.search(text):
                verdict.matches.append(pattern.pattern)
                verdict.severity = max(verdict.severity, severity)

        return verdict

    def check_username(self, username: str | None) -> NsfwVerdict:
        verdict = NsfwVerdict()
        if not username:
            return verdict
        uname = username.lstrip("@")
        for pattern in _USERNAME_PATTERNS:
            if pattern.match(uname):
                verdict.matches.append(f"username:@{uname}")
                verdict.severity = max(verdict.severity, 2)
                break
        # Username ichida ham so'z lug'atini tekshiramiz
        text_verdict = self.check_text(uname.replace("_", " "))
        if text_verdict.is_flagged:
            verdict.matches.extend(text_verdict.matches)
            verdict.severity = max(verdict.severity, text_verdict.severity)
        return verdict

    def check_forward(self, chat_title: str | None, chat_username: str | None) -> NsfwVerdict:
        """Forward qilingan kanal nomi/username'ini tekshiradi."""
        verdict = NsfwVerdict()
        for piece in (chat_title, chat_username):
            sub = self.check_text(piece)
            if sub.is_flagged:
                verdict.matches.extend(sub.matches)
                verdict.severity = max(verdict.severity, sub.severity)
        uname_verdict = self.check_username(chat_username)
        if uname_verdict.is_flagged:
            verdict.matches.extend(uname_verdict.matches)
            verdict.severity = max(verdict.severity, uname_verdict.severity)
        return verdict


# Modul darajasidagi yagona nusxa (lug'at fayldan bir marta yuklanadi)
_default_detector: NsfwDetector | None = None


def get_detector() -> NsfwDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = NsfwDetector()
    return _default_detector
