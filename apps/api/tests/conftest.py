import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db import engine
from app.main import app


@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()
    return get_settings()


def _asyncpg_dsn(settings) -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@pytest.fixture(scope="session")
def db_available(settings) -> bool:
    """Ping Postgres without touching the app engine pool."""
    import asyncpg

    async def _ping() -> bool:
        try:
            conn = await asyncpg.connect(_asyncpg_dsn(settings), timeout=3)
            await conn.execute("SELECT 1")
            await conn.close()
            return True
        except Exception:
            return False

    return asyncio.run(_ping())


@pytest_asyncio.fixture
async def client(db_available: bool) -> AsyncClient:
    if not db_available:
        pytest.skip(
            "Postgres not reachable at DATABASE_URL — start Docker db and ensure "
            "Windows postgresql-x64-* is not owning the same port (see docs/incident_log.md)."
        )
    # Dispose so connections are not tied to a closed loop (Windows + asyncpg).
    await engine.dispose()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()
