from fastapi import APIRouter
from sqlalchemy import select

from app.deps import CurrentUser, DbSession, TenantClientId
from app.models import Client
from app.schemas import ClientSummary

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientSummary])
async def list_my_clients(user: CurrentUser, db: DbSession) -> list[ClientSummary]:
    if not user.client_ids:
        return []
    result = await db.execute(select(Client).where(Client.client_id.in_(user.client_ids)))
    return [
        ClientSummary(
            client_id=c.client_id,
            business_name=c.business_name,
            industry_vertical=c.industry_vertical,
            tier=c.tier.value,
        )
        for c in result.scalars().all()
    ]


@router.get("/{client_id}", response_model=ClientSummary)
async def get_client(client_id: TenantClientId, db: DbSession) -> ClientSummary:
    result = await db.execute(select(Client).where(Client.client_id == client_id))
    client = result.scalar_one()
    return ClientSummary(
        client_id=client.client_id,
        business_name=client.business_name,
        industry_vertical=client.industry_vertical,
        tier=client.tier.value,
    )
