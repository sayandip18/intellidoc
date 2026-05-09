from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    cohere_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://intellidoc:intellidoc@localhost:5432/intellidoc"
    sync_database_url: str = "postgresql+psycopg2://intellidoc:intellidoc@localhost:5432/intellidoc"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO / S3
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_upload_bucket: str = "intellidoc-uploads"
    minio_archive_bucket: str = "intellidoc-archive"
    minio_region: str = "us-east-1"

    # Pipeline
    chunk_size: int = 512
    chunk_overlap: int = 64
    llm_model: str = "gpt-4o-mini"
    crag_max_retries: int = 3
    faithfulness_threshold: float = 0.7

    # Celery task retry settings
    max_retries: int = 3
    retry_backoff: int = 60


settings = Settings()
