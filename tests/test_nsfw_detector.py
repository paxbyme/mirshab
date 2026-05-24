"""nsfw_detector uchun testlar."""

from bot.services.nsfw_detector import NsfwDetector


def _det() -> NsfwDetector:
    # Faylga bog'liq bo'lmaslik uchun aniq lug'at beramiz
    return NsfwDetector(keywords={"porn": 3, "casino": 2, "nsfw": 1})


def test_clean_text():
    assert not _det().check_text("Salom, qalaysiz?").is_flagged


def test_detects_severity_3():
    v = _det().check_text("watch free PORN here")
    assert v.is_flagged and v.severity == 3


def test_detects_severity_2():
    v = _det().check_text("Best CASINO bonus")
    assert v.severity == 2


def test_leetspeak_normalization():
    # p0rn -> porn
    v = _det().check_text("p0rn link")
    assert v.severity == 3


def test_username_pattern():
    v = _det().check_username("@adult_videos")
    assert v.is_flagged and v.severity >= 2


def test_clean_username():
    assert not _det().check_username("@normal_user").is_flagged


def test_regex_signal_18plus():
    v = NsfwDetector(keywords={}).check_text("kontent 18+ shu yerda")
    assert v.severity >= 2
