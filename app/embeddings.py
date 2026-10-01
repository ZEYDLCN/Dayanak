"""Yerel (ağsız, API'siz) gömme modelleri ve bölüm gömmeleri için disk önbelleği.

Model, `fastembed` (ONNX, CPU) ile çalışır. Bölümler (~50 kısa metin) açılışta bir kez gömülür ve diske yazılır;
sorgu başına yalnızca tek bir kısa metin gömülür.
"""

import hashlib
import logging
from pathlib import Path
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)


class Embedder(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """(n, d) float32, satırlar L2-normalize."""

    def embed_query(self, text: str) -> np.ndarray:
        """(d,) float32, L2-normalize."""


def _normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(norm, 1e-12)


class FastEmbedder:
    """fastembed (ONNX) tabanlı çok dilli gömme. e5 ailesi için 'query:'/'passage:' önekleri fastembed tarafından eklenir."""

    def __init__(self, model_name: str, cache_dir: Path | None = None, threads: int | None = None):
        from fastembed import TextEmbedding  # tembel içe aktarma: BM25 modunda bağımlılık gerekmez

        self.name = model_name
        kwargs = {"cache_dir": str(cache_dir)} if cache_dir else {}
        if threads:
            kwargs["threads"] = threads
        self._model = TextEmbedding(model_name=model_name, **kwargs)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        fn = getattr(self._model, "passage_embed", self._model.embed)
        return _normalize(np.stack(list(fn(texts))))

    def embed_query(self, text: str) -> np.ndarray:
        fn = getattr(self._model, "query_embed", self._model.embed)
        return _normalize(np.asarray(next(iter(fn([text])))))


def cached_document_vectors(embedder: Embedder, texts: list[str], cache_dir: Path | None) -> np.ndarray:
    """Bölüm metinleri ve model adı aynıysa gömmeleri diskten okur."""
    if cache_dir is None:
        return embedder.embed_documents(texts)
    key = hashlib.sha1(("\n".join([embedder.name, *texts])).encode("utf-8")).hexdigest()[:20]
    path = cache_dir / "embeddings" / f"{key}.npy"
    if path.exists():
        try:
            return np.load(path)
        except Exception:  # bozuk önbellek: yeniden hesapla
            log.warning("gömme önbelleği okunamadı, yeniden hesaplanıyor: %s", path)
    vectors = embedder.embed_documents(texts)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, vectors)
    return vectors


def build_embedder(model_name: str, cache_dir: Path | None) -> Embedder | None:
    """Kurulamazsa (paket yok, model indirilemedi) None döner; çağıran BM25'e düşer."""
    try:
        return FastEmbedder(model_name, cache_dir=(cache_dir / "fastembed") if cache_dir else None)
    except Exception as exc:  # ImportError, ağ/disk hatası, bilinmeyen model
        log.warning("gömme modeli yüklenemedi (%s): %s — yalnızca BM25 kullanılacak", model_name, exc)
        return None
