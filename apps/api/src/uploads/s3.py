"""S3-compatible storage helpers (MinIO in dev, R2 in prod).

We use boto3's synchronous client wrapped in ``run_in_threadpool`` for the
async routes — presigning is a millisecond-scale operation, no need for
aiobotocore's extra machinery.  Two endpoints matter:

* ``s3_endpoint`` — what the API container reaches (e.g. ``http://minio:9000``).
  Used for HEAD / metadata operations the API itself performs.
* ``s3_public_endpoint`` — what the *browser* reaches (e.g.
  ``http://localhost:9000``).  Baked into presigned URLs so the client can
  actually PUT to that host.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from src.config import settings


@lru_cache(maxsize=2)
def _client(*, public: bool) -> Any:
    """boto3 S3 client.  Cached per (public flag) so we don't recreate
    sessions for every request."""
    endpoint = settings.s3_public_endpoint if public else settings.s3_endpoint
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        # path-style needed for MinIO; R2 supports virtual-hosted but path-style
        # works there too, so we keep one config.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def presign_put(
    *,
    key: str,
    content_type: str,
    max_bytes: int,
    expires_in: int = 600,
) -> dict[str, Any]:
    """Returns a presigned POST policy (URL + form fields) the browser uses to
    upload directly to S3/MinIO without proxying through the API.

    Constraints (``content-type`` exact match, ``content-length-range``) are
    enforced by the storage server, not us — so a malicious client can't grow
    the file size or change its type after we've signed."""
    client = _client(public=True)
    try:
        post = client.generate_presigned_post(
            Bucket=settings.s3_bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, max_bytes],
            ],
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"S3 presign failed: {e}") from e

    return {
        "url": post["url"],
        "fields": post["fields"],
        "public_url": public_url(key),
        "key": key,
    }


def public_url(key: str) -> str:
    """Browser-reachable URL for a public-read object."""
    return f"{settings.s3_public_endpoint.rstrip('/')}/{settings.s3_bucket}/{key}"


def put_object(*, key: str, body: bytes, content_type: str) -> str:
    """Direct server-side upload (no presign).  Used by the worker to push
    generated PDFs.  Returns the browser-reachable public URL."""
    client = _client(public=False)
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
    return public_url(key)


def head_object(key: str) -> dict[str, Any] | None:
    """Confirm an uploaded object exists.  Returns ``None`` when it's missing
    (S3 raises 404 / NoSuchKey)."""
    client = _client(public=False)
    try:
        return client.head_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
