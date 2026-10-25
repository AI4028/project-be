"""Who is calling?

- Phones: anonymous. POST /devices returns a device token ("dev_...");
  the app stores it and sends it as `Authorization: Bearer dev_...`.
- Kiosks: each kiosk has an API key ("ksk_...") made by
  scripts/create_kiosk.py, sent as `Authorization: Bearer ksk_...`.

Only SHA-256 hashes of tokens are stored, so a leaked database does not
leak working tokens.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Device, Kiosk

_bearer = HTTPBearer(auto_error=False)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_device_token() -> str:
    return "dev_" + secrets.token_urlsafe(32)


def new_kiosk_key() -> str:
    return "ksk_" + secrets.token_urlsafe(32)


def create_device(db: Session, now: int) -> tuple[Device, str]:
    token = new_device_token()
    device = Device(id=str(uuid.uuid4()), token_hash=hash_token(token), created_at=now)
    db.add(device)
    db.commit()
    return device, token


def device_for_token(db: Session, token: Optional[str]) -> Optional[Device]:
    if not token or not token.startswith("dev_"):
        return None
    return db.scalar(select(Device).where(Device.token_hash == hash_token(token)))


def kiosk_for_key(db: Session, key: Optional[str]) -> Optional[Kiosk]:
    if not key or not key.startswith("ksk_"):
        return None
    return db.scalar(select(Kiosk).where(Kiosk.api_key_hash == hash_token(key)))


def current_device(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Device:
    """Dependency for phone endpoints."""
    device = device_for_token(db, creds.credentials if creds else None)
    if device is None:
        raise AppError("not-signed-in", "Missing or unknown device token. Call POST /devices first.")
    return device


def current_kiosk(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Kiosk:
    """Dependency for kiosk endpoints."""
    kiosk = kiosk_for_key(db, creds.credentials if creds else None)
    if kiosk is None:
        raise AppError("not-kiosk", "Missing or unknown kiosk key.")
    return kiosk

