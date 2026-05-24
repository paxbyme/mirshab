"""bait_detector uchun testlar."""

from bot.services.bait_detector import analyze, is_bait


def test_screenshot_uz_bait_is_banned():
    text = (
        "O'zimga yubka olmoqchi edim, lekin endi o'ylab qoldim — haddan tashqari "
        "ochiq emasmi... Foto profilimda, halol fikring kerak 💞"
    )
    v = analyze(text)
    assert v.severity == 3
    assert "profile_ref" in v.categories
    assert is_bait(text)


def test_russian_profile_bait_is_banned():
    text = "Хочу узнать ваше честное мнение, фото в профиле 💕"
    v = analyze(text)
    assert v.severity == 3
    assert {"profile_ref", "opinion"} <= set(v.categories)


def test_dating_with_lure_is_banned():
    text = "Yolg'izman, zerikdim... juda ochiq kiyimdaman, lichkaga yozing 😘"
    assert analyze(text).severity == 3


def test_clean_message_not_flagged():
    assert analyze("Salom, bugun ob-havo qanday?").severity == 0


def test_single_suggestive_not_banned():
    # Profilga ishora yo'q — bitta yumshoq signal ban sababi emas
    v = analyze("Yangi ko'ylak oldim, sizningcha ochiqmi?")
    assert v.severity < 3


def test_opinion_only_not_flagged():
    assert analyze("Iltimos, fikringizni bildiring").severity == 0


def test_profile_ref_only_is_borderline_not_ban():
    v = analyze("Profilimda yangi rasm bor")
    assert v.severity == 1  # log, lekin ban emas


def test_empty_text():
    assert analyze("").severity == 0
    assert analyze(None).severity == 0
