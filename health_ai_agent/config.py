from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):

    # Database URL (fetches the required fields from the .env file)
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    
    # Model
    model_name: str = "m42-health/med42-v2-8b"
    model_cache_dir: Optional[str] = None
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Logging
    log_level: str = "INFO"

    @property # Required for development and production (I had previously hardcoded the database url)
    def database_url(self) -> str:
        """Construct database URL from components"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    # Hugging Face
    hf_token: Optional[str] = None
    use_api: bool = True


settings = Settings()