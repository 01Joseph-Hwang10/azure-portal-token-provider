from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env")


class Settings(BaseSettings):
    # Server settings
    log_level: str = "INFO"
    api_key: str | None = None
