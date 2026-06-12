from markwell.render import labels


def test_all_locales_share_exact_key_set():
    key_sets = {loc: set(d) for loc, d in labels.LABELS.items()}
    assert set(key_sets) == {"en", "zh-TW", "ja", "ko"}
    base = key_sets["en"]
    for loc, keys in key_sets.items():
        assert keys == base, f"{loc} drifted: {keys ^ base}"


def test_unknown_lang_falls_back_to_english():
    assert labels.for_lang("fr") == labels.LABELS["en"]
    assert labels.for_lang(None) == labels.LABELS["en"]


def test_chapter_line_per_locale():
    assert labels.chapter_line("en", 3) == "ch.3"
    assert labels.chapter_line("zh-TW", 3) == "第3章"
    assert labels.chapter_line("ja", 3) == "第3章"
    assert labels.chapter_line("ko", 3) == "3장"


def test_phrase_tables_cover_every_locale():
    # A locale added to LABELS but not the phrase tables would silently fall
    # back to English connectors — keep all four tables in lockstep.
    for table in (labels._NUM_GAP, labels._CHAPTER_LINE, labels._INDEX_TOTAL):
        assert set(table) == set(labels.LABELS)
