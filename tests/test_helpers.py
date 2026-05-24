"""helpers uchun testlar."""

from bot.utils.helpers import human_duration, normalize_channel_id, parse_duration


def test_parse_plain_number_is_minutes():
    assert parse_duration("30") == 30 * 60


def test_parse_minutes():
    assert parse_duration("10m") == 600


def test_parse_hours():
    assert parse_duration("2h") == 7200


def test_parse_days():
    assert parse_duration("1d") == 86400


def test_parse_none():
    assert parse_duration(None) is None
    assert parse_duration("") is None


def test_human_duration():
    assert human_duration(None) == "cheksiz"
    assert human_duration(0) == "cheksiz"
    assert "1 soat" in human_duration(3600)
    assert "1 kun" in human_duration(86400)


def test_normalize_channel_id_adds_prefix_to_bare_positive():
    # Prefikssiz musbat ID -> -100... ("chat not found" xatosining sababi)
    assert normalize_channel_id(3911652365) == -1003911652365
    assert normalize_channel_id("3911652365") == -1003911652365


def test_normalize_channel_id_keeps_valid_negative():
    assert normalize_channel_id(-1002122896152) == -1002122896152
    assert normalize_channel_id("-1002122896152") == -1002122896152
    assert normalize_channel_id(-4012345678) == -4012345678  # eski guruh ID


def test_normalize_channel_id_username_and_links():
    assert normalize_channel_id("@kanal") == "@kanal"
    assert normalize_channel_id("https://t.me/kanal") == "@kanal"
    assert normalize_channel_id("t.me/kanal/") == "@kanal"


def test_normalize_channel_id_invalid_returns_none():
    assert normalize_channel_id(None) is None
    assert normalize_channel_id("") is None
    assert normalize_channel_id("abc") is None
    assert normalize_channel_id(0) is None
