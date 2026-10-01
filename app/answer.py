"""Uctan uca akis: arama -> kapi -> yanit uretimi -> dayanak kontrolleri -> kaynak/celiski raporu."""

import logging
import re
import time
from dataclasses import dataclass, field, replace
from datetime import date

from app.config import Settings
from app.grounding import check_numbers, says_no_info, verify_evidence
from app.index import Hit
from app.llm import AnthropicGenerator, GeminiGenerator, Generation, Generator, NvidiaGenerator
from app.retrieval import KnowledgeBase, Retrieval
from app.textproc import tokenize
from app.versioning import ConflictReport, wants_history

log = logging.getLogger(__name__)

NO_INFO = "Bu soruyla ilgili doküman kayıtlarında yeterli bilgi bulunmuyor. Lütfen destek ekibiyle iletişime geçin."
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_MAX_QUOTE_CHARS = 400
FALLBACK_PREFIX = "(Yapay zekâ yanıt servisine şu an ulaşılamıyor; en yakın belge bölümü aynen aşağıdadır, sorunuzu yanıtlamayabilir:) "
ABSTAINED = "llm-abstained"  # model kendisi "cevap yok" dedi (guvenlik korumasi devreye girmedi)


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
    # "llm" | "extractive" | "extractive-fallback" | "no-retrieval" | "llm-rejected" | "version-comparison"
    mode: str
    retrieval: dict = field(default_factory=dict)


