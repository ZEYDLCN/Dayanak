import json

import httpx

from app.answer import AnswerService
from app.config import Settings
from app.llm import NvidiaGenerator


def test_nvidia_generator_uses_retrieved_passages_and_cites_source(kb):
    settings = Settings(
        _env_file=None, llm_provider="nvidia", nvidia_api_key="test-key",
        nvidia_model="nvidia/nemotron-3.5-lightning-30b-a3b",
    )

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url == NvidiaGenerator.URL
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        assert "[3]" not in payload["messages"][1]["content"]
        assert "İade Süresi" in payload["messages"][1]["content"]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "answerable": True, "answer": "İade süresi 30 gündür.", "used_passages": [1]
        })}}]})

    client = httpx.Client(transport=httpx.MockTransport(respond))
    generator = NvidiaGenerator(settings, client=client)
    answer = AnswerService(kb, settings, generator=generator).ask("İade süresi kaç gün?")

    assert settings.use_llm
    assert answer.mode == "llm"
    assert answer.answerable and "30 gün" in answer.answer
    assert answer.sources[0].doc_id == "iade-proseduru-v2"
    assert answer.conflicts


def test_gpt_oss_uses_json_output_and_low_reasoning(kb):
    settings = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="test-key")

    def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "openai/gpt-oss-20b"
        assert payload["reasoning_effort"] == "low"
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["max_tokens"] == 512
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps({
                "answerable": True, "answer": "İade süresi 30 gündür.", "used_passages": [1]
            })},
        }]})

    client = httpx.Client(transport=httpx.MockTransport(respond))
    answer = AnswerService(kb, settings, generator=NvidiaGenerator(settings, client=client)).ask(
        "İade süresi kaç gün?"
    )

    assert answer.mode == "llm"
    assert answer.sources[0].doc_id == "iade-proseduru-v2"
