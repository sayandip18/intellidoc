from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """
    All values can be overridden via environment variables.
    e.g.  REDIS_URL=redis://redis:6379/0
    """

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # Celery
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: list[str] = ["json"]
    celery_timezone: str = "UTC"
    celery_enable_utc: bool = True
    celery_task_track_started: bool = True
    celery_task_acks_late: bool = True          # re-queue on hard crash
    celery_worker_prefetch_multiplier: int = 1  # fair dispatch for long tasks
    celery_task_time_limit: int = 600           # hard kill after 10 min
    celery_task_soft_time_limit: int = 540      # SoftTimeLimitExceeded at 9 min
    celery_result_expires: int = 3_600          # 1 hour

    # -------------------------------------------------------------- OpenAI
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        "text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )

    # --------------------------------------------------------------- Cohere
    cohere_api_key: str = Field(..., alias="COHERE_API_KEY")

    # ------------------------------------------------------------ Postgres
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/intellidoc",
        alias="DATABASE_URL",
    )

    # --------------------------------------------------------- Chunking
    chunk_size: int = Field(512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(64, alias="CHUNK_OVERLAP")

    # ------------------------------------------------------------ MinIO / S3
    minio_endpoint: str = Field("http://localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field("minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("minioadmin", alias="MINIO_SECRET_KEY")
    minio_upload_bucket: str = Field("intellidoc-uploads", alias="MINIO_UPLOAD_BUCKET")
    minio_archive_bucket: str = Field("intellidoc-archive", alias="MINIO_ARCHIVE_BUCKET")
    minio_region: str = Field("us-east-1", alias="MINIO_REGION")

    # ---------------------------------------------------- Retry policy
    max_retries: int = 3
    retry_backoff: int = 5  # seconds

    class Config:
        env_file = ".env"
        populate_by_name = True

    @property
    def s3_client_kwargs(self) -> dict:
        return {
            "endpoint_url": self.minio_endpoint,
            "aws_access_key_id": self.minio_access_key,
            "aws_secret_access_key": self.minio_secret_key,
            "region_name": self.minio_region,
        }

    @property
    def celery_config(self) -> dict:
        return {
            "broker_url": self.redis_url,
            "result_backend": self.redis_url,
            "task_serializer": self.celery_task_serializer,
            "result_serializer": self.celery_result_serializer,
            "accept_content": self.celery_accept_content,
            "timezone": self.celery_timezone,
            "enable_utc": self.celery_enable_utc,
            "task_track_started": self.celery_task_track_started,
            "task_acks_late": self.celery_task_acks_late,
            "worker_prefetch_multiplier": self.celery_worker_prefetch_multiplier,
            "task_time_limit": self.celery_task_time_limit,
            "task_soft_time_limit": self.celery_task_soft_time_limit,
            "result_expires": self.celery_result_expires,
        }


settings = WorkerSettings()  # type: ignore[call-arg]