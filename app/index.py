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
    semantic: float = 0.0  # gomme kosinus benzerligi (yalnizca hibrit aramada dolu)


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

    def _backoff(self, term: str) -> str:
        """F5 kesmesi 3 harfli koklerde (gun -> gundu/gunde) eslesmeyi kacirir: kisa bir terim (en fazla 6 harf)
        dizinde yoksa ve ilk 3 harfi dizinde bir terimse o terime dus. Bilerek dar tutuldu: 4 harfli
        onek denendiginde 'homekit' -> 'home' ('Lumora Home' uygulamasi) gibi sahte eslesmeler olusuyordu."""
        if term in self._df or len(term) > 6:
            return term
        return term[:3] if term[:3] in self._df else term

    def search(self, query: str, k: int = 5) -> list[Hit]:
        terms = list(dict.fromkeys(self._backoff(t) for t in tokenize(query)))  # tekrarlari at, sirayi koru
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
