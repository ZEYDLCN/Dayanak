from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    llm_provider: str = "anthropic"  # "anthropic" | "nvidia" | "gemini" | "none"
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5-5"
    nvidia_api_key: str = ""
    nvidia_model: str = "openai/gpt-oss-20b"
    nvidia_timeout_seconds: float = 15.0
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_timeout_seconds: float = 20.0
    nvidia_temperature: float = 0.0  # tekrarlanabilirlik: ayni soru ayni yaniti versin
    nvidia_reasoning_effort: str = "low"  # yalnizca gpt-oss: low | medium | high

    # Halusinasyon korumalari
    require_evidence: bool = True  # model, yaniti destekleyen cumleyi bolumden aynen kopyalamali
    verify_answers: bool = False  # ikinci LLM cagrisi: kanit soruyu dogrudan yanitliyor mu?

    docs_dir: Path = ROOT / "data" / "docs"

    top_k: int = 4
    llm_context_passages: int = 2  # LLM'e verilen en iyi bölüm sayısı (top_k'nin alt kümesi)

    # Arama: "bm25" (yalnizca sozcuk) veya "hybrid" (BM25 + yerel gomme, RRF). Gomme yuklenemezse BM25'e dusulur.
    retriever: str = "bm25"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    cache_dir: Path = ROOT / ".cache"  # gomme onbellegi ve indirilen modeller (git disi)
    rrf_k: int = 60
    # LLM varken "LLM'e git" kapisina anlamsal benzerlik de eklenir (0 = kapali). Model basina kalibre edilir.
    min_semantic: float = 0.0
    # Cevapsiz karari icin esikler (bkz. README "Cevapsiz tespiti")
    min_score: float = 5.0
    min_coverage: float = 0.27

    @property
    def use_llm(self) -> bool:
        return (
            (self.llm_provider == "anthropic" and bool(self.anthropic_api_key))
            or (self.llm_provider == "nvidia" and bool(self.nvidia_api_key))
            or (self.llm_provider == "gemini" and bool(self.gemini_api_key))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
