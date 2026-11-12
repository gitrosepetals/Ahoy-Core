import asyncio
import secrets
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.config import get_settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import Client


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


@pytest_asyncio.fixture
async def db_session(db_available: bool):
    """Direct ORM session for tests that need rows the API can't create (e.g. POS clients)."""
    if not db_available:
        pytest.skip("Postgres not reachable at DATABASE_URL")
    await engine.dispose()
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


CAPTAIN_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CREW_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest_asyncio.fixture
async def temp_client(db_session):
    """A throwaway client owned by the seeded Captain/Crew, with tracking number + form key."""
    client = Client(
        business_name=f"0.10 Test Co {uuid.uuid4().hex[:6]}",
        industry_vertical="Test",
        owner_user_id=CAPTAIN_USER_ID,
        assigned_crew_id=CREW_USER_ID,
        twilio_tracking_number=f"+1555{secrets.randbelow(10**7):07d}",
        forward_to_number="+15557654321",
        lead_form_key=secrets.token_urlsafe(12),
        average_ticket_value=Decimal("100.00"),
        conversion_rate_estimate=Decimal("0.50"),
        timezone="America/Chicago",
    )
    db_session.add(client)
    await db_session.commit()
    client_id = client.client_id  # tests may roll back, expiring the instance
    yield client
    await db_session.rollback()
    await db_session.execute(delete(Client).where(Client.client_id == client_id))
    await db_session.commit()
