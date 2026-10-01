from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DocMeta:
    doc_id: str
    family: str  # ayni prosedurun tum surumleri ayni family'yi paylasir
    title: str
    version: int
    status: str  # "current" | "superseded"
    effective_date: date
    supersedes: str | None = None


@dataclass(frozen=True)
class Chunk:
    """Bir dokumanin tek bir bolumu (## basligi altindaki metin)."""

    chunk_id: str
    doc: DocMeta
    section: str
    text: str
    tags: str = ""  # yalnizca arama icin eş anlamli sozcukler (etiketler.yaml); yanitta/kanitta gosterilmez

    @property
    def index_text(self) -> str:
        # Baslik, bolum adi ve etiketler de aranabilir olsun
        return f"{self.doc.title} {self.section} {self.text} {self.tags}".rstrip()
