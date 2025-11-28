# /mnt/data/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    openrouter_api_key: str = ""
    aipipe_api_url: str = "https://aipipe.org/openrouter/v1"
    database_path: str = "./quiz_data.db"
    execution_timeout: int = 180

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
