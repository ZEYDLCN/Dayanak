from datetime import date

from app.answer import NO_INFO, AnswerService
from app.llm import Generation


class FakeGen:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    def generate(self, question, hits):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def test_unanswerable_never_reaches_llm(kb, settings):
    gen = FakeGen(Generation(True, "uydurma", [0]))
    svc = AnswerService(kb, settings, generator=gen)
    a = svc.ask("Apple HomeKit ile uyumlu mu?")
    assert not a.answerable and a.answer == NO_INFO and a.sources == []
    assert gen.calls == 0


def test_llm_abstention_is_respected(kb, settings):
    svc = AnswerService(kb, settings, generator=FakeGen(Generation(False, "Dokümanda yok.", [])))
    a = svc.ask("Telefon desteği hafta sonu açık mı?")
    assert not a.answerable and a.sources == [] and a.answer == "Dokümanda yok."


def test_llm_answer_reports_only_cited_sources(kb, settings):
    svc = AnswerService(kb, settings, generator=FakeGen(Generation(True, "30 gün.", [0])))
    a = svc.ask("İade süresi kaç gün?")
    assert a.mode == "llm" and len(a.sources) == 1
    assert a.sources[0].doc_id == "iade-proseduru-v2"
    assert a.conflicts and a.conflicts[0].discarded[0].section == a.sources[0].section


def test_llm_failure_falls_back_to_extractive(kb, settings):
    svc = AnswerService(kb, settings, generator=FakeGen(error=RuntimeError("boom")))
    a = svc.ask("Hub 5 GHz Wi-Fi ağına bağlanır mı?")
    assert a.mode == "extractive-fallback" and a.answerable
    assert a.sources[0].doc_id == "kurulum-kilavuzu"


def test_extractive_quotes_current_version(service):
    a = service.ask("İade süresi kaç gün?")
    assert "30 gün" in a.answer and "14 gün" not in a.answer
    assert a.sources[0].status == "current"


def test_conflict_not_reported_when_unrelated_section_used(service):
    a = service.ask("Kargo ücretsiz mi?")  # kargo dokümanı cevaplar; iade v1/v2 alakasız
    assert a.sources[0].doc_id == "kargo-ve-teslimat"
    assert a.conflicts == []


def test_as_of_selects_version_in_force(service):
    a = service.ask("İade süresi kaç gün?", as_of=date(2024, 6, 1))
    assert "14 gün" in a.answer and a.sources[0].doc_id == "iade-proseduru-v1"
