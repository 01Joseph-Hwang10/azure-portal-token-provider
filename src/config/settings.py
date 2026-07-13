from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Server settings
    log_level: str = "INFO"
    api_key: str | None = None

    # Health check daemon settings
    health_check_interval: int = 30  # Interval in seconds
    health_check_url: str = "http://localhost:8000/token"  # URL to ping
