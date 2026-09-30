"""LLM yanıtı için deterministik dayanak (grounding) kontrolleri.

LLM'e güvenmeden, yanıttaki somut iddiaları (sayı, saat, tutar) verilen bölümlerle karşılaştırır:
  - Kaynak bölümlerin hiçbirinde (ve soruda) geçmeyen bir sayı varsa yanıt uydurma sayılır.
  - Sayıyı içeren bölüm modelin gösterdiği kaynaklarda yoksa, o bölüm kaynaklara eklenir.
Sınır: yalnızca rakamla yazılmış iddiaları yakalar; "otuz gün" gibi yazıyla verilen sayıları veya
rakamsız anlam hatalarını ("her gün" -> "hafta sonu yok") yakalayamaz.
"""

import re
from dataclasses import dataclass

from app.index import Hit
from app.textproc import normalize

_NUM = re.compile(r"\d+(?:[.,:]\d+)*")
_NOINFO = re.compile(r"yeterli bilgi|bilgi bulunmuyor|bilgi yok|bulunmamaktadir|belirtilmemis|yer almiyor")


def numbers(text: str) -> set[str]:
    return {n.rstrip(".,:") for n in _NUM.findall(normalize(text))}


def says_no_info(text: str) -> bool:
    return bool(_NOINFO.search(normalize(text)))


@dataclass(frozen=True)
class GroundingResult:
    ok: bool
    ungrounded: set[str]  # hiçbir bölümde/soruda bulunmayan sayılar
    support: list[Hit]  # yanıtı destekleyen bölümler (atıf yapılanlar + sayıyı içeren ek bölümler)


def check_numbers(question: str, answer: str, cited: list[Hit], provided: list[Hit]) -> GroundingResult:
    """Yanıttaki her sayı, sorunun kendisinde ya da verilen bölümlerde geçmek zorunda."""
    wanted = numbers(answer) - numbers(question)
    support = list(cited)
    covered = set().union(*(numbers(h.chunk.text) for h in cited)) if cited else set()
    for hit in provided:
        missing = wanted - covered
        if not missing:
            break
        nums = numbers(hit.chunk.text)
        if hit not in support and missing & nums:
            support.append(hit)
            covered |= nums
    ungrounded = wanted - covered
    return GroundingResult(not ungrounded, ungrounded, support)
