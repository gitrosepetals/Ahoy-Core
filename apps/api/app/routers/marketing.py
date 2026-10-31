from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DbSession
from app.models import MarketingLead
from app.schemas import MarketingLeadRequest, MarketingLeadResponse

router = APIRouter(prefix="/marketing", tags=["marketing"])


@router.post("/leads", response_model=MarketingLeadResponse)
async def capture_lead(body: MarketingLeadRequest, db: DbSession) -> MarketingLeadResponse:
    email = str(body.email).strip().lower()
    business = (body.business_name or "").strip() or None
    source = (body.source or "welcome").strip() or "welcome"

    result = await db.execute(select(MarketingLead).where(MarketingLead.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        if business:
            existing.business_name = business
        existing.source = source
        await db.commit()
        return MarketingLeadResponse(ok=True, email=existing.email)

    row = MarketingLead(email=email, business_name=business, source=source)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return MarketingLeadResponse(ok=True, email=row.email)
