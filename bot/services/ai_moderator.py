"""AI-asosli moderatsiya (Claude) — profilga jalb qiluvchi spam-botlarni aniqlash.

Heuristika hamma holatni tutmaydi (yangi shablonlar, tabiiy matn). Bu modul
xabar matnini + yuboruvchining bio/profil kanalini Claude'ga berib, "odamlarni
o'z profili / biosidagi havola / kanaliga jalb qilayotgan scam-mi?" deb baholaydi.

Graceful: SDK o'rnatilmagan yoki ANTHROPIC_API_KEY yo'q bo'lsa — `is_available()`
False qaytaradi va chaqiruvchi heuristikaga fallback qiladi. Tarmoq/limit xatosida
`classify_lure` None qaytaradi (fail-open — xato tufayli xabar o'chirilmaydi).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from bot.config import get_settings
from bot.utils.logger import logger

try:
    import anthropic
    from anthropic import AsyncAnthropic

    _SDK_AVAILABLE = True
except Exception:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]
    AsyncAnthropic = None  # type: ignore[assignment, misc]
    _SDK_AVAILABLE = False

_SYSTEM_PROMPT = (
    "Siz Telegram guruh/kanal-izoh moderatorisiz. Vazifangiz: yuborilgan xabar "
    "o'quvchilarni YUBORUVCHINING profiliga / bio'sidagi havolaga / shaxsiy "
    "kanaliga yoki shaxsiy yozishmaga jalb qilishga urinayotgan SPAM/SCAM ekanini "
    "aniqlash.\n\n"
    "Bu janrning tipik belgilari:\n"
    "- 'Foto profilimda', 'profilimga qarang', 'в профиле', 'anketamga qara' kabi "
    "profilga ishora;\n"
    "- 'halol fikr', 'baho bering', 'menga yozing', 'lichkaga', 'tanishaylik' kabi "
    "shaxsiyga/profilga undash;\n"
    "- soxta ayol/tanishuv/escort, tez boyish/investitsiya/kripto, 18+ kontent "
    "reklamasi;\n"
    "- yuboruvchining bio'sida yoki profil kanalida tashqi havola bo'lishi (kontekstda "
    "beriladi) — bu jalb qilinadigan manzil.\n\n"
    "QAT'IY KONSERVATIV bo'ling: oddiy suhbat, savol, hazil yoki bio'da havolasi bor "
    "lekin reklama qilmayotgan foydalanuvchi — scam EMAS. Faqat xabar aniq ravishda "
    "profilga/havolaga/shaxsiyga jalb qilishga qaratilgan bo'lsa scam deb belgilang.\n\n"
    "FAQAT quyidagi JSON formatida javob bering, boshqa hech narsa yozmang:\n"
    '{"is_scam": true|false, "confidence": 0.0-1.0, "reason": "qisqa sabab (o\'zbekcha)"}'
)


@dataclass
class AiVerdict:
    """AI tasnifi natijasi."""

    is_scam: bool
    confidence: float
    reason: str


_client: "AsyncAnthropic | None" = None
_client_tried = False


def is_available() -> bool:
    """SDK o'rnatilgan va kalit/yoqilgan bo'lsa True."""
    return _SDK_AVAILABLE and get_settings().use_ai_moderation


def _get_client() -> "AsyncAnthropic | None":
    global _client, _client_tried
    if _client_tried:
        return _client
    _client_tried = True
    if not is_available():
        return None
    try:
        _client = AsyncAnthropic(api_key=get_settings().anthropic_api_key)
        logger.info(f"AI moderator yoqildi (model={get_settings().ai_model})")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"AI moderator klientini yaratib bo'lmadi: {e}")
        _client = None
    return _client


def _parse_verdict(text: str) -> AiVerdict | None:
    """Model javobidan JSON verdictni ajratadi."""
    text = text.strip()
    # Ehtiyot uchun ```json ... ``` yoki atrofdagi matndan {...} ni ajratamiz
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return AiVerdict(
        is_scam=bool(data.get("is_scam")),
        confidence=float(data.get("confidence", 0.0) or 0.0),
        reason=str(data.get("reason", "") or "")[:200],
    )


async def classify_lure(
    message_text: str,
    profile_summary: str,
    *,
    heuristic_hint: str = "",
) -> AiVerdict | None:
    """Xabarni profilga-jalb scam uchun baholaydi.

    None => baholab bo'lmadi (SDK yo'q, kalit yo'q yoki xato) — chaqiruvchi
    bu holatda xabarni o'chirmasligi kerak (fail-open).
    """
    client = _get_client()
    if client is None:
        return None

    settings = get_settings()
    user_block = (
        f"Yuboruvchi profili: {profile_summary}\n"
        + (f"Heuristik signal: {heuristic_hint}\n" if heuristic_hint else "")
        + f"\nXabar matni:\n{message_text[:2000]}"
    )
    try:
        resp = await client.with_options(timeout=8.0, max_retries=1).messages.create(
            model=settings.ai_model,
            max_tokens=256,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_block}],
        )
    except Exception as e:  # noqa: BLE001  (tarmoq/limit/xato — fail-open)
        logger.warning(f"AI moderator chaqiruvi muvaffaqiyatsiz: {e}")
        return None

    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
    verdict = _parse_verdict(text)
    if verdict is None:
        logger.warning(f"AI moderator javobini o'qib bo'lmadi: {text[:120]!r}")
    return verdict
