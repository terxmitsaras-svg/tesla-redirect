"""Password hashing, JWT issuance, and encryption of provider credentials at rest."""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings

JWT_ALG = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=s.jwt_ttl_minutes), "typ": "access"}
    return jwt.encode(payload, s.jwt_secret, algorithm=JWT_ALG)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    return payload.get("sub")


# --- Credential encryption -------------------------------------------------------------

@lru_cache
def _fernet() -> Fernet:
    s = get_settings()
    if s.encryption_key:
        return Fernet(s.encryption_key.encode())
    # Development fallback only (production refuses to boot without PLATO_ENCRYPTION_KEY).
    derived = base64.urlsafe_b64encode(hashlib.sha256(("plato-dev:" + s.jwt_secret).encode()).digest())
    return Fernet(derived)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:  # key rotated or data tampered with
        raise ValueError("Credential could not be decrypted") from exc


def key_hint(secret: str) -> str:
    if not secret:
        return "no key"
    return f"…{secret[-4:]}" if len(secret) >= 8 else "…"


# --- One-time WebSocket tickets (avoid putting long-lived JWTs in URLs) -----------------

_WS_TICKETS: dict[str, tuple[str, float]] = {}
WS_TICKET_TTL = 60.0


def issue_ws_ticket(user_id: str) -> str:
    now = time.monotonic()
    for k in [k for k, (_, exp) in _WS_TICKETS.items() if exp < now]:
        _WS_TICKETS.pop(k, None)
    ticket = secrets.token_urlsafe(32)
    _WS_TICKETS[ticket] = (user_id, now + WS_TICKET_TTL)
    return ticket


def redeem_ws_ticket(ticket: str) -> str | None:
    entry = _WS_TICKETS.pop(ticket, None)
    if not entry:
        return None
    user_id, exp = entry
    return user_id if exp >= time.monotonic() else None
