from functools import lru_cache
from os import getenv


class Settings:
    def __init__(self) -> None:
        self.openai_api_key = getenv("OPENAI_API_KEY")
        self.openai_model = getenv("OPENAI_MODEL", "gpt-4o-mini")


@lru_cache
def get_settings() -> Settings:
    return Settings()
