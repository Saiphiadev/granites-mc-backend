"""Configuration centralisée du backend IA Granites MC."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Odoo
    odoo_url: str = "https://granites-mc.odoo.com"
    odoo_db: str = "granites-mc"
    odoo_user: str = ""
    odoo_password: str = ""

    # Anthropic (Claude API)
    anthropic_api_key: str = ""

    # Deepgram (transcription)
    deepgram_api_key: str = ""

    # Server
    port: int = 8000
    env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
