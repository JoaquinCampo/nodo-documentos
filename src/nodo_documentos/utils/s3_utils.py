import boto3
from botocore.client import BaseClient
from pydantic import BaseModel

from nodo_documentos.utils.settings import s3_settings


class PresignedUrl(BaseModel):
    url: str
    expires_in: int


def create_s3_client() -> BaseClient:
    """Return an S3 client configured via environment variables."""

    return boto3.client(
        "s3",
        region_name=s3_settings.region_name,
        endpoint_url=s3_settings.endpoint_url,
    )


def build_s3_uri(key: str) -> str:
    """Return the canonical S3 URI for a given object key."""

    return f"s3://{s3_settings.bucket_name}/{key}"


def generate_presigned_put_url(
    *,
    key: str,
    content_type: str | None = None,
    expires_in: int | None = None,
) -> PresignedUrl:
    """
    Create a presigned URL that allows uploading an object via HTTP PUT.

    The helper passes through both the bucket and object key, as well as the
    optional content-type header the front-end might need to send.
    """

    client = create_s3_client()
    params: dict[str, str] = {
        "Bucket": s3_settings.bucket_name,
        "Key": key,
    }
    if content_type:
        params["ContentType"] = content_type

    expiration = expires_in or s3_settings.presigned_expiration_seconds

    url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params=params,
        ExpiresIn=expiration,
    )
    return PresignedUrl(url=url, expires_in=expiration)
