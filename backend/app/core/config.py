from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RDNA_AI_Guard"
    API_V1_STR: str = "/api/v1"
    OLLAMA_HOST: str = "http://localhost:11434"
    GEMMA_MODEL: str = "gemma4:12b"
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:guard_password@localhost:5432/rdna_guard"
    )

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()