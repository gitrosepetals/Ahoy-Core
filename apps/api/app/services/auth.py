import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuthMagicLink, Client, Session, User, UserRole
from app.schemas import AuthUser

logger = logging.getLogger(__name__)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_access_token(
    *,
    user: User,
    client_ids: list[uuid.UUID],
    settings: Settings,
    jti: str | None = None,
) -> tuple[str, datetime, str]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=settings.jwt_ttl_hours)
    token_jti = jti or secrets.token_urlsafe(16)
    payload = {
        "sub": str(user.user_id),
        "role": user.role.value,
        "email": user.email,
        "client_ids": [str(cid) for cid in client_ids],
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at, token_jti


def decode_access_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def resolve_client_ids(db: AsyncSession, user: User) -> list[uuid.UUID]:
    if user.role == UserRole.captain:
        result = await db.execute(select(Client.client_id).where(Client.owner_user_id == user.user_id))
        return list(result.scalars().all())
    if user.role == UserRole.crew:
        result = await db.execute(select(Client.client_id).where(Client.assigned_crew_id == user.user_id))
        return list(result.scalars().all())
    if user.role == UserRole.admin:
        result = await db.execute(select(Client.client_id))
        return list(result.scalars().all())
    # deckhand: no tenant ownership in MVP scaffolding
    return []


async def find_user_for_magic_link(
    db: AsyncSession,
    *,
    phone_number: str | None,
    email: str | None,
) -> User | None:
    clauses = []
    if phone_number:
        clauses.append(User.phone_number == phone_number)
    if email:
        clauses.append(User.email == email)
    if not clauses:
        return None
    result = await db.execute(select(User).where(or_(*clauses)))
    return result.scalar_one_or_none()


async def issue_magic_link(
    db: AsyncSession,
    *,
    user: User,
    redirect_path: str,
    settings: Settings,
) -> tuple[str, AuthMagicLink]:
    raw = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.magic_link_ttl_minutes)
    link = AuthMagicLink(
        user_id=user.user_id,
        token_hash=hash_token(raw),
        redirect_path=redirect_path or "/queue",
        expires_at=expires_at,
    )
    db.add(link)
    await db.commit()

    base = settings.ship_app_base_url if user.role == UserRole.captain else settings.crew_app_base_url
    verify_url = f"{base}/auth/verify?token={raw}"

    if settings.auth_dev_mode or not settings.twilio_account_sid:
        logger.info("DEV magic link for %s (%s): %s", user.email, user.role.value, verify_url)
    else:
        await _send_twilio_sms(user.phone_number, verify_url, settings)

    return verify_url, link


async def _send_twilio_sms(phone: str | None, verify_url: str, settings: Settings) -> None:
    if not phone:
        raise ValueError("User has no phone number for magic link SMS")
    from twilio.rest import Client as TwilioClient

    client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
    client.messages.create(
        body=f"Ahoy! Sign in to your Ship: {verify_url}",
        from_=settings.twilio_from_number,
        to=phone,
    )


async def consume_magic_link(
    db: AsyncSession,
    *,
    raw_token: str,
    settings: Settings,
) -> tuple[str, datetime, AuthUser, str]:
    token_hash = hash_token(raw_token)
    result = await db.execute(select(AuthMagicLink).where(AuthMagicLink.token_hash == token_hash))
    link = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if link is None or link.consumed_at is not None or link.expires_at < now:
        raise ValueError("Invalid or expired magic link")

    user_result = await db.execute(select(User).where(User.user_id == link.user_id))
    user = user_result.scalar_one()
    client_ids = await resolve_client_ids(db, user)
    access_token, expires_at, jti = create_access_token(user=user, client_ids=client_ids, settings=settings)

    link.consumed_at = now
    db.add(
        Session(
            user_id=user.user_id,
            token_jti=jti,
            expires_at=expires_at,
        )
    )
    await db.commit()

    auth_user = AuthUser(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
        client_ids=client_ids,
    )
    return access_token, expires_at, auth_user, link.redirect_path or "/queue"


async def load_user_from_token(db: AsyncSession, token: str, settings: Settings) -> AuthUser:
    try:
        payload = decode_access_token(token, settings)
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    jti = payload.get("jti")
    if not jti:
        raise ValueError("Invalid token")

    session_result = await db.execute(select(Session).where(Session.token_jti == jti))
    session = session_result.scalar_one_or_none()
    now = datetime.now(UTC)
    if session is None or session.revoked_at is not None or session.expires_at < now:
        raise ValueError("Session expired or revoked")

    user_id = uuid.UUID(payload["sub"])
    user_result = await db.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")

    client_ids = [uuid.UUID(cid) for cid in payload.get("client_ids", [])]
    return AuthUser(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
        client_ids=client_ids,
    )
