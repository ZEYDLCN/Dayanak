"""LLM yanıtı için deterministik dayanak (grounding) kontrolleri.

LLM'e güvenmeden, yanıttaki iddiaları verilen bölümlerle karşılaştırır:
  - evidence: modelin "kanıt" diye gösterdiği cümleler bölümlerde gerçekten geçmek zorunda.
  - Kaynak bölümlerin hiçbirinde (ve soruda) geçmeyen bir sayı varsa yanıt uydurma sayılır.
  - Sayıyı içeren bölüm modelin gösterdiği kaynaklarda yoksa, o bölüm kaynaklara eklenir.
Sınır: bu kontroller "kanıt gerçekten var mı" sorusunu yanıtlar, "kanıt soruyu gerçekten yanıtlıyor mu"
sorusunu değil (örn. komşu bir bölümün doğru bir cümlesi yanlış soruya kanıt gösterilebilir);
o iş için isteğe bağlı doğrulayıcı LLM geçişi vardır (settings.verify_answers).
Yazıyla verilen sayıları ("otuz gün") da yakalayamaz.
"""

import re
from dataclasses import dataclass

from app.index import Hit
from app.textproc import normalize

# gpt-oss gibi modeller tipografik karakterler üretir (dar boşluk U+202F, bölünmez tire U+2011...);
# bunlar bölüm metniyle karşılaştırmayı bozar.
_TYPO = str.maketrans(
    {
        " ": " ",
        " ": " ",
        " ": " ",
        "​": "",
        "‐": "-",
        "‑": "-",
        "–": "-",
        "—": "-",
    }
)
_QUOTES = re.compile("[\"'“”‘’«»`]")
_ELLIPSIS = re.compile(r"\s*(?:…|\.\.\.)\s*")
_MIN_EVIDENCE_CHARS = 8
_NUM = re.compile(r"\d+(?:[.,:]\d+)*")
_NOINFO = re.compile(r"yeterli bilgi|bilgi bulunmuyor|bilgi yok|bulunmamaktadir|belirtilmemis|yer almiyor")


def clean_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.translate(_TYPO)).strip()


def _flat(text: str) -> str:
    t = normalize(clean_text(text)).replace("*", "")
    return re.sub(r"\s+", " ", _QUOTES.sub("", t)).strip(" .")


def verify_evidence(evidence: tuple[str, ...] | list[str], context: list[Hit]) -> list[Hit] | None:
    """Her kanıt cümlesi, verilen bölümlerden birinde AYNEN (biçim farkları hariç) geçmek zorunda.
    Geçiyorsa o bölümleri döner; kanıt yoksa/uydurmaysa None. '...' ile kısaltılmış alıntı parça parça aranır."""
    if not evidence:
        return None
    found: list[Hit] = []
    for quote in evidence:
        for part in _ELLIPSIS.split(quote):
            flat = _flat(part)
            if not flat:
                continue
            if len(flat) < _MIN_EVIDENCE_CHARS:
                return None
            hit = next((h for h in context if flat in _flat(h.chunk.text)), None)
            if hit is None:
                return None
            if hit not in found:
                found.append(hit)
    return found or None


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
