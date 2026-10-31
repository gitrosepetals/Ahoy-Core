from fastapi import APIRouter, Depends

from app.deps import AppSettings, CrewUser, DbSession, TenantClientId, require_roles
from app.models import BrandProfile, UserRole
from app.schemas import AuthUser, BrandProfileOut, BrandProfileUpdate
from app.services.brand_context import get_or_create_brand_profile, recompute_embedding

router = APIRouter(prefix="/clients", tags=["brand"])


def _to_out(profile: BrandProfile) -> BrandProfileOut:
    return BrandProfileOut(
        profile_id=profile.profile_id,
        client_id=profile.client_id,
        brand_voice_guidelines=profile.brand_voice_guidelines,
        target_zip_codes=profile.target_zip_codes,
        compliance_rules=profile.compliance_rules,
        services_offered=profile.services_offered,
        has_embedding=profile.context_embedding is not None,
        updated_at=profile.updated_at,
    )


@router.get("/{client_id}/brand-profile", response_model=BrandProfileOut)
async def get_brand_profile(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = Depends(require_roles(UserRole.crew, UserRole.captain)),
) -> BrandProfileOut:
    profile = await get_or_create_brand_profile(db, client_id)
    await db.commit()
    await db.refresh(profile)
    return _to_out(profile)


@router.put("/{client_id}/brand-profile", response_model=BrandProfileOut)
async def put_brand_profile(
    client_id: TenantClientId,
    body: BrandProfileUpdate,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> BrandProfileOut:
    profile = await get_or_create_brand_profile(db, client_id)
    profile.brand_voice_guidelines = body.brand_voice_guidelines
    profile.target_zip_codes = body.target_zip_codes
    profile.compliance_rules = body.compliance_rules
    profile.services_offered = body.services_offered
    await recompute_embedding(settings, profile)
    await db.commit()
    await db.refresh(profile)
    return _to_out(profile)
