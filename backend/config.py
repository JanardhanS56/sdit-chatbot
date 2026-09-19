from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: Optional[str] = None
    
    # LLM Settings
    llm_api_key: str
    llm_api_base: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemini-2.0-flash-001"
    
    # Embedding (Optional)
    embedding_api_key: Optional[str] = None
    embedding_api_base: Optional[str] = None
    embedding_model: str = "openai/text-embedding-3-small"
    
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = Path(__file__).resolve().parent / ".env"


settings = Settings()

# force reload
