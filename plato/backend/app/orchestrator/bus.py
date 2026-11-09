"""Event bus: fan-out of run events to WebSocket subscribers, keyed by project.

* ``InMemoryBus`` — single process (default; dev and single-instance deployments).
* ``RedisBus`` — publishes through Redis pub/sub so every API instance can serve any client's
  WebSocket. Enabled automatically when ``PLATO_REDIS_URL`` is set.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import defaultdict
from typing import Any

log = logging.getLogger("plato.bus")

QUEUE_MAX = 2000


class Subscription:
    def __init__(self, bus: EventBus, project_id: str):
        self.bus = bus
        self.project_id = project_id
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_MAX)

    def offer(self, event: dict[str, Any]) -> None:
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            # Slow consumer: drop ephemeral deltas first; persisted events are recoverable via REST.
            log.warning("subscriber queue full for project %s; dropping event %s", self.project_id, event["type"])

    async def get(self) -> dict[str, Any]:
        return await self.queue.get()

    async def close(self) -> None:
        await self.bus.unsubscribe(self)


class EventBus:
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def publish(self, event: dict[str, Any]) -> None:
        raise NotImplementedError

    async def subscribe(self, project_id: str) -> Subscription:
        raise NotImplementedError

    async def unsubscribe(self, sub: Subscription) -> None:
        raise NotImplementedError


class InMemoryBus(EventBus):
    def __init__(self) -> None:
        self._subs: dict[str, set[Subscription]] = defaultdict(set)

    def _deliver(self, event: dict[str, Any]) -> None:
        for sub in list(self._subs.get(event["project_id"], ())):
            sub.offer(event)

    async def publish(self, event: dict[str, Any]) -> None:
        self._deliver(event)

    async def subscribe(self, project_id: str) -> Subscription:
        sub = Subscription(self, project_id)
        self._subs[project_id].add(sub)
        return sub

    async def unsubscribe(self, sub: Subscription) -> None:
        self._subs.get(sub.project_id, set()).discard(sub)


class RedisBus(InMemoryBus):
    """Publishes to Redis; one listener per process re-delivers to local subscribers."""

    CHANNEL_PREFIX = "plato:project:"

    def __init__(self, redis_client) -> None:
        super().__init__()
        self.redis = redis_client
        self._pubsub = None
        self._listener: asyncio.Task | None = None

    async def start(self) -> None:
        self._pubsub = self.redis.pubsub()
        await self._pubsub.psubscribe(self.CHANNEL_PREFIX + "*")
        self._listener = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self._listener:
            self._listener.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener
        if self._pubsub:
            await self._pubsub.aclose()

    async def _listen(self) -> None:
        assert self._pubsub is not None
        while True:
            try:
                msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "pmessage":
                    self._deliver(json.loads(msg["data"]))
            except asyncio.CancelledError:
                raise
            except Exception:  # keep the listener alive on transient Redis errors
                log.exception("redis bus listener error")
                await asyncio.sleep(1.0)

    async def publish(self, event: dict[str, Any]) -> None:
        await self.redis.publish(self.CHANNEL_PREFIX + event["project_id"], json.dumps(event, default=str))


_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = InMemoryBus()
    return _bus


def set_bus(bus: EventBus) -> None:
    global _bus
    _bus = bus
