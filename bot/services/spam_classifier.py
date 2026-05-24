"""Faza 7 — oddiy spam (reklama) klassifikatori.

Ikki rejim:
  1) Heuristik skorlash (har doim mavjud, dependency talab qilmaydi).
  2) scikit-learn modeli (agar `bot/data/spam_model.joblib` mavjud bo'lsa).

Yolg'on ishlashni kamaytirish uchun konservativ — yuqori ishonchda faqat
'shubhali' (severity 1) deb belgilaydi.
"""

from __future__ import annotations

import re
from pathlib import Path

from bot.utils.logger import logger

_MODEL_PATH = Path(__file__).resolve().parent.parent / "data" / "spam_model.joblib"

# Tez-tez uchraydigan reklama/spam iboralari (uz/ru/en)
_SPAM_PHRASES = [
    "tezda boyish", "pul ishlash", "investitsiya", "promokod", "chegirma",
    "заработок", "инвестиции", "промокод", "скидка", "розыгрыш", "бесплатно",
    "earn money", "make money", "free crypto", "giveaway", "limited offer",
    "подпишись", "obuna bo'ling", "kanalga o'ting", "perehodi",
]
_PHONE_RE = re.compile(r"(?:\+?\d[\s\-]?){9,}")
_EMOJI_RUN_RE = re.compile(r"[\U0001F000-\U0001FAFF☀-➿]{4,}")

_sklearn_model = None
_sklearn_tried = False


def _load_sklearn_model():
    global _sklearn_model, _sklearn_tried
    if _sklearn_tried:
        return _sklearn_model
    _sklearn_tried = True
    if not _MODEL_PATH.exists():
        return None
    try:
        import joblib  # type: ignore

        _sklearn_model = joblib.load(_MODEL_PATH)
        logger.info("Spam modeli yuklandi (scikit-learn)")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Spam modelini yuklab bo'lmadi: {e}")
        _sklearn_model = None
    return _sklearn_model


def heuristic_score(text: str) -> float:
    """0.0–1.0 oralig'ida spam ehtimoli (heuristik)."""
    if not text:
        return 0.0
    t = text.lower()
    score = 0.0

    # Reklama iboralari
    hits = sum(1 for p in _SPAM_PHRASES if p in t)
    score += min(hits * 0.25, 0.6)

    # Katta harflar nisbati
    letters = [c for c in text if c.isalpha()]
    if letters:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if caps_ratio > 0.6 and len(letters) > 10:
            score += 0.2

    # Telefon raqami
    if _PHONE_RE.search(text):
        score += 0.2

    # Ketma-ket ko'p emoji
    if _EMOJI_RUN_RE.search(text):
        score += 0.15

    # Juda ko'p takroriy belgilar (!!!!!, $$$$)
    if re.search(r"(.)\1{4,}", text):
        score += 0.1

    return min(score, 1.0)


def classify(text: str) -> float:
    """Spam ehtimolini qaytaradi (model bor bo'lsa undan, aks holda heuristik)."""
    model = _load_sklearn_model()
    if model is not None:
        try:
            proba = model.predict_proba([text])[0]
            # 'spam' sinfi indeksini topishga urinish
            classes = list(getattr(model, "classes_", [0, 1]))
            idx = classes.index(1) if 1 in classes else len(proba) - 1
            return float(proba[idx])
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Spam model xatosi, heuristikaga o'tildi: {e}")
    return heuristic_score(text)


def is_spam(text: str, threshold: float = 0.7) -> bool:
    return classify(text) >= threshold
