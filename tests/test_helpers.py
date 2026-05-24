"""helpers uchun testlar."""

from bot.utils.helpers import human_duration, parse_duration


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
