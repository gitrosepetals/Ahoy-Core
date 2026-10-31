from fastapi import APIRouter, HTTPException, status

from app.deps import AppSettings, CrewUser, DbSession, TenantClientId
from app.schemas import CampaignGenerateRequest, ContentQueueOut
from app.services.campaigns import generate_campaign_posts

router = APIRouter(prefix="/clients", tags=["campaigns"])


def _post_out(post) -> ContentQueueOut:
    return ContentQueueOut(
        post_id=post.post_id,
        client_id=post.client_id,
        asset_id=post.asset_id,
        channel=post.channel,
        caption_text=post.caption_text,
        scheduled_publish_at=post.scheduled_publish_at,
        status=post.status,
        client_feedback=post.client_feedback,
        generation_meta=post.generation_meta,
        created_at=post.created_at,
    )


@router.post(
    "/{client_id}/campaigns/generate",
    response_model=list[ContentQueueOut],
    status_code=status.HTTP_201_CREATED,
)
async def generate_campaign(
    client_id: TenantClientId,
    body: CampaignGenerateRequest,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> list[ContentQueueOut]:
    try:
        posts = await generate_campaign_posts(
            db,
            settings,
            client_id=client_id,
            asset_ids=body.asset_ids,
            channels=body.channels,
            days=body.days,
            count=body.count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    for p in posts:
        await db.refresh(p)
    return [_post_out(p) for p in posts]
