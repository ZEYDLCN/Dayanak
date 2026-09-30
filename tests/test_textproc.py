from app.textproc import normalize, tokenize


def test_turkish_dotted_dotless_i():
    assert normalize("İADE") == "iade"
    assert normalize("IŞIK") == "isik"  # I -> ı -> i (katlanmış)


def test_diacritics_are_folded_so_ascii_queries_match():
    assert tokenize("iade süresi") == tokenize("iade suresi")


def test_stopwords_removed_but_numbers_kept():
    assert tokenize("Kaç gün ve 30 mi?") == ["gun", "30"]


def test_prefix_stemming_matches_inflections():
    assert tokenize("ayarlarına") == tokenize("ayarlar")
