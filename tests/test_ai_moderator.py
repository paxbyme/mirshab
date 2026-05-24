"""ai_moderator uchun testlar (JSON parsing + mocklangan klient)."""

from types import SimpleNamespace

import pytest

from bot.services import ai_moderator


def test_parse_verdict_clean_json():
    v = ai_moderator._parse_verdict('{"is_scam": true, "confidence": 0.9, "reason": "profilga jalb"}')
    assert v is not None
    assert v.is_scam is True
    assert v.confidence == 0.9
    assert "profil" in v.reason


def test_parse_verdict_wrapped_in_text():
    raw = 'Mana natija:\n```json\n{"is_scam": false, "confidence": 0.1, "reason": "oddiy"}\n```'
    v = ai_moderator._parse_verdict(raw)
    assert v is not None
    assert v.is_scam is False


def test_parse_verdict_garbage_returns_none():
    assert ai_moderator._parse_verdict("javob yo'q") is None
    assert ai_moderator._parse_verdict("") is None


class _FakeMessages:
    def __init__(self, text):
        self._text = text

    async def create(self, **kwargs):
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self._text)]
        )


class _FakeOpts:
    def __init__(self, text):
        self.messages = _FakeMessages(text)


class _FakeClient:
    def __init__(self, text):
        self._text = text

    def with_options(self, **kwargs):
        return _FakeOpts(self._text)


@pytest.mark.asyncio
async def test_classify_lure_scam(monkeypatch):
    monkeypatch.setattr(
        ai_moderator, "_get_client",
        lambda: _FakeClient('{"is_scam": true, "confidence": 0.95, "reason": "profilga jalb"}'),
    )
    v = await ai_moderator.classify_lure(
        "Foto profilimda, halol fikring kerak", "bio havolalari: @scamchannel"
    )
    assert v is not None and v.is_scam is True


@pytest.mark.asyncio
async def test_classify_lure_clean(monkeypatch):
    monkeypatch.setattr(
        ai_moderator, "_get_client",
        lambda: _FakeClient('{"is_scam": false, "confidence": 0.05, "reason": "oddiy suhbat"}'),
    )
    v = await ai_moderator.classify_lure("Salom, qalaysiz?", "profil bo'sh")
    assert v is not None and v.is_scam is False


@pytest.mark.asyncio
async def test_classify_lure_no_client_returns_none(monkeypatch):
    # Kalit yo'q / SDK yo'q => fail-open (None), xabar o'chirilmaydi
    monkeypatch.setattr(ai_moderator, "_get_client", lambda: None)
    v = await ai_moderator.classify_lure("istalgan matn", "profil bo'sh")
    assert v is None
