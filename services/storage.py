import logging
import os

from supabase import create_client

logger = logging.getLogger(__name__)
_client = None
_TRUTHY = {'1', 'true', 'yes', 'on'}


def _is_truthy(value):
    return str(value or '').strip().lower() in _TRUTHY


def storage_enabled():
    """Use Supabase Storage only when explicitly enabled or fully configured.

    Database access and file storage are separate in Supabase. QuickHire can run
    completely without Storage because extracted resume/JD text is stored in SQL.
    """
    explicit = os.getenv('ENABLE_SUPABASE_STORAGE')
    if explicit is not None:
        return _is_truthy(explicit)
    return bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_KEY'))


def _get_client():
    global _client
    if _client is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        if not url or not key:
            raise RuntimeError('SUPABASE_URL and SUPABASE_KEY must be set to use Supabase Storage')
        _client = create_client(url, key)
    return _client


def upload_file(bucket, path, file_bytes, content_type='application/pdf'):
    if not storage_enabled():
        logger.info('Supabase Storage disabled; retaining extracted content in database only.')
        return None
    client = _get_client()
    client.storage.from_(bucket).upload(path, file_bytes, {'content-type': content_type, 'upsert': 'true'})
    return client.storage.from_(bucket).get_public_url(path)


def delete_file(bucket, path):
    if not storage_enabled():
        return
    try:
        _get_client().storage.from_(bucket).remove([path])
    except Exception as exc:
        logger.warning('Could not delete %s/%s from storage: %s', bucket, path, exc)
