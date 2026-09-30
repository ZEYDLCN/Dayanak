import json

import httpx
import pytest

from app.answer import AnswerService
from app.config import Settings
from app.llm import GeminiGenerator, _gemini_schema, RESPONSE_SCHEMA

IADE_SURESI = "Müşteriler, ürünü teslim aldıkları tarihten itibaren 30 gün içinde iade talebinde bulunabilir."
KEY = "test-gemini-key-123"


def settings(**kw):
    return Settings(_env_file=None, llm_provider="gemini", gemini_api_key=KEY, **kw)


def gemini_reply(payload: dict, finish: str = "STOP") -> httpx.Response:
    return httpx.Response(
        200, json={"candidates": [{"finishReason": finish, "content": {"parts": [{"text": json.dumps(payload)}]}}]}
    )


def test_request_shape_key_in_header_not_in_url(kb):
    seen = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["key"], seen["body"] = str(request.url), request.headers["x-goog-api-key"], json.loads(request.content)
        return gemini_reply({"answerable": True, "answer": "İade süresi **30** gündür.", "evidence": [IADE_SURESI], "used_passages": [1]})

    s = settings()
    gen = GeminiGenerator(s, client=httpx.Client(transport=httpx.MockTransport(respond)))
    a = AnswerService(kb, s, generator=gen).ask("İade süresi kaç gün?")

    assert seen["key"] == KEY and KEY not in seen["url"]  # anahtar günlüklere/hata mesajlarına sızmasın
    assert seen["url"].endswith("/models/gemini-3.1-flash-lite:generateContent")
    cfg = seen["body"]["generationConfig"]
    assert cfg["temperature"] == 0 and cfg["responseMimeType"] == "application/json"
    assert cfg["responseSchema"]["type"] == "OBJECT" and "additionalProperties" not in json.dumps(cfg["responseSchema"])
    assert "İade Süresi" in seen["body"]["contents"][0]["parts"][0]["text"]
    assert a.mode == "llm" and a.answerable and a.sources[0].doc_id == "iade-proseduru-v2"


def test_schema_conversion_uppercases_types_and_drops_additional_properties():
    out = _gemini_schema(RESPONSE_SCHEMA)
    assert out["properties"]["answerable"]["type"] == "BOOLEAN"
    assert out["properties"]["evidence"]["items"]["type"] == "STRING"
    assert "additionalProperties" not in out
    assert RESPONSE_SCHEMA["type"] == "object"  # kaynak şema değişmedi


def test_valid_abstention_is_not_an_error(kb):
    s = settings()
    gen = GeminiGenerator(s, client=httpx.Client(transport=httpx.MockTransport(lambda r: gemini_reply({"answerable": False}))))
    a = AnswerService(kb, s, generator=gen).ask("Telefon desteği hafta sonu açık mı?")
    assert a.mode == "llm" and not a.answerable


@pytest.mark.parametrize("finish", ["MAX_TOKENS", "SAFETY"])
def test_incomplete_generation_falls_back_safely(kb, finish):
    s = settings()
    gen = GeminiGenerator(s, client=httpx.Client(transport=httpx.MockTransport(lambda r: gemini_reply({"answerable": True}, finish))))
    assert AnswerService(kb, s, generator=gen).ask("İade süresi kaç gün?").mode == "extractive-fallback"


def test_overload_503_is_retried_then_succeeds(kb, monkeypatch):
    monkeypatch.setattr("app.llm.time.sleep", lambda s: None)
    calls = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(503, json={"error": {"message": "high demand"}})
        return gemini_reply({"answerable": False})

    gen = GeminiGenerator(settings(), client=httpx.Client(transport=httpx.MockTransport(respond)))
    assert gen.generate("soru", kb.retrieve("İade süresi kaç gün?").hits[:1]).answerable is False
    assert len(calls) == 3


def test_provider_needs_key_to_be_active():
    assert Settings(_env_file=None, llm_provider="gemini", gemini_api_key="").use_llm is False
    assert settings().use_llm is True
