from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    llm_provider: str = "anthropic"  # "anthropic" | "nvidia" | "none"
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5-5"
    nvidia_api_key: str = ""
    nvidia_model: str = "openai/gpt-oss-20b"
    nvidia_timeout_seconds: float = 15.0

    docs_dir: Path = ROOT / "data" / "docs"

    top_k: int = 4
    llm_context_passages: int = 2  # LLM'e verilen en iyi bölüm sayısı (top_k'nin alt kümesi)
    # Cevapsiz karari icin esikler (bkz. README "Cevapsiz tespiti")
    min_score: float = 5.0
    min_coverage: float = 0.27

    @property
    def use_llm(self) -> bool:
        return (
            (self.llm_provider == "anthropic" and bool(self.anthropic_api_key))
            or (self.llm_provider == "nvidia" and bool(self.nvidia_api_key))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
