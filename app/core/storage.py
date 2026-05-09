import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_buckets(client) -> None:
    for bucket in (settings.minio_upload_bucket, settings.minio_archive_bucket):
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError:
            client.create_bucket(Bucket=bucket)
