"""Faza 7 — opsional rasm-asosli aniqlash (NSFW ML + OCR).

Bu modul og'ir paketlarga (nudenet, pytesseract, pillow) tayanadi.
Ular o'rnatilmagan bo'lsa — barcha funksiyalar xavfsiz tarzda None qaytaradi
va bot link/matn moderatsiyasini davom ettiraveradi.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from aiogram.types import Message

from bot.config import get_settings
from bot.utils.logger import logger

# --- Opsional paketlarni aniqlash (import qilmasdan) ---
try:  # NudeNet
    from nudenet import NudeDetector  # type: ignore

    _NUDE_AVAILABLE = True
except Exception:  # pragma: no cover
    NudeDetector = None  # type: ignore[assignment, misc]
    _NUDE_AVAILABLE = False

try:  # OCR
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore

    _OCR_AVAILABLE = True
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment, misc]
    _OCR_AVAILABLE = False


@dataclass
class MediaVerdict:
    severity: int = 0
    reason: str = ""
    matches: list[str] = field(default_factory=list)

    @property
    def is_flagged(self) -> bool:
        return self.severity > 0


# NudeNet detektori (bir marta yaratiladi — model yuklanadi)
_nude_detector = None
# Xavfli deb hisoblanadigan NudeNet teglari
_UNSAFE_LABELS = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
}


def features_status() -> dict[str, bool]:
    """Diagnostika uchun: qaysi opsional imkoniyatlar mavjud."""
    return {"image_nsfw": _NUDE_AVAILABLE, "ocr": _OCR_AVAILABLE}


def _get_nude_detector():
    global _nude_detector
    if _nude_detector is None and _NUDE_AVAILABLE:
        _nude_detector = NudeDetector()
    return _nude_detector


async def _download_photo(message: Message) -> Path | None:
    """Eng katta rasmni vaqtinchalik faylga yuklab oladi."""
    if message.bot is None:
        return None
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.sticker and not message.sticker.is_animated:
        file_id = message.sticker.file_id
    if file_id is None:
        return None
    try:
        tg_file = await message.bot.get_file(file_id)
        tmp = Path(tempfile.gettempdir()) / f"qoriqchi_{file_id}.jpg"
        await message.bot.download_file(tg_file.file_path, destination=tmp)
        return tmp
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Rasmni yuklab bo'lmadi: {e}")
        return None


def _check_image_nsfw(path: Path) -> MediaVerdict:
    detector = _get_nude_detector()
    if detector is None:
        return MediaVerdict()
    try:
        detections = detector.detect(str(path))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"NudeNet xatosi: {e}")
        return MediaVerdict()
    hits = [
        d["class"]
        for d in detections
        if d.get("class") in _UNSAFE_LABELS and d.get("score", 0) >= 0.5
    ]
    if hits:
        return MediaVerdict(
            severity=3, reason="rasm NSFW (NudeNet)", matches=hits
        )
    return MediaVerdict()


def _ocr_text(path: Path) -> str:
    if not _OCR_AVAILABLE:
        return ""
    try:
        return pytesseract.image_to_string(Image.open(path))  # type: ignore[union-attr]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"OCR xatosi: {e}")
        return ""


async def scan_media(message: Message, group_settings: dict) -> MediaVerdict | None:
    """Rasm/sticker'ni NSFW va (OCR orqali) matn uchun tekshiradi.

    Hech narsa topilmasa yoki imkoniyat o'chiq bo'lsa — None.
    """
    settings = get_settings()
    want_nsfw = group_settings.get("image_nsfw_on") and settings.image_nsfw_enabled
    want_ocr = group_settings.get("ocr_on") and settings.ocr_enabled
    if not (want_nsfw or want_ocr):
        return None
    if not (message.photo or message.sticker):
        return None

    path = await _download_photo(message)
    if path is None:
        return None

    try:
        if want_nsfw and _NUDE_AVAILABLE:
            verdict = _check_image_nsfw(path)
            if verdict.is_flagged:
                return verdict

        if want_ocr and _OCR_AVAILABLE:
            text = _ocr_text(path)
            if text.strip():
                # OCR matnini matn detektorlari bilan tekshiramiz
                from bot.services.link_detector import extract_links
                from bot.services.nsfw_detector import get_detector

                nsfw = get_detector().check_text(text)
                if nsfw.severity >= 2:
                    return MediaVerdict(
                        severity=nsfw.severity,
                        reason=f"rasm ichidagi 18+ matn (OCR): {', '.join(nsfw.matches[:3])}",
                        matches=nsfw.matches,
                    )
                if extract_links(text).has_any:
                    return MediaVerdict(
                        severity=2, reason="rasm ichidagi havola (OCR)"
                    )
        return None
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
