"""Uctan uca akis: arama -> (yeterli mi?) -> yanit uretimi -> kaynak/celiski raporu."""

import logging
import re
from dataclasses import dataclass, field, replace
from datetime import date

from app.config import Settings
from app.index import Hit
from app.llm import AnthropicGenerator, Generator
from app.retrieval import KnowledgeBase
from app.textproc import tokenize
from app.versioning import ConflictReport

log = logging.getLogger(__name__)

NO_INFO = "Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin."
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Source:
    doc_id: str
    title: str
    version: int
    status: str
    effective_date: date
    section: str
    snippet: str
    score: float


@dataclass
class Answer:
    question: str
    answerable: bool
    answer: str
    sources: list[Source]
    conflicts: list[ConflictReport]
    mode: str  # "llm" | "extractive" | "extractive-fallback" | "no-retrieval"
    retrieval: dict = field(default_factory=dict)


class AnswerService:
    def __init__(self, kb: KnowledgeBase, settings: Settings, generator: Generator | None = None):
        self.kb = kb
        self.generator = generator or (AnthropicGenerator(settings) if settings.use_llm else None)

    def ask(self, question: str, as_of: date | None = None) -> Answer:
        r = self.kb.retrieve(question, as_of)
        diag = {"top_score": round(r.top_score, 2), "top_coverage": round(r.top_coverage, 2)}

        if not r.sufficient:
            return Answer(question, False, NO_INFO, [], [], "no-retrieval", diag)

        mode = "llm" if self.generator else "extractive"
        gen = None
        if self.generator:
            try:
                gen = self.generator.generate(question, r.hits)
            except Exception:  # ağ/kota/şema hatası: servis düşmesin, kaynak alıntılayan yanıta dön
                log.exception("LLM çağrısı başarısız, extractive moda düşülüyor")
                mode = "extractive-fallback"

        if gen is None:
            used_hits, text = self._extractive(question, r.hits)
            answerable = bool(used_hits)
        else:
            answerable = gen.answerable
            used_hits = [r.hits[i] for i in gen.used] if answerable else []
            if answerable and not used_hits:
                used_hits = r.hits[:1]  # atıf verilmediyse en iyi bölüm
            text = gen.answer

        if not answerable:
            return Answer(question, False, text or NO_INFO, [], [], mode, diag)

        sources = [_to_source(h) for h in used_hits]
        conflicts = _relevant_conflicts(r.conflicts, used_hits)
        if conflicts:
            text += " " + _conflict_note(conflicts)
        return Answer(question, True, text, sources, conflicts, mode, diag)

    @staticmethod
    def _extractive(question: str, hits: list[Hit]) -> tuple[list[Hit], str]:
        """LLM yokken: en iyi bölümden sorgu terimlerini içeren cümleleri aynen alıntılar."""
        top = hits[0]
        q_terms = set(tokenize(question))
        sentences = [s for s in _SENTENCE.split(top.chunk.text.replace("\n", " ")) if s.strip()]
        scored = [(len(q_terms & set(tokenize(s))), i, s) for i, s in enumerate(sentences)]
        best = sorted((x for x in scored if x[0] > 0), key=lambda x: (-x[0], x[1]))[:2]
        if not best:
            return [], NO_INFO
        return [top], " ".join(s for _, _, s in sorted(best, key=lambda x: x[1]))


def _to_source(h: Hit) -> Source:
    c = h.chunk
    return Source(
        c.doc.doc_id, c.doc.title, c.doc.version, c.doc.status,
        c.doc.effective_date, c.section, c.text, round(h.score, 2),
    )


def _relevant_conflicts(conflicts: list[ConflictReport], used: list[Hit]) -> list[ConflictReport]:
    """Yalnızca yanıtta kullanılan bölümle aynı bölüm adını taşıyan eski/başka sürüm bölümleri raporlanır."""
    used_sections: dict[str, set[str]] = {}
    for h in used:
        used_sections.setdefault(h.chunk.doc.family, set()).add(h.chunk.section)

    relevant = []
    for c in conflicts:
        sections = used_sections.get(c.family, set())
        discarded = [d for d in c.discarded if d.section in sections]
        if discarded:
            relevant.append(replace(c, discarded=discarded, selected_sections=sorted(sections)))
    return relevant


def _conflict_note(conflicts: list[ConflictReport]) -> str:
    c = conflicts[0]
    others = ", ".join(sorted({f"v{d.version}" for x in conflicts for d in x.discarded}))
    return (
        f"(Not: Bu konuda {others} sürümünde farklı bilgi var; "
        f"yürürlükteki v{c.selected_version} esas alınmıştır.)"
    )
