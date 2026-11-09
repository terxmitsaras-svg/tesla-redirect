"""Thin REST client for the PLATO API."""
from __future__ import annotations

from typing import Any

import httpx

from .config import Config


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class Client:
    def __init__(self, cfg: Config, timeout: float = 60.0):
        self.cfg = cfg
        self.http = httpx.Client(base_url=cfg.server, timeout=timeout)

    def close(self) -> None:
        self.http.close()

    def request(self, method: str, path: str, *, json: Any = None, params: dict | None = None,
                auth: bool = True) -> Any:
        headers = {}
        if auth:
            if not self.cfg.token:
                raise ApiError(401, "Not signed in. Run: plato login")
            headers["Authorization"] = f"Bearer {self.cfg.token}"
        try:
            r = self.http.request(method, path, json=json, params=params, headers=headers)
        except httpx.ConnectError as exc:
            raise ApiError(0, f"Cannot reach the PLATO server at {self.cfg.server}. Is it running?") from exc
        except httpx.HTTPError as exc:
            raise ApiError(0, f"Network error talking to {self.cfg.server}: {exc}") from exc
        if r.status_code == 401 and auth:
            raise ApiError(401, "Your session expired or is invalid. Run: plato login")
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
                if isinstance(detail, list):
                    detail = "; ".join(d.get("msg", str(d)) for d in detail)
            except ValueError:
                detail = r.text
            raise ApiError(r.status_code, str(detail or r.reason_phrase))
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    def get(self, path: str, **kw: Any) -> Any:
        return self.request("GET", path, **kw)

    def post(self, path: str, json: Any = None, **kw: Any) -> Any:
        return self.request("POST", path, json=json, **kw)

    def delete(self, path: str, **kw: Any) -> Any:
        return self.request("DELETE", path, **kw)

    # ---- lookups by id or name ------------------------------------------------------------
    def find_project(self, ref: str) -> dict:
        projects = self.get("/api/projects")
        exact = [p for p in projects if p["id"] == ref or p["name"].lower() == ref.lower()]
        if not exact:
            exact = [p for p in projects if p["id"].startswith(ref)]
        if len(exact) == 1:
            return exact[0]
        if not exact:
            raise ApiError(404, f"No project named or with id '{ref}'. See: plato projects")
        raise ApiError(409, f"'{ref}' matches several projects; use the id.")

    def find_agent(self, project_id: str, ref: str) -> dict:
        agents = self.get(f"/api/projects/{project_id}/agents")
        match = [a for a in agents if a["id"] == ref or a["name"].lower() == ref.lower()]
        if len(match) != 1:
            raise ApiError(404, f"No agent '{ref}' in this project. See: plato agents <project>")
        return match[0]

    def active_run(self, project_id: str) -> dict | None:
        runs = self.get(f"/api/projects/{project_id}/runs", params={"limit": 5})
        return next((r for r in runs if r["status"] in ("pending", "running", "paused")), None)
