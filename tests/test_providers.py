"""Sohbet ekranındaki model seçimi: istek başına LLM sağlayıcısı."""

from fastapi.testclient import TestClient

from app.answer import AnswerService, UnknownProvider
from app.llm import Generation
from app.main import create_app
from tests.test_answer import IADE_SURESI, FakeGen

import pytest


def two_providers(kb, settings):
    fast = FakeGen(Generation(True, "Hızlı model: 30 gün.", [0], (IADE_SURESI,)))
    slow = FakeGen(Generation(True, "Diğer model: 30 gün.", [0], (IADE_SURESI,)))
    return AnswerService(kb, settings, generators={"nvidia": fast, "gemini": slow}), fast, slow


def test_default_provider_is_first_and_used_when_unspecified(kb, settings):
    svc, fast, slow = two_providers(kb, settings)
    a = svc.ask("İade süresi kaç gün?")
    assert a.provider == "nvidia" and a.answer.startswith("Hızlı") and (fast.calls, slow.calls) == (1, 0)


def test_explicit_provider_overrides_default(kb, settings):
    svc, fast, slow = two_providers(kb, settings)
    a = svc.ask("İade süresi kaç gün?", provider="gemini")
    assert a.provider == "gemini" and a.answer.startswith("Diğer") and (fast.calls, slow.calls) == (0, 1)


def test_unknown_provider_is_rejected_not_silently_replaced(kb, settings):
    svc, fast, slow = two_providers(kb, settings)
    with pytest.raises(UnknownProvider):
        svc.ask("İade süresi kaç gün?", provider="bilinmeyen")
    assert fast.calls == slow.calls == 0


def test_provider_choice_does_not_weaken_guards(kb, settings):
    # Her sağlayıcıda aynı kanıt/sayı denetimi çalışır: uydurma kanıt hangi modelden gelirse gelsin reddedilir
    bad = FakeGen(Generation(True, "İade süresi 45 gündür.", [0], ("Müşteriler 45 gün içinde iade edebilir.",)))
    svc = AnswerService(kb, settings, generators={"nvidia": bad, "gemini": bad})
    for p in ("nvidia", "gemini"):
        a = svc.ask("İade süresi kaç gün?", provider=p)
        assert not a.answerable and a.mode == "llm-rejected"


def test_api_lists_providers_and_accepts_choice(kb, settings):
    svc, _, _ = two_providers(kb, settings)
    with TestClient(create_app(svc)) as c:
        listing = c.get("/providers").json()
        assert [p["id"] for p in listing] == ["nvidia", "gemini"] and listing[0]["default"] and not listing[1]["default"]
        ok = c.post("/ask", json={"question": "İade süresi kaç gün?", "provider": "gemini"}).json()
        assert ok["provider"] == "gemini"
        bad = c.post("/ask", json={"question": "İade süresi kaç gün?", "provider": "yok"})
        assert bad.status_code == 400


def test_extractive_mode_has_no_providers(service):
    with TestClient(create_app(service)) as c:
        assert c.get("/providers").json() == []
        assert c.post("/ask", json={"question": "İade süresi kaç gün?"}).json()["provider"] is None
