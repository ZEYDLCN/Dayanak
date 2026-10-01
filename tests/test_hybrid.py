"""Hibrit arama (BM25 + gömme, RRF): model indirmeden, sahte gömmeyle test edilir."""

import hashlib

import pytest

np = pytest.importorskip("numpy", reason="hibrit arama istege bagli: pip install -r requirements-hybrid.txt")

from app.config import Settings  # noqa: E402
from app.embeddings import cached_document_vectors  # noqa: E402
from app.retrieval import KnowledgeBase  # noqa: E402


def _vec(key: str, dim: int = 64) -> np.ndarray:
    seed = int.from_bytes(hashlib.sha1(key.encode("utf-8")).digest()[:8], "big")
    v = np.random.default_rng(seed).normal(size=dim).astype(np.float32)
    return v / np.linalg.norm(v)


class StubEmbedder:
    """Her metin için deterministik rastgele vektör; sorgular istenen bölümün vektörüne eşlenebilir."""

    name = "stub"

    def __init__(self, query_to_chunk_text: dict[str, str] | None = None):
        self.mapping = query_to_chunk_text or {}
        self.doc_calls = 0

    def embed_documents(self, texts):
        self.doc_calls += 1
        return np.stack([_vec(t) for t in texts])

    def embed_query(self, text):
        return _vec(self.mapping.get(text, "sorgu:" + text))


def chunk_text(kb, chunk_id):
    return next(c for c in kb.chunks if c.chunk_id == chunk_id).index_text


def hybrid_settings(tmp_path, **kw):
    return Settings(_env_file=None, llm_provider="none", retriever="hybrid", cache_dir=tmp_path, **kw)


def test_bm25_is_the_default_and_hits_have_no_semantic_score(kb):
    assert kb.hybrid is None and kb.retriever_name == "bm25"
    assert all(h.semantic == 0.0 for h in kb.retrieve("İade süresi kaç gün?").hits)


def test_semantic_signal_rescues_a_chunk_that_bm25_ranks_low(kb, tmp_path):
    q = "İade için müşteri hizmetlerini telefonla arayabilir miyim?"
    bm25_rank = [h.chunk.chunk_id for h in kb.index.search(q, k=10)].index("iade-proseduru-v2#3")
    assert bm25_rank >= 1  # BM25 tek başına bu bölümü ilk sıraya koymuyor
    emb = StubEmbedder({q: chunk_text(kb, "iade-proseduru-v2#3")})
    hy = KnowledgeBase(hybrid_settings(tmp_path), embedder=emb)
    top = hy.retrieve(q).hits
    assert top[0].chunk.chunk_id == "iade-proseduru-v2#3"
    assert top[0].semantic > 0.99


class FlatEmbedder(StubEmbedder):
    """Bilgi taşımayan gömme: tüm metinler ve sorgu aynı vektör (anlamsal sıralama = bölüm sırası)."""

    def embed_documents(self, texts):
        self.doc_calls += 1
        return np.stack([_vec("sabit") for _ in texts])

    def embed_query(self, text):
        return _vec("sabit")


def test_lexical_signal_still_wins_when_embedding_is_uninformative(kb, tmp_path):
    hy = KnowledgeBase(hybrid_settings(tmp_path), embedder=FlatEmbedder())  # gömme hiçbir şey ayırt etmiyor
    hits = hy.retrieve("Hub 5 GHz Wi-Fi ağına bağlanır mı?").hits
    assert "kurulum-kilavuzu#3" in [h.chunk.chunk_id for h in hits[:2]]


def test_superseded_versions_never_survive_even_if_embedding_prefers_them(kb, tmp_path):
    q = "iade süresi"
    emb = StubEmbedder({q: chunk_text(kb, "iade-proseduru-v1#2")})  # eski sürümün bölümü
    hits = KnowledgeBase(hybrid_settings(tmp_path), embedder=emb).retrieve(q).hits
    assert hits and all(h.chunk.doc.doc_id != "iade-proseduru-v1" for h in hits)


def test_falls_back_to_bm25_when_embedding_model_cannot_load(tmp_path, monkeypatch):
    monkeypatch.setattr("app.embeddings.build_embedder", lambda *a, **k: None)
    hy = KnowledgeBase(hybrid_settings(tmp_path))
    assert hy.hybrid is None and hy.retriever_name == "bm25"
    assert hy.retrieve("İade süresi kaç gün?").sufficient


def test_semantic_gate_is_only_an_or_signal_and_never_loosens_the_strict_gate(kb, tmp_path):
    q = "How long does the reset link stay valid?"  # sözcüksel örtüşme yok (Türkçe korpus)
    emb = StubEmbedder({q: chunk_text(kb, "hesap-ve-sifre#3")})
    off = KnowledgeBase(hybrid_settings(tmp_path, min_semantic=0.0), embedder=emb).retrieve(q)
    on = KnowledgeBase(hybrid_settings(tmp_path, min_semantic=0.9), embedder=emb).retrieve(q)
    assert not off.plausible and on.plausible  # LLM'e gitmeye izin verir
    assert not on.sufficient  # LLM'siz (alıntılayan) modun sıkı kapısı yalnızca sözcüğe bakar


def test_document_vectors_are_cached_on_disk(tmp_path):
    emb = StubEmbedder()
    texts = ["bir", "iki", "üç"]
    a = cached_document_vectors(emb, texts, tmp_path)
    b = cached_document_vectors(emb, texts, tmp_path)
    assert emb.doc_calls == 1 and np.allclose(a, b)
    cached_document_vectors(emb, texts + ["dört"], tmp_path)  # metin değişti -> yeniden hesapla
    assert emb.doc_calls == 2
