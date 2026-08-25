import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Seixas AI"
    ENVIRONMENT: str = "development"
    
    # Banco de Dados: SQLite local por padrão para dev/testes, PostgreSQL em produção
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./seixas_local.db")
    
    # Message Broker RabbitMQ & Redis Backend
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Object Storage MinIO / S3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_PROCESSES: str = "judicial-processes"
    MINIO_BUCKET_POLICIES: str = "internal-policies"
    MINIO_SECURE: bool = False
    
    # APIs de IA (Fallback & Extração)
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_VISION_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    LLM_MODEL: str = "openai/gpt-4o-mini"
    
    # Thresholds Operacionais
    NATIVE_CHAR_COUNT_MIN: int = 30
    NATIVE_GARBAGE_RATIO_MAX: float = 0.05
    OCR_CONFIDENCE_THRESHOLD: float = 0.85
    EVIDENCE_MATCH_RATIO_MIN: float = 0.85

settings = Settings()
