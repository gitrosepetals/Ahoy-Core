"""1.2.0: pluggable file storage (local disk / Supabase Storage)."""

import httpx
import pytest

from app.config import Settings
from app.services import storage
from app.services.storage import StorageError, save_file


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_backend_writes_and_returns_uploads_url(tmp_path) -> None:
    s = Settings(storage_backend="local", upload_dir=str(tmp_path), public_api_base_url="http://x/")
    url = await save_file(s, key="c1/voice/a.webm", data=b"abc", content_type="audio/webm")
    assert url == "http://x/uploads/c1/voice/a.webm"
    assert (tmp_path / "c1" / "voice" / "a.webm").read_bytes() == b"abc"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_supabase_backend_posts_to_storage_api(monkeypatch) -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["type"] = request.headers["content-type"]
        seen["body"] = request.content
        return httpx.Response(200, json={"Key": "ok"})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        storage.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    s = Settings(
        storage_backend="supabase",
        supabase_url="https://abc.supabase.co/",
        supabase_service_key="svc",
        supabase_bucket="ahoy-media",
    )
    url = await save_file(s, key="c1/p.jpg", data=b"img", content_type="image/jpeg")
    assert seen["url"] == "https://abc.supabase.co/storage/v1/object/ahoy-media/c1/p.jpg"
    assert seen["auth"] == "Bearer svc" and seen["type"] == "image/jpeg" and seen["body"] == b"img"
    assert url == "https://abc.supabase.co/storage/v1/object/public/ahoy-media/c1/p.jpg"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_supabase_backend_requires_config_and_surfaces_errors(monkeypatch) -> None:
    with pytest.raises(StorageError):
        await save_file(Settings(storage_backend="supabase"), key="k", data=b"x")

    real = httpx.AsyncClient
    monkeypatch.setattr(
        storage.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(lambda r: httpx.Response(403)), **kw),
    )
    s = Settings(storage_backend="supabase", supabase_url="https://a.co", supabase_service_key="k")
    with pytest.raises(StorageError, match="403"):
        await save_file(s, key="k", data=b"x")
