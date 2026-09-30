from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    llm_provider: str = "anthropic"  # "anthropic" | "none"
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5-5"

    docs_dir: Path = ROOT / "data" / "docs"

    top_k: int = 4
    # Cevapsiz karari icin esikler (bkz. README "Cevapsiz tespiti")
    min_score: float = 5.0
    min_coverage: float = 0.27

    @property
    def use_llm(self) -> bool:
        return self.llm_provider == "anthropic" and bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