class AnswerService:
    def __init__(self, kb: KnowledgeBase, settings: Settings, generator: Generator | None = None):
        self.kb = kb
        self.settings = settings
        if generator is not None:
            self.generator = generator
        elif settings.llm_provider == "nvidia" and settings.use_llm:
            self.generator = NvidiaGenerator(settings)
        elif settings.llm_provider == "gemini" and settings.use_llm:
            self.generator = GeminiGenerator(settings)
        elif settings.llm_provider == "anthropic" and settings.use_llm:
            self.generator = AnthropicGenerator(settings)
        else:
            self.generator = None

    def ask(self, question: str, as_of: date | None = None) -> Answer:
        t_ret = time.perf_counter()
        r = self.kb.retrieve(question, as_of)
        diag = {
            "top_score": round(r.top_score, 2),
            "top_coverage": round(r.top_coverage, 2),
            "retrieval_ms": round((time.perf_counter() - t_ret) * 1000, 1),  # arama gecikmesi (gomme dahil)
        }

        # Kapi, ardindaki karar vericiye gore secilir: LLM varsa LLM karar verir (genis kapi),
        # yoksa alintilanan bolum tek savunmadir (siki kapi).
        if not (r.plausible if self.generator else r.sufficient):
            return Answer(question, False, NO_INFO, [], [], "no-retrieval", diag)

        # "Eski prosedurde ... kac gundu?" gibi sorularda LLM'e gitmeden iki surumu yan yana goster:
        # LLM eski surumu gormedigi icin guncel degeri "eski" diye sunardi.
        if r.conflicts and wants_history(question, self.kb.metas):
            comparison = self._compare_versions(question, r, diag)
            if comparison:
                return comparison

        mode = "llm" if self.generator else "extractive"
        gen: Generation | None = None
        used_hits: list[Hit] = []
        reject: str | None = None
        context = r.hits[: self.settings.llm_context_passages]
        if self.generator:
            try:
                gen = self.generator.generate(question, context)
                used_hits, reject = self._vet(question, gen, context)
            except Exception:  # ağ/kota/şema hatası: servis düşmesin, kaynak alıntılayan yanıta dön
                log.exception("LLM çağrısı başarısız, extractive moda düşülüyor")
                gen, mode = None, "extractive-fallback"

        if gen is None:
            # LLM yokken/hatada zayif eslesmis bir bolumu kesin cevap gibi gostermeyelim.
            if not r.sufficient or (mode == "extractive-fallback" and r.top_coverage < 0.5):
                return Answer(question, False, NO_INFO, [], [], mode, diag)
            used_hits, text = self._extractive(question, r.hits)
            if not used_hits:
                return Answer(question, False, NO_INFO, [], [], mode, diag)
            if mode == "extractive-fallback":  # LLM hakem olmadan alıntı: cevap değil "en yakın bölüm" olduğunu söyle
                text = FALLBACK_PREFIX + text
        else:
            if reject == ABSTAINED:
                return Answer(question, False, NO_INFO, [], [], mode, diag)
            if reject:  # model cevap verdi ama dayanak kontrolu gecmedi: kullaniciya gostermiyoruz
                log.warning("LLM yaniti reddedildi (%s): %r", reject, gen.answer)
                return Answer(question, False, NO_INFO, [], [], "llm-rejected", {**diag, "guard": reject})
            text = gen.answer

        sources = [_to_source(h) for h in used_hits]
        conflicts = _relevant_conflicts(r.conflicts, used_hits)
        if conflicts:
            text += " " + _conflict_note(conflicts)
        return Answer(question, True, text, sources, conflicts, mode, diag)

    def _vet(self, question: str, gen: Generation, context: list[Hit]) -> tuple[list[Hit], str | None]:
        """LLM yanitini denetler. (kaynak bolumler, ret nedeni); ret nedeni None ise yanit guvenlidir.

        Sira: kanit gercekten bolumde var mi -> sayilar bolumlerde var mi -> (istege bagli) dogrulayici LLM.
        """
        s = self.settings
        if not gen.answerable:
            return [], ABSTAINED
        if s.require_evidence:
            cited = verify_evidence(gen.evidence, context)
            if cited is None:
                return [], "kanıt cümlesi verilen bölümlerde bulunamadı"
        else:
            if says_no_info(gen.answer):  # answerable=true ama "bilgi yok" diyor: kendiyle celisiyor
                return [], ABSTAINED
            cited = [context[i] for i in gen.used] or context[:1]

        grounding = check_numbers(question, gen.answer, cited, context)
        if not grounding.ok:
            return [], f"kaynakta olmayan sayı: {sorted(grounding.ungrounded)}"

        if s.verify_answers and hasattr(self.generator, "verify"):
            evidence = " ".join(gen.evidence) or " ".join(h.chunk.text for h in cited)
            if not self.generator.verify(question, gen.answer, evidence):
                return [], "doğrulayıcı: kanıt soruyu doğrudan yanıtlamıyor"
        return grounding.support, None

    def _compare_versions(self, question: str, r: Retrieval, diag: dict) -> Answer | None:
        """Tarihsel soru: eski ve güncel sürümü, metinlerini aynen alıntılayarak yan yana verir (LLM yok)."""
        top = r.hits[0]
        conflicts = _relevant_conflicts(r.conflicts, [top])
        if not conflicts:
            return None
        meta = {m.doc_id: m for m in self.kb.metas}
        parts, sources = [], [_to_source(top)]
        for c in conflicts:
            for d in c.discarded:
                parts.append(
                    f"Eski sürümde (v{d.version}, yürürlük {d.effective_date.isoformat()}): {_flat(d.snippet)}"
                )
                m = meta[d.doc_id]
                sources.append(
                    Source(m.doc_id, m.title, m.version, m.status, m.effective_date, d.section, d.snippet, 0.0)
                )
        d0 = top.chunk.doc
        parts.append(f"Güncel sürümde (v{d0.version}, yürürlük {d0.effective_date.isoformat()}): {_flat(top.chunk.text)}")
        return Answer(question, True, " ".join(parts), sources, conflicts, "version-comparison", diag)

    @staticmethod
    def _extractive(question: str, hits: list[Hit]) -> tuple[list[Hit], str]:
        """LLM yokken: en iyi bölümü aynen alıntılar. Bölümler kısa; uzunsa sorgu terimlerini içeren cümleler seçilir."""
        top = hits[0]
        flat = _flat(top.chunk.text)
        if len(flat) <= _MAX_QUOTE_CHARS:
            return [top], flat
        q_terms = set(tokenize(question))
        sentences = [s for s in _SENTENCE.split(flat) if s.strip()]
        scored = [(len(q_terms & set(tokenize(s))), i, s) for i, s in enumerate(sentences)]
        best = sorted((x for x in scored if x[0] > 0), key=lambda x: (-x[0], x[1]))[:2]
        if not best:
            return [], NO_INFO
        return [top], " ".join(s for _, _, s in sorted(best, key=lambda x: x[1]))


def _flat(text: str) -> str:
    return text.replace("\n", " ").strip()


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
