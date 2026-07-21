from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

class Settings(BaseSettings):
    LLM_API_KEY: str
    DATABASE_URL: str
    SERVICE_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()