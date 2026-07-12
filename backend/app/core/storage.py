from datetime import timedelta
from io import BytesIO
from minio import Minio
from app.core.config import settings

_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)


def ensure_bucket() -> None:
    if not _client.bucket_exists(settings.MINIO_BUCKET):
        _client.make_bucket(settings.MINIO_BUCKET)


def upload_file(object_key: str, data: bytes, content_type: str | None) -> None:
    ensure_bucket()
    _client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )


def get_presigned_download_url(object_key: str, expires_minutes: int = 15) -> str:
    return _client.presigned_get_object(
        settings.MINIO_BUCKET, object_key, expires=timedelta(minutes=expires_minutes)
    )


def delete_file(object_key: str) -> None:
    _client.remove_object(settings.MINIO_BUCKET, object_key)
