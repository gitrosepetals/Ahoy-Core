import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.deps import AppSettings, CrewUser, DbSession, TenantClientId, require_roles
from app.models import MediaAsset, MediaType, UserRole
from app.schemas import AuthUser, MediaAssetOut, MediaRegisterRequest
from app.services.llm import tag_asset
from app.services.storage import StorageError, save_file

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
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    asset_id = uuid.uuid4()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    name = f"{asset_id}{suffix}"
    try:
        storage_url = await save_file(
            settings, key=f"{client_id}/{name}", data=data, content_type=file.content_type
        )
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    tags, _tag_meta = await tag_asset(
        settings, filename=file.filename or name, data=data, content_type=file.content_type
    )

    asset = MediaAsset(
        asset_id=asset_id,
        client_id=client_id,
        storage_url=storage_url,
        thumbnail_url=storage_url,
        asset_type=asset_type,
        ai_tags=tags,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return _to_out(asset)
