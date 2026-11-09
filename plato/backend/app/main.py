"""PLATO API entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .api import auth, billing, projects, providers, runs, ws
from .core.config import get_settings
from .orchestrator.bus import RedisBus, get_bus, set_bus
from .orchestrator.engine import get_run_manager, recover_orphaned_runs
from .plans import seed_plans

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("plato")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await db.create_all()
    async with db.sessionmaker()() as s:
        await seed_plans(s)
    n = await recover_orphaned_runs()
    if n:
        log.warning("marked %d orphaned run(s) as interrupted", n)
    if settings.redis_url:
        import redis.asyncio as redis

        set_bus(RedisBus(redis.from_url(settings.redis_url)))
    await get_bus().start()
    yield
    await get_run_manager().shutdown()
    await get_bus().stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="PLATO API", version="0.1.0", lifespan=lifespan,
                  docs_url=None if settings.is_production else "/docs")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    for r in (auth.router, providers.router, projects.router, runs.router, billing.router, ws.router):
        app.include_router(r)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/modes")
    async def modes():
        from .orchestrator.prompts import MODES

        return [{"id": k, "label": v["label"], "guidance": v["guidance"], "policy": v["policy"]}
                for k, v in MODES.items()]

    return app


app = create_app()
