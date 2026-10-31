"""Health check — also covered under milestone_a in test_milestone_a.py."""

import pytest
from httpx import AsyncClient


@pytest.mark.milestone_a
@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
