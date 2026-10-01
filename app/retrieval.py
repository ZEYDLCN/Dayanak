import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from app.config import Settings
from app.index import BM25Index, Hit
from app.ingest import load_corpus
from app.versioning import ConflictReport, resolve_versions, strip_history_terms, wants_history

if TYPE_CHECKING:  # numpy/fastembed yalnizca hibrit modda gerekir; BM25 kurulumu bunlara baglanmaz
    from app.embeddings import Embedder
    from app.hybrid import HybridIndex

log = logging.getLogger(__name__)


@dataclass
class Retrieval:
    hits: list[Hit]  # yalnizca guncel surumler
    conflicts: list[ConflictReport]
    sufficient: bool  # skor VE kapsama esigi gecti (yuksek kesinlik; LLM'siz modda kapi budur)
    top_score: float
    top_coverage: float
    plausible: bool = False  # skor VEYA kapsama (VEYA anlamsal) esigi gecti (yuksek duyarlilik; LLM modunda kapi budur)
    top_semantic: float = 0.0


class KnowledgeBase:
    def __init__(self, settings: Settings, embedder: "Embedder | None" = None):
        self.settings = settings
        self.metas, self.chunks = load_corpus(settings.docs_dir)
        self.index = BM25Index(self.chunks)  # her zaman var: kapi, aciklanabilirlik ve yedek
        self.hybrid: "HybridIndex | None" = None
        if settings.retriever == "hybrid":
            try:
                from app.embeddings import build_embedder
                from app.hybrid import HybridIndex
            except ImportError as exc:  # numpy yok
                log.warning("hibrit arama icin gerekli paket yok (%s); BM25 ile devam ediliyor", exc)
            else:
                embedder = embedder or build_embedder(settings.embedding_model, settings.cache_dir)
                if embedder is not None:
                    self.hybrid = HybridIndex(self.index, embedder, settings.cache_dir, settings.rrf_k)
            if self.hybrid is None:
                log.warning("retriever=hybrid istendi ama gomme yok; BM25 ile devam ediliyor")

    @property
    def retriever_name(self) -> str:
        return f"hybrid({self.hybrid.embedder.name})" if self.hybrid else "bm25"

    def retrieve(self, question: str, as_of: date | None = None) -> Retrieval:
        s = self.settings
        as_of = as_of or date.today()
        # Eski surumler top-k'da yer kaplamasin diye sürüm çözümünden önce daha genis aday cek
        search_q = strip_history_terms(question) if wants_history(question, self.metas) else question
        index = self.hybrid or self.index
        raw = index.search(search_q, k=s.top_k * 2)
        resolution = resolve_versions(raw, self.metas, as_of)
        hits = resolution.hits[: s.top_k]

        if self.hybrid and hits:
            # Birlesik siralamada en ustteki bolum sozcuksel olarak zayif olabilir (anlamsal eslesme);
            # kapi icin sozcuk sinyalinin en iyisi kullanilir.
            top_score = max(h.score for h in hits)
            top_cov = max(h.coverage for h in hits)
            top_sem = max(h.semantic for h in hits)
        else:
            top_score = hits[0].score if hits else 0.0
            top_cov = hits[0].coverage if hits else 0.0
            top_sem = 0.0
        # Iki kapi: LLM yokken yanlis kabul pahali (bolumu cevap diye alintilariz) -> VE (yalnizca sozcuk).
        # LLM varken karari LLM verir, yanlis ret pahali (mesru soru "bilgi yok" olur) -> VEYA.
        sufficient = bool(hits) and top_score >= s.min_score and top_cov >= s.min_coverage
        plausible = bool(hits) and (
            top_score >= s.min_score
            or top_cov >= s.min_coverage
            or (s.min_semantic > 0 and top_sem >= s.min_semantic)
        )
        return Retrieval(hits, resolution.conflicts, sufficient, top_score, top_cov, plausible, top_sem)
