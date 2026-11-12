from fastapi import APIRouter
from sqlalchemy import select

from app.deps import CrewUser, CurrentUser, DbSession, TenantClientId
from app.models import AuditEvent, Client, Notification
from app.schemas import AuditEventOut, ClientSummary, NotificationOut
from app.services.kpis import portfolio_kpis

router = APIRouter(prefix="/clients", tags=["clients"])
kpi_router = APIRouter(tags=["kpis"])


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


@router.get("/{client_id}/notifications", response_model=list[NotificationOut])
async def list_notifications(
    client_id: TenantClientId,
    db: DbSession,
    _crew: CrewUser,
) -> list[NotificationOut]:
    """Crew: recent owner notifications (push / SMS / dev log) for delivery troubleshooting."""
    result = await db.execute(
        select(Notification)
        .where(Notification.client_id == client_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return [
        NotificationOut(
            notification_id=n.notification_id,
            kind=n.kind,
            channel=n.channel,
            status=n.status,
            deep_link=n.deep_link,
            body=n.body,
            error=n.error,
            created_at=n.created_at,
        )
        for n in result.scalars().all()
    ]


@router.get("/{client_id}/audit", response_model=list[AuditEventOut])
async def list_audit_events(
    client_id: TenantClientId,
    db: DbSession,
    _crew: CrewUser,
) -> list[AuditEventOut]:
    """Crew: who moved which post / review / integration, newest first (last 100)."""
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.client_id == client_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
    )
    return [
        AuditEventOut(
            audit_id=e.audit_id,
            actor_role=e.actor_role,
            actor_user_id=e.actor_user_id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            action=e.action,
            from_status=e.from_status,
            to_status=e.to_status,
            created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]


@kpi_router.get("/kpis")
async def get_kpis(user: CrewUser, db: DbSession) -> dict:
    """PRD §7 pilot KPIs across the Crew member's clients (admin: all clients)."""
    return await portfolio_kpis(db, user.client_ids)
