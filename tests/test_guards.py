"""Halüsinasyon korumaları: kanıt doğrulama, doğrulayıcı geçiş, eski sürüm karşılaştırması, ağ dayanıklılığı."""

import json

import httpx
import pytest

from app.answer import NO_INFO, AnswerService
from app.grounding import clean_text, verify_evidence
from app.llm import Generation, NvidiaGenerator, extract_json

IADE_SURESI = "Müşteriler, ürünü teslim aldıkları tarihten itibaren 30 gün içinde iade talebinde bulunabilir."


class FakeGen:
    def __init__(self, result, verdict=None):
        self.result, self.verdict, self.verify_calls = result, verdict, 0

    def generate(self, question, hits):
        return self.result

    def verify(self, question, answer, evidence):
        self.verify_calls += 1
        if isinstance(self.verdict, Exception):
            raise self.verdict
        return self.verdict


@pytest.fixture()
def context(kb):
    return kb.retrieve("İade süresi kaç gün?").hits[:2]


# --- evidence ---------------------------------------------------------------------------------------------

def test_verbatim_evidence_is_accepted_and_maps_to_its_passage(context):
    found = verify_evidence([IADE_SURESI], context)
    assert found and found[0].chunk.section == "İade Süresi"


def test_evidence_tolerates_typography_bold_and_quotes(context):
    quote = "“Müşteriler, ürünü teslim aldıkları tarihten itibaren **30 gün** içinde iade talebinde bulunabilir”"
    assert verify_evidence([quote], context)


def test_ellipsis_quote_is_checked_piecewise(context):
    assert verify_evidence(["Müşteriler, ürünü teslim aldıkları ... 30 gün içinde iade talebinde"], context)
    assert not verify_evidence(["Müşteriler, ürünü teslim aldıkları ... 60 gün içinde iade talebinde"], context)


@pytest.mark.parametrize("bad", [[], [""], ["30 gün"], ["İade süresi 30 gündür ve kargo bedavadır."]])
def test_missing_short_or_invented_evidence_is_rejected(context, bad):
    assert verify_evidence(bad, context) is None


def test_fabricated_evidence_never_reaches_the_user(kb, settings):
    """Model 'kanıt' uydurursa (komşu bilgiyi kanıt gibi yazarsa) yanıt gösterilmez."""
    gen = FakeGen(Generation(True, "İade kargo kodu 30 gün geçerlidir.", [0], ("İade kargo kodu 30 gün geçerlidir.",)))
    a = AnswerService(kb, settings, generator=gen).ask("İade kargo kodunu kaç gün içinde kullanmalıyım?")
    assert not a.answerable and a.mode == "llm-rejected" and a.answer == NO_INFO and a.sources == []
    assert "kanıt" in a.retrieval["guard"]


def test_sources_come_from_verified_evidence_not_from_model_citations(kb, settings):
    """Model yanlış bölüm numarası atıf yapsa bile kaynak, kanıtın geçtiği bölümdür."""
    question = "İade süresi kaç gün?"
    context = kb.retrieve(question).hits[: settings.llm_context_passages]
    wrong = next(i for i, h in enumerate(context) if h.chunk.section != "İade Süresi")
    gen = FakeGen(Generation(True, "İade süresi 30 gündür.", [wrong], (IADE_SURESI,)))
    a = AnswerService(kb, settings, generator=gen).ask(question)
    assert a.answerable and [s.section for s in a.sources] == ["İade Süresi"]


def test_legacy_mode_without_evidence_uses_model_citations(kb, settings):
    lenient = settings.model_copy(update={"require_evidence": False})
    a = AnswerService(kb, lenient, generator=FakeGen(Generation(True, "30 gün.", [0]))).ask("İade süresi kaç gün?")
    assert a.answerable and a.sources[0].section == "İade Süresi"


# --- doğrulayıcı geçiş ------------------------------------------------------------------------------------

def _verifying(settings):
    return settings.model_copy(update={"verify_answers": True})


def test_verifier_rejection_blocks_an_answer_whose_evidence_is_real_but_off_topic(kb, settings):
    gen = FakeGen(Generation(True, "İade süresi 30 gündür.", [0], (IADE_SURESI,)), verdict=False)
    a = AnswerService(kb, _verifying(settings), generator=gen).ask("İade süresi kaç gün?")
    assert not a.answerable and a.mode == "llm-rejected" and gen.verify_calls == 1
    assert "doğrulayıcı" in a.retrieval["guard"]


def test_verifier_approval_lets_answer_through(kb, settings):
    gen = FakeGen(Generation(True, "İade süresi 30 gündür.", [0], (IADE_SURESI,)), verdict=True)
    a = AnswerService(kb, _verifying(settings), generator=gen).ask("İade süresi kaç gün?")
    assert a.answerable and a.mode == "llm"


def test_verifier_is_not_called_when_disabled_or_when_model_abstains(kb, settings):
    gen = FakeGen(Generation(True, "İade süresi 30 gündür.", [0], (IADE_SURESI,)), verdict=False)
    assert AnswerService(kb, settings, generator=gen).ask("İade süresi kaç gün?").answerable
    assert gen.verify_calls == 0
    gen = FakeGen(Generation(False, "", []), verdict=True)
    AnswerService(kb, _verifying(settings), generator=gen).ask("İade süresi kaç gün?")
    assert gen.verify_calls == 0


