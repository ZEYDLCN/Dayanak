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
    # Ret metni modelin serbest yazdığı değil, sabit ve güvenli mesajdır
    assert not a.answerable and a.sources == [] and a.answer == NO_INFO


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


def test_llm_failure_does_not_quote_unrelated_bluetooth_section(kb, settings):
    svc = AnswerService(kb, settings, generator=FakeGen(error=RuntimeError("boom")))
    a = svc.ask("Lumora Hub Bluetooth 5.0 destekliyor mu?")
    assert a.mode == "extractive-fallback"
    assert not a.answerable and a.answer == NO_INFO and a.sources == []


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


def test_orange_led_question_retrieves_do_not_unplug_instruction(kb):
    result = kb.retrieve("Turuncu LED yanarken Hub’ın fişini çekebilir miyim?")
    assert result.sufficient
    assert result.hits[0].chunk.section == "Güncelleme Sırasında Yapılmaması Gerekenler"
    assert "fişini çekmeyin" in result.hits[0].chunk.text


def test_ungrounded_number_in_llm_answer_is_rejected(kb, settings):
    """Model kaynakta olmayan bir sayı uydurursa kullanıcıya gösterilmez."""
    svc = AnswerService(kb, settings, generator=FakeGen(Generation(True, "İade süresi 45 gündür.", [0])))
    a = svc.ask("İade süresi kaç gün?")
    assert not a.answerable and a.mode == "llm-rejected" and a.sources == []
    assert "45" in a.retrieval["guard"]


def test_number_echoed_from_question_is_allowed(kb, settings):
    gen = FakeGen(Generation(True, "Hayır, 14 gün değil; iade süresi 30 gündür.", [0]))
    a = AnswerService(kb, settings, generator=gen).ask("İade süresi 14 gün, doğru mu?")
    assert a.answerable and a.mode == "llm"


def test_self_contradicting_llm_answer_is_rejected(kb, settings):
    gen = FakeGen(Generation(True, "Bu konuda yeterli bilgi bulunmuyor.", [0]))
    a = AnswerService(kb, settings, generator=gen).ask("Telefon desteği hafta sonu açık mı?")
    assert not a.answerable and a.answer == NO_INFO and a.sources == []


def test_cited_source_is_extended_with_passage_that_grounds_the_number(kb):
    """Model 30 gün'ü söyleyip yalnızca kargo bölümünü atıf yaparsa, 30'u içeren bölüm kaynaklara eklenir."""
    from app.grounding import check_numbers

    hits = {h.chunk.chunk_id: h for h in kb.index.search("iade süresi kargo ücreti", k=20)}
    cargo, period = hits["kargo-ve-teslimat#2"], hits["iade-proseduru-v2#2"]
    ok = check_numbers("soru", "İade süresi 30 gün, kargo 49,90 TL.", [cargo], [cargo, period])
    assert ok.ok and period in ok.support
    bad = check_numbers("soru", "İade süresi 45 gün.", [cargo], [cargo, period])
    assert not bad.ok and bad.ungrounded == {"45"}


def test_llm_mode_lets_llm_judge_borderline_retrieval(kb, settings):
    """Skor eşiği geçen ama kapsaması düşük soru: LLM'siz modda ret, LLM modunda LLM'e gider."""
    question = "Aboneliğimi iptal edersem paramı geri alabilir miyim?"
    r = kb.retrieve(question)
    assert r.plausible and not r.sufficient
    gen = FakeGen(Generation(True, "Kalan döneme ait kısmi ücret iadesi yapılmaz.", [0]))
    assert AnswerService(kb, settings, generator=gen).ask(question).mode == "llm"
    assert gen.calls == 1
    assert AnswerService(kb, settings).ask(question).mode == "no-retrieval"
