"""Outbound URL validation (SSRF protection) for user-supplied endpoints.

Users can point PLATO at their own infrastructure (Ollama, LM Studio, vLLM, external agents).
In a multi-tenant deployment the *server* makes those requests, so private/loopback/link-local
targets (cloud metadata, internal services) are refused unless private endpoints are allowed —
the default outside production, opt-in for single-tenant self-hosted production installs.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from .config import get_settings


class UnsafeURLError(ValueError):
    pass


async def validate_endpoint_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeURLError("URL must be an absolute http(s) URL.")
    if parsed.username or parsed.password:
        raise UnsafeURLError("Put credentials in the API key field, not in the URL.")
    if get_settings().private_endpoints_allowed:
        return
    if parsed.scheme != "https":
        raise UnsafeURLError("URL must use https.")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve host: {parsed.hostname}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeURLError(
                "URL resolves to a private network address. Self-hosted single-tenant installs can allow this "
                "with PLATO_ALLOW_PRIVATE_ENDPOINTS=true."
            )
