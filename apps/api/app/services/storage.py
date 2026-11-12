"""File storage for uploads (media vault photos, voice notes).

Two backends, chosen by `STORAGE_BACKEND`:
- `local` (default): files under `UPLOAD_DIR`, served by the API at `/uploads/...`.
- `supabase`: Supabase Storage over its REST API (public bucket). Use this in production, where
  the API host's disk is wiped on every redeploy.

Both return the public URL that is stored on the row (`media_assets.storage_url`,
`content_queue.voice_feedback_url`).
"""

from pathlib import Path

import httpx

from app.config import Settings


class StorageError(RuntimeError):
    pass


def upload_root(settings: Settings) -> Path:
    root = Path(settings.upload_dir)
    return root if root.is_absolute() else Path.cwd() / root


async def save_file(
    settings: Settings, *, key: str, data: bytes, content_type: str | None = None
) -> str:
    """Store `data` at `key` (e.g. `<client_id>/<uuid>.jpg`) and return its public URL."""
    if settings.storage_backend == "supabase":
        return await _save_supabase(settings, key=key, data=data, content_type=content_type)
    dest = upload_root(settings) / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return f"{settings.public_api_base_url.rstrip('/')}/uploads/{key}"


async def _save_supabase(
    settings: Settings, *, key: str, data: bytes, content_type: str | None
) -> str:
    base = settings.supabase_url.rstrip("/")
    if not (base and settings.supabase_service_key):
        raise StorageError("STORAGE_BACKEND=supabase needs SUPABASE_URL and SUPABASE_SERVICE_KEY")
    bucket = settings.supabase_bucket
    async with httpx.AsyncClient(timeout=30) as http:
        res = await http.post(
            f"{base}/storage/v1/object/{bucket}/{key}",
            headers={
                "Authorization": f"Bearer {settings.supabase_service_key}",
                "Content-Type": content_type or "application/octet-stream",
                "x-upsert": "true",
            },
            content=data,
        )
    if res.status_code >= 400:
        raise StorageError(f"Supabase upload failed ({res.status_code}): {res.text[:200]}")
    return f"{base}/storage/v1/object/public/{bucket}/{key}"
