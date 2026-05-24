"""account_heuristics uchun testlar."""

from bot.services.account_heuristics import analyze_account


def test_flirty_emoji_name_is_suspicious():
    v = analyze_account("Anna 💋", "anna_official")
    assert v.is_suspicious
    assert "ismda flirt emoji" in v.signals


def test_suggestive_word_is_suspicious():
    v = analyze_account("Знакомства для встреч", None)
    assert v.is_suspicious


def test_plain_user_not_suspicious():
    v = analyze_account("Aziz Karimov", "aziz_k")
    assert not v.is_suspicious
    assert v.score == 0.0


def test_no_username_alone_not_suspicious():
    # Ko'p haqiqiy foydalanuvchida username yo'q — yolg'iz signal yetarli emas
    v = analyze_account("Dilshod", None)
    assert not v.is_suspicious
    assert "username yo'q" in v.signals


def test_trailing_digits_username():
    v = analyze_account("Lola", "lola_45219")
    assert "usernameda ketma-ket raqamlar" in v.signals


def test_score_capped():
    v = analyze_account("Sweet baby 💋😘", "intim_12345")
    assert v.score <= 1.0
    assert v.is_suspicious
