"""Turkce metin normalizasyonu, tokenizasyon ve basit kok alma."""

import re

# Turkce'ye ozgu buyuk/kucuk harf tuzagi: "I".lower() == "i" (yanlis), dogrusu "ı"; "İ" -> "i".
_LOWER = str.maketrans({"I": "ı", "İ": "i"})
# Aksansiz yazan kullanicilar icin ASCII'ye katlama ("iade süresi" == "iade suresi")
_FOLD = str.maketrans("ığüşöç", "igusoc")
_TOKEN = re.compile(r"[a-z0-9]+")

# Katlanmis (ASCII) formda. Soru kaliplari ve baglaclar; icerik tasiyan kelimeler bilerek yok.
STOPWORDS = frozenset(
    """
    ve veya ile bir bu o icin mi mu ne kac kadar nasil nedir midir var ise da de
    ya her en daha gibi olan olarak hangi kim nerede neden benim ben bana biz
    lutfen acaba mumkun olur mudur mi
    """.split()
)

STEM_LEN = 5  # F5: ilk 5 harf. Turkce IR literaturunde sabit-onek kesmenin iyi bir taban cizgisi.


def normalize(text: str) -> str:
    return text.translate(_LOWER).lower().translate(_FOLD)


def stem(token: str) -> str:
    return token[:STEM_LEN]


def tokenize(text: str) -> list[str]:
    """Normalize eder, durak kelimeleri atar, kok alir. Rakamlar ('30', '2') korunur."""
    out = []
    for tok in _TOKEN.findall(normalize(text)):
        if tok in STOPWORDS:
            continue
        if len(tok) < 2 and not tok.isdigit():
            continue
        out.append(stem(tok))
    return out
