import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.answer import Answer, AnswerService, UnknownProvider
from app.config import get_settings
from app.retrieval import KnowledgeBase
from app.schemas import AskRequest, AskResponse, ConflictOut, DocumentOut, ProviderOut, SourceOut

logging.basicConfig(level=logging.INFO)
WEB_DIR = Path(__file__).resolve().parent / "web"


def create_app(service: AnswerService | None = None) -> FastAPI:
    """service verilirse (testler) onu kullanir; yoksa ortam degiskenlerinden kurar."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if service is not None:
            app.state.service = service
        else:
            settings = get_settings()
            app.state.service = AnswerService(KnowledgeBase(settings), settings)
        yield

    app = FastAPI(title="Lumora Bilgi Asistanı", version="1.0.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/health")
    def health(request: Request):
        svc: AnswerService = request.app.state.service
        return {
            "status": "ok",
            "documents": len(svc.kb.metas),
            "chunks": len(svc.kb.chunks),
            "mode": "llm" if svc.generator else "extractive",
        }

    @app.get("/documents", response_model=list[DocumentOut])
    def documents(request: Request):
        kb = request.app.state.service.kb
        sections: dict[str, list[str]] = {}
        for c in kb.chunks:
            sections.setdefault(c.doc.doc_id, []).append(c.section)
        return [
            DocumentOut(**{**m.__dict__, "sections": sections.get(m.doc_id, [])}) for m in kb.metas
        ]

    @app.get("/providers", response_model=list[ProviderOut])
    def providers(request: Request):
        return request.app.state.service.providers()

    # Senkron endpoint: FastAPI bunu thread pool'da calistirir, LLM cagrisi event loop'u bloklamaz.
    @app.post("/ask", response_model=AskResponse)
    def ask(body: AskRequest, request: Request):
        svc: AnswerService = request.app.state.service
        try:
            return _to_response(svc.ask(body.question.strip(), body.as_of, body.provider))
        except UnknownProvider as e:
            raise HTTPException(status_code=400, detail=str(e))

    return app


def _to_response(a: Answer) -> AskResponse:
    return AskResponse(
        question=a.question,
        answerable=a.answerable,
        answer=a.answer,
        sources=[SourceOut(**s.__dict__) for s in a.sources],
        conflicts=[
            ConflictOut(
                family=c.family,
                selected_doc_id=c.selected_doc_id,
                selected_version=c.selected_version,
                selected_effective_date=c.selected_effective_date,
                discarded=[d.__dict__ for d in c.discarded],
                reason=c.reason,
            )
            for c in a.conflicts
        ],
        mode=a.mode,
        retrieval=a.retrieval,
        provider=a.provider,
    )


app = create_app()
