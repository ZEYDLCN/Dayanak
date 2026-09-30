"""Bellek ici BM25 indeksi (bagimlilik yok; ~40 satir, savunmasi kolay)."""

import math
from collections import Counter
from dataclasses import dataclass

from app.models import Chunk
from app.textproc import tokenize


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    coverage: float  # sorgu terimlerinin (IDF agirlikli) ne kadari bu bolumde geciyor, 0..1
    matched: frozenset[str]


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self._tf = [Counter(tokenize(c.index_text)) for c in chunks]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg_len = sum(self._len) / len(chunks)
        df: Counter[str] = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(chunks)
        self._df = df
        self._n = n

    def idf(self, term: str) -> float:
        # Korpusta hic gecmeyen terim (df=0) en yuksek IDF'i alir
        df = self._df.get(term, 0)
        return math.log(1 + (self._n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 5) -> list[Hit]:
        terms = list(dict.fromkeys(tokenize(query)))  # tekrarlari at, sirayi koru
        if not terms:
            return []
        total_idf = sum(self.idf(t) for t in terms)
        hits = []
        for i, chunk in enumerate(self.chunks):
            tf, dl = self._tf[i], self._len[i]
            score, matched = 0.0, set()
            for t in terms:
                f = tf.get(t, 0)
                if not f:
                    continue
                matched.add(t)
                norm = f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self._avg_len))
                score += self.idf(t) * norm
            if matched:
                coverage = sum(self.idf(t) for t in matched) / total_idf
                hits.append(Hit(chunk, score, coverage, frozenset(matched)))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]
