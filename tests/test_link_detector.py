"""link_detector uchun testlar."""

from bot.services.link_detector import LinkScan, extract_links, matches_patterns


def test_detects_http_url():
    scan = extract_links("Mana havola: https://example.com/page")
    assert "example.com" in scan.domains
    assert scan.has_any


def test_detects_bare_domain():
    scan = extract_links("example.uz saytiga kiring")
    assert "example.uz" in scan.domains


def test_detects_tme_and_username():
    scan = extract_links("Obuna: t.me/some_channel va @another_user")
    assert "some_channel" in scan.usernames
    assert "another_user" in scan.usernames


def test_detects_tg_scheme():
    scan = extract_links("tg://resolve?domain=hidden_chan")
    assert "hidden_chan" in scan.usernames


def test_clean_text_has_no_links():
    scan = extract_links("Bu oddiy xabar, hech qanday havola yo'q.")
    assert not scan.has_any


def test_www_normalized():
    scan = extract_links("www.Example.COM/path")
    assert "example.com" in scan.domains


def test_matches_domain_pattern_subdomain():
    scan = LinkScan(domains={"sub.example.com"})
    assert matches_patterns(scan, ["example.com"]) == "example.com"


def test_matches_username_pattern():
    scan = LinkScan(usernames={"spammer"})
    assert matches_patterns(scan, ["@spammer"]) == "@spammer"


def test_no_match_when_whitelisted_only():
    scan = LinkScan(domains={"telegram.org"})
    assert matches_patterns(scan, ["example.com"]) is None


def test_regex_pattern():
    scan = LinkScan(usernames={"adult_bot"})
    assert matches_patterns(scan, ["re:adult_.*"]) == "re:adult_.*"


# --- Mustahkamlash: de-obfuskatsiya ---


def test_deobf_bracket_dot():
    assert "example.com" in extract_links("kiring: example[.]com").domains


def test_deobf_word_dot():
    assert "example.com" in extract_links("example (dot) com ga o'ting").domains


def test_deobf_uzbek_nuqta():
    assert "kanal.uz" in extract_links("kanal nuqta uz").domains


def test_deobf_spaced_dot_both_sides():
    assert "example.com" in extract_links("manzil example . com").domains


def test_normal_punctuation_not_a_domain():
    # "rahmat. uz" (nuqtadan oldin bo'shliq yo'q) — domen DEB topilmasligi kerak
    scan = extract_links("Sizga rahmat. uz tilida yozing.")
    assert not scan.has_any


def test_sentence_no_false_positive():
    scan = extract_links("Keldim.Men ketdim. Yana keldim.")
    assert not scan.has_any


# --- Mustahkamlash: kengaytirilgan TLD'lar ---


def test_new_gtld_dev():
    assert "mysite.dev" in extract_links("https'siz: mysite.dev").domains


def test_cctld_kz():
    assert "shop.kz" in extract_links("buyurtma: shop.kz").domains


def test_unknown_tld_with_path_detected():
    # Noma'lum TLD, lekin /yo'l bor => ushlanadi
    assert extract_links("randomsite.foobar/promo123").has_any


def test_unknown_tld_without_path_ignored():
    # Noma'lum TLD, yo'lsiz => e'tiborga olinmaydi (FP'dan saqlanish)
    assert not extract_links("bu shunchaki matn.foobar").has_any