def test_verifier_failure_falls_back_instead_of_crashing(kb, settings):
    gen = FakeGen(Generation(True, "İade süresi 30 gündür.", [0], (IADE_SURESI,)), verdict=RuntimeError("ağ"))
    a = AnswerService(kb, _verifying(settings), generator=gen).ask("İade süresi kaç gün?")
    assert a.mode == "extractive-fallback"


# --- eski sürüm soruları ----------------------------------------------------------------------------------

def test_history_question_compares_versions_instead_of_claiming_current_value_is_old(service):
    a = service.ask("Eski iade prosedüründe iade süresi kaç gündü?")
    assert a.mode == "version-comparison" and a.answerable
    assert "v1" in a.answer and "14 gün" in a.answer  # eski değer, eski olarak etiketli
    assert "Güncel sürümde (v2" in a.answer and "30 gün" in a.answer
    assert {s.status for s in a.sources} == {"current", "superseded"}


def test_year_of_superseded_version_triggers_comparison(service):
    assert service.ask("2023 iade süresi kaç gündü?").mode == "version-comparison"


def test_ordinary_question_does_not_trigger_comparison(service):
    assert service.ask("İade süresi kaç gün?").mode == "extractive"


# --- yardımcılar ------------------------------------------------------------------------------------------

def test_clean_text_normalizes_typographic_characters():
    assert clean_text("2,4 GHz Wi‑Fi – hazır") == "2,4 GHz Wi-Fi - hazır"


@pytest.mark.parametrize(
    "raw",
    [
        '{"answerable": false}',
        '```json\n{"answerable": false}\n```',
        '<think>düşünüyorum {x}</think>\n{"answerable": false}',
        'Yanıt: {"answerable": false} bitti',
    ],
)
def test_extract_json_handles_fences_and_think_blocks(raw):
    assert extract_json(raw) == {"answerable": False}


def test_extract_json_without_object_raises():
    with pytest.raises(ValueError):
        extract_json("json yok")


def test_nvidia_retries_once_on_rate_limit_then_succeeds(kb):
    from app.config import Settings

    settings = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="k")
    calls = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": "rate"})
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"answerable": false}'}}]})

    gen = NvidiaGenerator(settings, client=httpx.Client(transport=httpx.MockTransport(respond)))
    assert gen.generate("soru", kb.retrieve("İade süresi kaç gün?").hits[:1]).answerable is False
    assert len(calls) == 2


def test_nvidia_payload_is_deterministic_and_prompt_has_no_leaked_facts(kb):
    from app.config import Settings

    settings = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="k")
    seen = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"answerable": false}'}}]})

    NvidiaGenerator(settings, client=httpx.Client(transport=httpx.MockTransport(respond))).generate(
        "soru", kb.retrieve("İade süresi kaç gün?").hits[:1]
    )
    assert seen["temperature"] == 0.0
    system = seen["messages"][0]["content"]
    # Örnek çıktı gerçek bir olgu içermemeli (few-shot sızıntısı: model örnekteki değeri yanıta taşıyabilir)
    assert "30 gün" not in system and "iade" not in system.lower()


def test_nvidia_honors_retry_after_and_gives_up_after_three_attempts(kb, monkeypatch):
    from app.config import Settings

    slept = []
    monkeypatch.setattr("app.llm.time.sleep", lambda s: slept.append(s))
    settings = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="k")
    calls = []

    def always_429(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429, headers={"retry-after": "4"}, json={"error": "rate"})

    gen = NvidiaGenerator(settings, client=httpx.Client(transport=httpx.MockTransport(always_429)))
    with pytest.raises(httpx.HTTPStatusError):
        gen.generate("soru", kb.retrieve("İade süresi kaç gün?").hits[:1])
    assert len(calls) == 3 and slept == [4.0, 4.0]


def test_service_falls_back_safely_when_rate_limit_persists(kb, monkeypatch):
    from app.answer import AnswerService
    from app.config import Settings

    monkeypatch.setattr("app.llm.time.sleep", lambda s: None)
    settings = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="k")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429, json={})))
    svc = AnswerService(kb, settings, generator=NvidiaGenerator(settings, client=client))
    a = svc.ask("Telefon desteği hafta sonu açık mı?")
    assert a.mode == "extractive-fallback"
    # Uyarı: fallback yalnızca güçlü eşleşmede alıntı yapar; zayıfta "bilgi yok" der
    assert a.answerable or a.answer


def test_fallback_answer_is_labeled_as_nearest_section_not_as_an_answer(kb, settings):
    """LLM hakem olmadan alıntı yapıldığında kullanıcı bunun kesin cevap olmadığını görmeli."""
    from app.answer import FALLBACK_PREFIX

    class Boom:
        def generate(self, question, hits):
            raise RuntimeError("503")

    a = AnswerService(kb, settings, generator=Boom()).ask("Hub 5 GHz Wi-Fi ağına bağlanır mı?")
    assert a.mode == "extractive-fallback" and a.answerable
    assert a.answer.startswith(FALLBACK_PREFIX) and "2,4 GHz" in a.answer
    assert "sorunuzu yanıtlamayabilir" in a.answer
