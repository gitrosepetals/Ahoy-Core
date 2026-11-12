"""Per-client integration secrets (Ayrshare profile key, GBP OAuth tokens, …) encrypted at rest.

Stored in ``integration_credentials.encrypted_payload`` as a Fernet token of a JSON object.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import IntegrationCredential
from app.services.audit import record


def _fernet(settings: Settings) -> Fernet:
    # Any string works as the configured secret; derive a valid 32-byte urlsafe key from it.
    digest = hashlib.sha256(settings.credentials_encryption_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_payload(settings: Settings, payload: dict) -> str:
    return _fernet(settings).encrypt(json.dumps(payload).encode("utf-8")).decode("ascii")


def decrypt_payload(settings: Settings, token: str) -> dict:
    try:
        return json.loads(_fernet(settings).decrypt(token.encode("ascii")))
    except InvalidToken as exc:
        raise ValueError("Credential cannot be decrypted (CREDENTIALS_ENCRYPTION_KEY changed?)") from exc


async def get_credential(
    db: AsyncSession, settings: Settings, client_id: uuid.UUID, provider: str
) -> dict | None:
    row = (
        await db.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.client_id == client_id,
                IntegrationCredential.provider == provider,
            )
        )
    ).scalar_one_or_none()
    return decrypt_payload(settings, row.encrypted_payload) if row else None


async def put_credential(
    db: AsyncSession, settings: Settings, client_id: uuid.UUID, provider: str, payload: dict
) -> IntegrationCredential:
    row = (
        await db.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.client_id == client_id,
                IntegrationCredential.provider == provider,
            )
        )
    ).scalar_one_or_none()
    token = encrypt_payload(settings, payload)
    if row is None:
        row = IntegrationCredential(client_id=client_id, provider=provider, encrypted_payload=token)
        db.add(row)
    else:
        row.encrypted_payload = token
        row.updated_at = datetime.now(UTC)
    record(
        db.sync_session,
        client_id=client_id,
        entity_type="integration",
        entity_id=provider,
        action="credential_saved",
        details={"fields": sorted(payload)},  # names only, never values
    )
    await db.flush()
    return row


async def list_providers(db: AsyncSession, client_id: uuid.UUID) -> list[IntegrationCredential]:
    result = await db.execute(
        select(IntegrationCredential).where(IntegrationCredential.client_id == client_id)
    )
    return list(result.scalars().all())
