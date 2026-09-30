from datetime import date

from app.versioning import current_docs, resolve_versions


def test_latest_version_is_current(kb):
    cur = current_docs(kb.metas, date(2026, 1, 1))
    assert cur["iade-proseduru"].doc_id == "iade-proseduru-v2"


def test_future_dated_version_is_not_in_force(kb):
    cur = current_docs(kb.metas, date(2024, 6, 1))  # v2 (2025-01-15) henüz yürürlükte değil
    assert cur["iade-proseduru"].doc_id == "iade-proseduru-v1"


def test_superseded_chunks_never_survive_resolution(kb):
    hits = kb.index.search("iade süresi kaç gün", k=10)
    assert {h.chunk.doc.doc_id for h in hits} >= {"iade-proseduru-v1", "iade-proseduru-v2"}
    res = resolve_versions(hits, kb.metas, date(2026, 1, 1))
    assert all(h.chunk.doc.doc_id != "iade-proseduru-v1" for h in res.hits)
    assert res.conflicts and res.conflicts[0].selected_doc_id == "iade-proseduru-v2"
    assert "v2" in res.conflicts[0].reason


def test_no_conflict_for_unversioned_docs(kb):
    hits = kb.index.search("wi-fi 5 ghz", k=5)
    assert resolve_versions(hits, kb.metas, date(2026, 1, 1)).conflicts == []
