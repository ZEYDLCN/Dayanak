import pytest

from app.answer import AnswerService
from app.config import Settings
from app.retrieval import KnowledgeBase


@pytest.fixture(scope="session")
def settings() -> Settings:
    # .env'den bağımsız: LLM kapalı, eşikler varsayılan
    return Settings(_env_file=None, llm_provider="none", anthropic_api_key="")


@pytest.fixture(scope="session")
def kb(settings) -> KnowledgeBase:
    return KnowledgeBase(settings)


@pytest.fixture()
def service(kb, settings) -> AnswerService:
    return AnswerService(kb, settings)
