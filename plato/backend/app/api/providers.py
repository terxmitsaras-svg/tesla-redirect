"""Provider catalogue + BYOK credential management (keys encrypted at rest, never returned)."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ..core.config import get_settings
from ..core.security import decrypt_secret, encrypt_secret, key_hint
from ..models import ProviderCredential
from ..providers.base import ProviderError
from ..providers.registry import get_adapter, registry
from ..schemas import CredentialIn, CredentialOut
from .deps import SessionDep, UserDep, audit

router = APIRouter(prefix="/api", tags=["providers"])


@router.get("/providers")
async def list_providers(user: UserDep, session: SessionDep):
    creds = (await session.scalars(select(ProviderCredential).where(ProviderCredential.owner_id == user.id))).all()
    s = get_settings()
    out = []
    for adapter in registry().values():
        i = adapter.info
        out.append({
            "id": i.id, "display_name": i.display_name, "integration": i.integration,
            "requires_api_key": i.requires_api_key, "suggested_models": i.suggested_models,
            "docs_url": i.docs_url,
            "connected": any(c.provider == i.id for c in creds) or not i.requires_api_key,
            "platform_managed_available": bool(s.platform_key(i.id)),
        })
    return out


@router.get("/providers/{provider}/models")
async def list_models(provider: str, user: UserDep, session: SessionDep, credential_id: str | None = None):
    """Live model list from the provider (genuine API call with the user's key)."""
    try:
        adapter = get_adapter(provider)
    except ProviderError as exc:
        raise HTTPException(404, str(exc)) from exc
    if not adapter.info.requires_api_key:
        return {"models": adapter.info.suggested_models, "live": False}
    q = select(ProviderCredential).where(ProviderCredential.owner_id == user.id,
                                         ProviderCredential.provider == provider)
    if credential_id:
        q = q.where(ProviderCredential.id == credential_id)
    cred = await session.scalar(q)
    if not cred:
        return {"models": adapter.info.suggested_models, "live": False}
    try:
        models = await adapter.list_models(api_key=decrypt_secret(cred.encrypted_key))
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return {"models": models, "live": True}


@router.get("/credentials", response_model=list[CredentialOut])
async def list_credentials(user: UserDep, session: SessionDep):
    return (await session.scalars(select(ProviderCredential).where(ProviderCredential.owner_id == user.id)
                                  .order_by(ProviderCredential.created_at))).all()


@router.post("/credentials", response_model=CredentialOut, status_code=201)
async def add_credential(body: CredentialIn, request: Request, user: UserDep, session: SessionDep):
    try:
        adapter = get_adapter(body.provider)
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc
    if adapter.info.integration == "simulated":
        raise HTTPException(400, "The simulated provider needs no key")
    api_key = body.api_key.strip()
    verified_at = None
    if body.verify and adapter.info.integration == "hosted":
        try:
            await adapter.list_models(api_key=api_key)  # genuine call: proves the key works
        except ProviderError as exc:
            raise HTTPException(400, f"Key verification failed: {exc}") from exc
        verified_at = datetime.now(UTC)
    existing = await session.scalar(select(ProviderCredential).where(
        ProviderCredential.owner_id == user.id, ProviderCredential.provider == body.provider,
        ProviderCredential.label == body.label))
    if existing:
        existing.encrypted_key, existing.key_hint, existing.verified_at = \
            encrypt_secret(api_key), key_hint(api_key), verified_at
        cred = existing
    else:
        cred = ProviderCredential(owner_id=user.id, provider=body.provider, label=body.label,
                                  encrypted_key=encrypt_secret(api_key), key_hint=key_hint(api_key),
                                  verified_at=verified_at)
        session.add(cred)
    await session.flush()
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="credential.upsert",
                target=cred.id, details={"provider": body.provider, "verified": bool(verified_at)}, request=request)
    await session.commit()
    return cred


@router.delete("/credentials/{credential_id}", status_code=204)
async def delete_credential(credential_id: str, request: Request, user: UserDep, session: SessionDep):
    cred = await session.get(ProviderCredential, credential_id)
    if not cred or cred.owner_id != user.id:
        raise HTTPException(404, "Credential not found")
    await session.delete(cred)
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="credential.delete",
                target=credential_id, details={"provider": cred.provider}, request=request)
    await session.commit()
