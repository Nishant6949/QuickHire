import logging
import os

from supabase import create_client

logger = logging.getLogger(__name__)

_client = None
_TRUTHY = {"1", "true", "yes", "on"}


def _is_truthy(value):
    return str(value).strip().lower() in _TRUTHY


def storage_enabled():
    """Toggle Supabase Storage usage.

    - Set ENABLE_SUPABASE_STORAGE=true to force-enable.
    - Set ENABLE_SUPABASE_STORAGE=false to force-disable.
    - If unset, default to disabled on Vercel (Hobby-safe) and enabled elsewhere.
    """
    explicit = os.getenv("ENABLE_SUPABASE_STORAGE")
    if explicit is not None:
        return _is_truthy(explicit)
    return not _is_truthy(os.getenv("VERCEL", ""))


def _get_client():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(url, key)
    return _client


def upload_file(bucket, path, file_bytes, content_type="application/pdf"):
    """Upload a file to Supabase Storage. Returns the public URL."""
    if not storage_enabled():
        return None
    client = _get_client()
    client.storage.from_(bucket).upload(
        path, file_bytes, {"content-type": content_type, "upsert": "true"}
    )
    return client.storage.from_(bucket).get_public_url(path)


def download_file(bucket, path):
    """Download a file from Supabase Storage. Returns bytes."""
    if not storage_enabled():
        raise RuntimeError("Supabase storage is disabled")
    client = _get_client()
    return client.storage.from_(bucket).download(path)


def get_public_url(bucket, path):
    """Return the public URL for a file in Supabase Storage."""
    if not storage_enabled():
        raise RuntimeError("Supabase storage is disabled")
    client = _get_client()
    return client.storage.from_(bucket).get_public_url(path)


def delete_file(bucket, path):
    """Delete a file from Supabase Storage."""
    if not storage_enabled():
        return
    try:
        client = _get_client()
        client.storage.from_(bucket).remove([path])
    except Exception as e:
        logger.warning("Could not delete %s/%s from storage: %s", bucket, path, e)
