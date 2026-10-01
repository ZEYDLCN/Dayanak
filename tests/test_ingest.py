import pytest

from app.ingest import DocumentError, load_corpus


def write(dir_, name, **fm):
    front = {"doc_id": name, "family": name, "title": name, "version": 1,
             "status": "current", "effective_date": "2024-01-01", **fm}
    lines = "\n".join(f"{k}: {v}" for k, v in front.items() if v is not None)
    (dir_ / f"{name}.md").write_text(f"---\n{lines}\n---\n\n# T\n\n## Bölüm\nMetin.\n", encoding="utf-8")


def test_real_corpus_has_expected_shape(kb):
    assert 8 <= len(kb.metas) <= 10
    assert {m.family for m in kb.metas if m.version > 1} == {"iade-proseduru"}
    assert all(c.text and c.section for c in kb.chunks)


def test_missing_front_matter_field(tmp_path):
    (tmp_path / "a.md").write_text("---\ndoc_id: a\n---\nx", encoding="utf-8")
    with pytest.raises(DocumentError, match="eksik alanlar"):
        load_corpus(tmp_path)


def test_duplicate_doc_id(tmp_path):
    write(tmp_path, "a")
    (tmp_path / "b.md").write_text((tmp_path / "a.md").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(DocumentError, match="tekrar eden"):
        load_corpus(tmp_path)


def test_status_must_match_version_order(tmp_path):
    write(tmp_path, "v1", family="f", version=1, status="current")
    write(tmp_path, "v2", family="f", version=2, status="current")
    with pytest.raises(DocumentError, match="status"):
        load_corpus(tmp_path)


def test_unknown_supersedes(tmp_path):
    write(tmp_path, "a", supersedes="yok")
    with pytest.raises(DocumentError, match="supersedes"):
        load_corpus(tmp_path)


def test_tags_are_search_only(tmp_path):
    write(tmp_path, "a")
    (tmp_path / "etiketler.yaml").write_text("a:\n  Bölüm: [kutudan ne çıkıyor, paket]\n", encoding="utf-8")
    _, chunks = load_corpus(tmp_path)
    c = chunks[0]
    assert c.tags == "kutudan ne çıkıyor paket"
    assert "kutudan" in c.index_text and "kutudan" not in c.text  # aranır ama metne/kanıta girmez


def test_tags_unknown_section_is_error(tmp_path):
    write(tmp_path, "a")
    (tmp_path / "etiketler.yaml").write_text("a:\n  Yok: [x]\n", encoding="utf-8")
    with pytest.raises(DocumentError, match="bilinmeyen bolum"):
        load_corpus(tmp_path)


def test_tags_must_be_list_of_strings(tmp_path):
    write(tmp_path, "a")
    (tmp_path / "etiketler.yaml").write_text("a:\n  Bölüm: düz metin\n", encoding="utf-8")
    with pytest.raises(DocumentError, match="liste"):
        load_corpus(tmp_path)


def test_real_corpus_tags_never_leak_into_text(kb):
    for c in kb.chunks:
        assert c.tags not in c.text or not c.tags
