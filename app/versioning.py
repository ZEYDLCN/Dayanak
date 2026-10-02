"""Ayni prosedurun (family) birden fazla surumu varsa guncel olani secer ve nedenini uretir.

Kural (deterministik, LLM'e birakilmaz):
  1. Yururluk tarihi as_of'tan sonra olan surumler henuz gecerli degildir, elenir.
  2. Kalanlar arasinda en yuksek surum numarasi (esitlikte en yeni yururluk tarihi) guncel sayilir.
  3. Diger surumlerden gelen bolumler cevap uretiminde KULLANILMAZ; yalnizca raporlanir.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from app.index import Hit
from app.models import DocMeta
from app.textproc import normalize


@dataclass(frozen=True)
class DiscardedSection:
    doc_id: str
    version: int
    effective_date: date
    section: str
    snippet: str


@dataclass(frozen=True)
class ConflictReport:
    family: str
    selected_doc_id: str
    selected_version: int
    selected_effective_date: date
    selected_sections: list[str]
    discarded: list[DiscardedSection]
    reason: str


@dataclass
class Resolution:
    hits: list[Hit]  # yalnizca guncel surumlerden gelenler, skora gore sirali
    conflicts: list[ConflictReport] = field(default_factory=list)


def current_docs(metas: list[DocMeta], as_of: date) -> dict[str, DocMeta]:
    """family -> o family'nin as_of tarihinde gecerli olan surumu."""
    by_family: dict[str, list[DocMeta]] = {}
    for m in metas:
        by_family.setdefault(m.family, []).append(m)
    result = {}
    for family, docs in by_family.items():
        in_force = [d for d in docs if d.effective_date <= as_of]
        if in_force:  # bu tarihte ailenin hiçbir sürümü henüz yürürlükte değilse aile dışarıda kalır
            result[family] = max(in_force, key=lambda d: (d.version, d.effective_date))
    return result


def resolve_versions(hits: list[Hit], metas: list[DocMeta], as_of: date) -> Resolution:
    current = current_docs(metas, as_of)
    family_versions: dict[str, list[DocMeta]] = {}
    for m in metas:
        family_versions.setdefault(m.family, []).append(m)

    kept: list[Hit] = []
    dropped: dict[str, list[Hit]] = {}
    for hit in hits:
        doc = hit.chunk.doc
        selected = current.get(doc.family)
        if selected is None:  # bu tarihte ailenin henüz yürürlükte bir sürümü yok
            continue
        if doc.doc_id == selected.doc_id:
            kept.append(hit)
        else:
            dropped.setdefault(doc.family, []).append(hit)

    conflicts = []
    for family, dropped_hits in dropped.items():
        winner = current[family]
        winner_sections = [h.chunk.section for h in kept if h.chunk.doc.family == family]
        old = sorted({(h.chunk.doc.version, h.chunk.doc.effective_date) for h in dropped_hits})
        old_txt = ", ".join(f"v{v} ({d.isoformat()})" for v, d in old)
        if all(v < winner.version for v, _ in old):
            why = "daha eski sürüm olduğu için"
        else:
            why = f"{as_of.isoformat()} tarihinde henüz yürürlükte olmadığı için"
        reason = (
            f"Aynı prosedürün birden fazla sürümü eşleşti: {old_txt} ve "
            f"v{winner.version} ({winner.effective_date.isoformat()}). {as_of.isoformat()} tarihinde "
            f"yürürlükte olan en yüksek sürüm v{winner.version} seçildi; diğerleri {why} yanıtta kullanılmadı."
        )
        conflicts.append(
            ConflictReport(
                family=family,
                selected_doc_id=winner.doc_id,
                selected_version=winner.version,
                selected_effective_date=winner.effective_date,
                selected_sections=winner_sections,
                discarded=[
                    DiscardedSection(
                        h.chunk.doc.doc_id,
                        h.chunk.doc.version,
                        h.chunk.doc.effective_date,
                        h.chunk.section,
                        h.chunk.text,
                    )
                    for h in dropped_hits
                ],
                reason=reason,
            )
        )
    return Resolution(hits=kept, conflicts=conflicts)


_HISTORY = re.compile(r"\b(eski|onceki|eskiden|onceden|gecmis|gecmiste|ilk surum|v1|1\.? surum)\b")
_YEAR = re.compile(r"\b(19|20)\d\d\b")


def wants_history(question: str, metas: list[DocMeta]) -> bool:
    """Soru bilerek eski bir sürümü mü soruyor? ('eski prosedürde', '2023'te', 'v1')"""
    q = normalize(question)
    if _HISTORY.search(q):
        return True
    return any(str(m.effective_date.year) in q for m in metas if m.status == "superseded")


def strip_history_terms(question: str) -> str:
    """'Eski', 'önceki', '2023' gibi sürüm-üstü sözcükler içerik değildir; aramada gürültü yapmasın."""
    q = _HISTORY.sub(" ", normalize(question))
    return _YEAR.sub(" ", q)
