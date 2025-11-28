"""Configuration settings for the LLM Quiz Solver application."""
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from pydantic_settings import BaseSettings
    USE_PYDANTIC_SETTINGS = True
except ImportError:
    # Fallback to pydantic BaseSettings if pydantic_settings not available
    try:
        from pydantic import BaseSettings
        USE_PYDANTIC_SETTINGS = False
    except ImportError:
        # If neither is available, use a simple class-based approach
        BaseSettings = None
        USE_PYDANTIC_SETTINGS = None


if BaseSettings is not None:
    if USE_PYDANTIC_SETTINGS:
        # Pydantic v2 with pydantic-settings 2.1.0
        class Settings(BaseSettings):
            """Application settings loaded from environment variables."""
            
            secret_key: str = "default-secret-key-change-me"
            openrouter_api_key: Optional[str] = None
            aipipe_api_url: str = "https://aipipe.org/openrouter/v1"
            database_path: str = "./quiz_data.db"
            execution_timeout: int = 180  # 3 minutes
            
            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"
                case_sensitive = False
    else:
        # Pydantic v1 BaseSettings (fallback)
        class Settings(BaseSettings):
            """Application settings loaded from environment variables."""
            
            secret_key: str = "default-secret-key-change-me"
            openrouter_api_key: Optional[str] = None
            aipipe_api_url: str = "https://aipipe.org/openrouter/v1"
            database_path: str = "./quiz_data.db"
            execution_timeout: int = 180  # 3 minutes
            
            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"
                case_sensitive = False
    
    settings = Settings()
else:
    # Simple fallback using environment variables directly
    class Settings:
        """Application settings loaded from environment variables."""
        
        def __init__(self):
            self.secret_key: str = os.getenv("SECRET_KEY", "default-secret-key-change-me")
            self.openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
            self.aipipe_api_url: str = os.getenv("AIPIPE_API_URL", "https://aipipe.org/openrouter/v1")
            self.database_path: str = os.getenv("DATABASE_PATH", "./quiz_data.db")
            self.execution_timeout: int = int(os.getenv("EXECUTION_TIMEOUT", "180"))
    
    settings = Settings()
