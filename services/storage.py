import logging
import os

from supabase import create_client

logger = logging.getLogger(__name__)

_client = None


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
    client = _get_client()
    client.storage.from_(bucket).upload(
        path, file_bytes, {"content-type": content_type, "upsert": "true"}
    )
    return client.storage.from_(bucket).get_public_url(path)


def download_file(bucket, path):
    """Download a file from Supabase Storage. Returns bytes."""
    client = _get_client()
    return client.storage.from_(bucket).download(path)


def delete_file(bucket, path):
    """Delete a file from Supabase Storage."""
    try:
        client = _get_client()
        client.storage.from_(bucket).remove([path])
    except Exception as e:
        logger.warning("Could not delete %s/%s from storage: %s", bucket, path, e)
