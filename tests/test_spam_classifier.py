"""spam_classifier (heuristik) uchun testlar."""

from bot.services.spam_classifier import heuristic_score, is_spam


def test_clean_message_low_score():
    assert heuristic_score("Salom, bugun ob-havo qanday?") < 0.3


def test_spam_phrases_raise_score():
    text = "🔥🔥🔥 TEZDA BOYISH! Promokod bilan chegirma! +998901234567"
    assert heuristic_score(text) >= 0.5


def test_is_spam_threshold():
    assert is_spam("заработок инвестиции промокод скидка", threshold=0.5)
    assert not is_spam("oddiy suhbat", threshold=0.5)
