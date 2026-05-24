"""profile_inspector uchun testlar (mocklangan get_chat)."""

from types import SimpleNamespace

import pytest

from bot.services import profile_inspector


class _FakeBot:
    def __init__(self, chat):
        self._chat = chat
        self.calls = 0

    async def get_chat(self, user_id):
        self.calls += 1
        if isinstance(self._chat, Exception):
            raise self._chat
        return self._chat


@pytest.fixture(autouse=True)
def _clear_cache():
    profile_inspector._cache.clear()
    yield
    profile_inspector._cache.clear()


@pytest.mark.asyncio
async def test_bio_link_is_target():
    chat = SimpleNamespace(bio="Yangi loyiham: t.me/mychannel", personal_chat=None)
    info = await profile_inspector.get_profile(_FakeBot(chat), 111)
    assert info.has_target
    assert info.bio_links


@pytest.mark.asyncio
async def test_personal_channel_is_target():
    personal = SimpleNamespace(username="myshop", title="My Shop")
    chat = SimpleNamespace(bio="", personal_chat=personal)
    info = await profile_inspector.get_profile(_FakeBot(chat), 222)
    assert info.has_target
    assert info.personal_channel == "@myshop"


@pytest.mark.asyncio
async def test_empty_profile_no_target():
    chat = SimpleNamespace(bio="oddiy foydalanuvchi", personal_chat=None)
    info = await profile_inspector.get_profile(_FakeBot(chat), 333)
    assert not info.has_target


@pytest.mark.asyncio
async def test_get_chat_failure_is_graceful():
    info = await profile_inspector.get_profile(_FakeBot(RuntimeError("privacy")), 444)
    assert not info.has_target
    assert info.bio == ""


@pytest.mark.asyncio
async def test_result_is_cached():
    chat = SimpleNamespace(bio="t.me/x", personal_chat=None)
    bot = _FakeBot(chat)
    await profile_inspector.get_profile(bot, 555)
    await profile_inspector.get_profile(bot, 555)
    assert bot.calls == 1  # ikkinchi marta keshdan
