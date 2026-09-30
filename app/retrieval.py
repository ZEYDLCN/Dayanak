from dataclasses import dataclass
from datetime import date

from app.config import Settings
from app.index import BM25Index, Hit
from app.ingest import load_corpus
from app.versioning import ConflictReport, resolve_versions


@dataclass
class Retrieval:
    hits: list[Hit]  # yalnizca guncel surumler
    conflicts: list[ConflictReport]
    sufficient: bool  # esikleri gecti mi (False ise LLM'e hic gitmeden "bilgi yok" denir)
    top_score: float
    top_coverage: float


class KnowledgeBase:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.metas, self.chunks = load_corpus(settings.docs_dir)
        self.index = BM25Index(self.chunks)

    def retrieve(self, question: str, as_of: date | None = None) -> Retrieval:
        s = self.settings
        as_of = as_of or date.today()
        # Eski surumler top-k'da yer kaplamasin diye sürüm çözümünden önce daha genis aday cek
        raw = self.index.search(question, k=s.top_k * 2)
        resolution = resolve_versions(raw, self.metas, as_of)
        hits = resolution.hits[: s.top_k]

        top_score = hits[0].score if hits else 0.0
        top_cov = hits[0].coverage if hits else 0.0
        sufficient = bool(hits) and top_score >= s.min_score and top_cov >= s.min_coverage
        return Retrieval(hits, resolution.conflicts, sufficient, top_score, top_cov)
