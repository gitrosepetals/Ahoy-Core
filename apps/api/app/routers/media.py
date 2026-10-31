import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.deps import AppSettings, CrewUser, DbSession, TenantClientId, require_roles
from app.models import MediaAsset, MediaType, UserRole
from app.schemas import AuthUser, MediaAssetOut, MediaRegisterRequest

router = APIRouter(prefix="/clients", tags=["media"])


def _to_out(asset: MediaAsset) -> MediaAssetOut:
    return MediaAssetOut(
        asset_id=asset.asset_id,
        client_id=asset.client_id,
        storage_url=asset.storage_url,
        thumbnail_url=asset.thumbnail_url,
        asset_type=asset.asset_type,
        ai_tags=asset.ai_tags,
        is_used=bool(asset.is_used),
        created_at=asset.created_at,
    )


@router.get("/{client_id}/media", response_model=list[MediaAssetOut])
async def list_media(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = Depends(require_roles(UserRole.crew, UserRole.captain)),
) -> list[MediaAssetOut]:
    result = await db.execute(
        select(MediaAsset)
        .where(MediaAsset.client_id == client_id)
        .order_by(MediaAsset.created_at.desc())
    )
    return [_to_out(a) for a in result.scalars().all()]


@router.post("/{client_id}/media", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
async def register_media(
    client_id: TenantClientId,
    body: MediaRegisterRequest,
    db: DbSession,
    _crew: CrewUser,
) -> MediaAssetOut:
    asset = MediaAsset(
        client_id=client_id,
        storage_url=body.storage_url,
        thumbnail_url=body.thumbnail_url,
        asset_type=body.asset_type,
        ai_tags=body.ai_tags,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return _to_out(asset)


@router.post(
    "/{client_id}/media/upload",
    response_model=MediaAssetOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    client_id: TenantClientId,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
    file: UploadFile = File(...),
    asset_type: MediaType = Form(MediaType.raw_photo),
) -> MediaAssetOut:
    upload_root = Path(settings.upload_dir)
    if not upload_root.is_absolute():
        upload_root = Path.cwd() / upload_root
    client_dir = upload_root / str(client_id)
    client_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    asset_id = uuid.uuid4()
    dest = client_dir / f"{asset_id}{suffix}"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    dest.write_bytes(data)

    public_base = settings.public_api_base_url.rstrip("/")
    storage_url = f"{public_base}/uploads/{client_id}/{dest.name}"

    asset = MediaAsset(
        asset_id=asset_id,
        client_id=client_id,
        storage_url=storage_url,
        thumbnail_url=storage_url,
        asset_type=asset_type,
        ai_tags=["uploaded"],
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return _to_out(asset)
