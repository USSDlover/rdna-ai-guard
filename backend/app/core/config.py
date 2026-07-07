from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RDNA AI Guard"
    API_V1_STR: str = "/api/v1"
    OLLAMA_HOST: str = "http://localhost:11434"
    GEMMA_MODEL: str = "gemma4:12b"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
