def test_short_root_inflection_falls_back_to_indexed_prefix(kb):
    # "gündü" F5 ile "gundu" olur ve dizinde yoktur; dizindeki "gun" önekine düşmeli
    assert kb.index._backoff("gundu") == "gun"
    assert kb.index.search("iade süresi kaç gündü", k=1)[0].chunk.section == "İade Süresi"


def test_backoff_never_invents_terms_for_undocumented_topics(kb):
    # Dokümanda olmayan konular 'bilinmeyen' kalmalı ki cevapsız tespiti çalışsın
    for word in ("bluetooth", "taksit", "homekit", "fiyat", "watt"):
        stem = word[:5]
        assert stem not in kb.index._df
        assert kb.index._backoff(stem) == stem
