"""Provider catalogue + BYOK credential management (keys encrypted at rest, never returned)."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ..core.config import get_settings
from ..core.netguard import UnsafeURLError, validate_endpoint_url
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
        mine = [c for c in creds if c.provider == i.id]
        out.append({
            "id": i.id, "display_name": i.display_name, "integration": i.integration, "category": i.category,
            "requires_api_key": i.requires_api_key, "suggested_models": i.suggested_models,
            "docs_url": i.docs_url, "base_url_mode": i.base_url_mode, "default_base_url": i.default_base_url,
            "self_hosted": i.self_hosted,
            # Keyless runtimes with a default URL (Ollama, LM Studio) work without a saved connection.
            "connected": bool(mine) or (not i.requires_api_key and i.base_url_mode != "required"),
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
    q = select(ProviderCredential).where(ProviderCredential.owner_id == user.id,
                                         ProviderCredential.provider == provider)
    if credential_id:
        q = q.where(ProviderCredential.id == credential_id)
    cred = await session.scalar(q)
    if cred is None and (adapter.info.requires_api_key or adapter.info.integration != "hosted"):
        return {"models": adapter.info.suggested_models, "live": False}
    try:
        models = await adapter.list_models(
            api_key=decrypt_secret(cred.encrypted_key) or None if cred else None,
            endpoint=cred.base_url if cred else None)
    except ProviderError as exc:
        if cred is None:  # e.g. local Ollama not running: fall back to suggestions instead of failing
            return {"models": adapter.info.suggested_models, "live": False, "error": str(exc)}
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
    info = adapter.info
    if info.integration != "hosted":
        raise HTTPException(400, f"{info.display_name} is not configured here")
    api_key = body.api_key.strip()
    if info.requires_api_key and len(api_key) < 8:
        raise HTTPException(422, f"{info.display_name} needs an API key")
    if body.base_url and info.base_url_mode == "fixed":
        raise HTTPException(400, f"{info.display_name} uses a fixed API URL")
    if info.base_url_mode == "required" and not body.base_url:
        raise HTTPException(422, f"{info.display_name} needs a base URL")
    if body.base_url:
        try:
            await validate_endpoint_url(body.base_url)
        except UnsafeURLError as exc:
            raise HTTPException(400, f"Base URL rejected: {exc}") from exc
    verified_at = None
    if body.verify:
        try:  # genuine call: proves the key and/or URL work
            await adapter.list_models(api_key=api_key or None, endpoint=body.base_url)
        except ProviderError as exc:
            raise HTTPException(400, f"Verification failed: {exc}") from exc
        verified_at = datetime.now(UTC)
    existing = await session.scalar(select(ProviderCredential).where(
        ProviderCredential.owner_id == user.id, ProviderCredential.provider == body.provider,
        ProviderCredential.label == body.label))
    if existing:
        existing.encrypted_key, existing.key_hint, existing.verified_at = \
            encrypt_secret(api_key), key_hint(api_key), verified_at
        existing.base_url = body.base_url
        cred = existing
    else:
        cred = ProviderCredential(owner_id=user.id, provider=body.provider, label=body.label,
                                  encrypted_key=encrypt_secret(api_key), key_hint=key_hint(api_key),
                                  base_url=body.base_url, verified_at=verified_at)
        session.add(cred)
    await session.flush()
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="credential.upsert",
                target=cred.id, request=request,
                details={"provider": body.provider, "verified": bool(verified_at), "base_url": body.base_url})
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
