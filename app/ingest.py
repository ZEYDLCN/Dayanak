"""Markdown dokumanlarini (front-matter + '## bolum') okuyup Chunk listesine cevirir."""

import re
from dataclasses import replace
from datetime import date
from pathlib import Path

import yaml

from app.models import Chunk, DocMeta

TAGS_FILE = "etiketler.yaml"
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
_REQUIRED = ("doc_id", "family", "title", "version", "status", "effective_date")
_STATUSES = {"current", "superseded"}


class DocumentError(ValueError):
    pass


def parse_document(path: Path) -> tuple[DocMeta, list[Chunk]]:
    raw = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER.match(raw)
    if not match:
        raise DocumentError(f"{path.name}: front-matter bulunamadi")

    front = yaml.safe_load(match.group(1)) or {}
    missing = [k for k in _REQUIRED if k not in front]
    if missing:
        raise DocumentError(f"{path.name}: eksik alanlar: {', '.join(missing)}")
    if front["status"] not in _STATUSES:
        raise DocumentError(f"{path.name}: gecersiz status: {front['status']!r}")

    eff = front["effective_date"]
    meta = DocMeta(
        doc_id=str(front["doc_id"]),
        family=str(front["family"]),
        title=str(front["title"]),
        version=int(front["version"]),
        status=front["status"],
        effective_date=eff if isinstance(eff, date) else date.fromisoformat(str(eff)),
        supersedes=front.get("supersedes"),
    )
    return meta, split_sections(meta, match.group(2))


def split_sections(meta: DocMeta, body: str) -> list[Chunk]:
    """'## ' basliklarina gore boler. Ilk basliktan onceki metin 'Giris' bolumu olur."""
    chunks: list[Chunk] = []
    section = "Giriş"
    buf: list[str] = []

    def flush() -> None:
        text = "\n".join(buf).strip()
        if text:
            chunks.append(Chunk(f"{meta.doc_id}#{len(chunks) + 1}", meta, section, text))
        buf.clear()

    for line in body.splitlines():
        if line.startswith("# "):  # dokuman basligi; bolum degil
            continue
        if line.startswith("## "):
            flush()
            section = line[3:].strip()
        else:
            buf.append(line)
    flush()
    return chunks


def load_corpus(docs_dir: Path) -> tuple[list[DocMeta], list[Chunk]]:
    metas: list[DocMeta] = []
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        meta, doc_chunks = parse_document(path)
        metas.append(meta)
        chunks.extend(doc_chunks)

    if not metas:
        raise DocumentError(f"{docs_dir} altinda dokuman bulunamadi")
    _validate(metas)
    return metas, apply_tags(chunks, docs_dir / TAGS_FILE)


def apply_tags(chunks: list[Chunk], path: Path) -> list[Chunk]:
    """etiketler.yaml (doc_id -> bolum basligi -> eş anlamli sozcukler) varsa bolumlere baglar.
    Dokuman metnine dokunmaz; etiketler yalnizca aramada kullanilir. Bilinmeyen doc/bolum hata verir."""
    if not path.exists():
        return chunks
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    by_key = {(c.doc.doc_id, c.section): i for i, c in enumerate(chunks)}
    out = list(chunks)
    for doc_id, sections in data.items():
        for section, words in (sections or {}).items():
            if (doc_id, section) not in by_key:
                raise DocumentError(f"{path.name}: bilinmeyen bolum {doc_id!r} / {section!r}")
            if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
                raise DocumentError(f"{path.name}: {doc_id}/{section} bir metin listesi olmali")
            i = by_key[(doc_id, section)]
            out[i] = replace(out[i], tags=" ".join(words))
    return out


def _validate(metas: list[DocMeta]) -> None:
    ids = [m.doc_id for m in metas]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise DocumentError(f"tekrar eden doc_id: {sorted(dupes)}")
    for m in metas:
        if m.supersedes and m.supersedes not in ids:
            raise DocumentError(f"{m.doc_id}: supersedes -> bilinmeyen doc_id {m.supersedes!r}")

    # status alani, surum numarasindan turetilen kuralla tutarli olmali:
    # her family'de en yuksek surum 'current', digerleri 'superseded'.
    families: dict[str, list[DocMeta]] = {}
    for m in metas:
        families.setdefault(m.family, []).append(m)
    for family, docs in families.items():
        latest = max(docs, key=lambda d: d.version)
        for d in docs:
            expected = "current" if d is latest else "superseded"
            if d.status != expected:
                raise DocumentError(
                    f"{d.doc_id}: status={d.status!r} ama '{family}' family'sinde v{d.version} icin {expected!r} bekleniyordu"
                )
