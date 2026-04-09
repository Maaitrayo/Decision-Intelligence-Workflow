from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./data/decision_intelligence.db"
    max_agent_input: int = 20
    signal_keywords: str = "agent,multimodal,vision,safety,robotics"
    hn_timeout: int = 8
    arxiv_max_age_hours: int = 48
    score_threshold_high: float = 0.65
    score_threshold_medium: float = 0.35
    score_threshold_low: float = 0.15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
