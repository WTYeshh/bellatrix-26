import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "AEGIS Privacy-First AIOps Observability Platform"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Database: Use local SQLite async by default for zero-network dependency & reliability,
    # or override with DATABASE_URL (e.g. PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./aegis_central.db"
    )
    
    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "aegis-enterprise-secret-key-2026-super-secure")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Ingestion & Security
    ALLOWED_PAYLOAD_MAX_BYTES: int = 1024 * 1024  # 1 MB max payload
    COLLECTOR_OFFLINE_THRESHOLD_SECONDS: int = 45  # Marked offline after 45s of missed heartbeats
    
    # AIOps Configuration
    BASELINE_WINDOW_SIZE: int = 30
    ANOMALY_ZSCORE_THRESHOLD: float = 2.5
    ANOMALY_MAD_THRESHOLD: float = 3.0

    # AI & LLM Engine (Google Gemini)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

settings = Settings()
