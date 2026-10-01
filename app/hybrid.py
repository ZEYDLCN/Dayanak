"""Hibrit arama: BM25 (sözcük) + gömme (anlam), Reciprocal Rank Fusion ile birleştirilir.

Sözcük sinyali (skor, kapsama) her Hit'te korunur: "bilgi yok" kapısı ve açıklanabilirlik BM25'e dayanmaya devam eder.
Anlamsal benzerlik (kosinüs) ek bir sinyal olarak Hit.semantic'te taşınır.
"""

import numpy as np

from app.embeddings import Embedder, cached_document_vectors
from app.index import BM25Index, Hit


class HybridIndex:
    def __init__(self, bm25: BM25Index, embedder: Embedder, cache_dir=None, rrf_k: int = 60):
        self.bm25 = bm25
        self.embedder = embedder
        self.rrf_k = rrf_k
        self.chunks = bm25.chunks
        self.vectors = cached_document_vectors(embedder, [c.index_text for c in self.chunks], cache_dir)

    def semantic_scores(self, query: str) -> np.ndarray:
        return self.vectors @ self.embedder.embed_query(query)

    def search(self, query: str, k: int = 5) -> list[Hit]:
        sims = self.semantic_scores(query)
        lex = {h.chunk.chunk_id: (rank, h) for rank, h in enumerate(self.bm25.search(query, k=len(self.chunks)))}
        sem_rank = {int(i): rank for rank, i in enumerate(np.argsort(-sims))}
        fused = []
        for i, chunk in enumerate(self.chunks):
            score = 1.0 / (self.rrf_k + sem_rank[i] + 1)
            lex_hit = lex.get(chunk.chunk_id)
            if lex_hit:
                score += 1.0 / (self.rrf_k + lex_hit[0] + 1)
            fused.append((score, i, lex_hit[1] if lex_hit else None))
        fused.sort(key=lambda x: x[0], reverse=True)
        out = []
        for _, i, lex_hit in fused[:k]:
            sem = float(sims[i])
            if lex_hit:
                out.append(Hit(lex_hit.chunk, lex_hit.score, lex_hit.coverage, lex_hit.matched, sem))
            else:
                out.append(Hit(self.chunks[i], 0.0, 0.0, frozenset(), sem))
        return out
