"""API sozlesmesi (istek/yanit modelleri)."""

from datetime import date

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500, examples=["İade süresi kaç gün?"])
    as_of: date | None = Field(
        default=None,
        description="Hangi tarihte geçerli sürüme göre yanıtlansın (varsayılan: bugün).",
    )


class SourceOut(BaseModel):
    doc_id: str
    title: str
    version: int
    status: str
    effective_date: date
    section: str
    snippet: str
    score: float


class DiscardedOut(BaseModel):
    doc_id: str
    version: int
    effective_date: date
    section: str
    snippet: str


class ConflictOut(BaseModel):
    family: str
    selected_doc_id: str
    selected_version: int
    selected_effective_date: date
    discarded: list[DiscardedOut]
    reason: str


class AskResponse(BaseModel):
    question: str
    answerable: bool
    answer: str
    sources: list[SourceOut]
    conflicts: list[ConflictOut]
    mode: str = Field(description="llm | extractive | extractive-fallback | no-retrieval")
    retrieval: dict


class DocumentOut(BaseModel):
    doc_id: str
    family: str
    title: str
    version: int
    status: str
    effective_date: date
    sections: list[str]
