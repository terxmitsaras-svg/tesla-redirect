"""SIMULATED provider — no real AI is called.

Exists so the full orchestration pipeline (streaming, agent-to-agent messaging, persistence,
interrupts) can be exercised offline and in automated tests. Everything it produces is clearly
labelled "Simulated" in the UI and in usage records (``billed_to="simulated"``, cost 0).
Disabled in production (PLATO_ENABLE_MOCK_PROVIDER=false is enforced).

Behaviour (deterministic, loop-safe):
* On a kickoff/task it streams a short plan and asks the first teammate a question.
* On a message containing "?" it answers the sender once (answers never contain "?").
* Otherwise it acknowledges and emits <done>.
"""
from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator

from .base import GenerationRequest, ProviderAdapter, ProviderInfo, StreamEvent

_TEAM_RE = re.compile(r"^- (?P<name>[^<—\n][^—\n]*?) —", re.MULTILINE)
_SELF_RE = re.compile(r"You are (?P<name>[^,\n]+),")
_FROM_RE = re.compile(r'<agent_message from="(?P<name>[^"]+)"')


class MockAdapter(ProviderAdapter):
    info = ProviderInfo(
        id="mock", display_name="Simulated (offline)", integration="simulated", requires_api_key=False,
        suggested_models=["sim-fast", "sim-slow"],
    )

    def __init__(self, delay: float = 0.02):
        self.delay = delay

    def _script(self, req: GenerationRequest) -> str:
        self_match = _SELF_RE.search(req.system)
        me = self_match.group("name") if self_match else "Agent"
        teammates = [n.strip() for n in _TEAM_RE.findall(req.system) if n.strip() != me]
        last = req.messages[-1].content if req.messages else ""
        senders = _FROM_RE.findall(last)

        if senders and "?" in last:
            to = senders[-1]
            return (f"[Simulated] {me} received a question from {to}. Sharing my findings.\n"
                    f'<message to="{to}">Here is my part: I have drafted the outline for my area. '
                    f"Merge it with yours when ready.</message>\n<done>Answered {to}.</done>")
        if "<kickoff>" in last or "<task " in last:
            if teammates:
                to = teammates[0]
                return (f"[Simulated] {me} is analysing the objective and splitting the work.\n"
                        f"Plan: 1) research constraints 2) draft a proposal 3) review with the team.\n"
                        f'<message to="{to}">Hi {to}, which part of the objective will you own?</message>')
            return f"[Simulated] {me} is working alone on the objective.\n<done>Drafted a plan.</done>"
        return f"[Simulated] {me} acknowledges the update.\n<done>Acknowledged.</done>"

    async def stream(
        self, request: GenerationRequest, *, api_key: str | None, endpoint: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        text = self._script(request)
        if request.model == "sim-slow":
            delay = max(self.delay, 0.15)
        else:
            delay = self.delay
        for token in re.findall(r"\S+\s*", text):
            await asyncio.sleep(delay)
            yield StreamEvent(type="text", text=token)
        prompt_len = len(request.system) + sum(len(m.content) for m in request.messages)
        yield StreamEvent(type="usage", input_tokens=prompt_len // 4, output_tokens=len(text) // 4, stop_reason="end")

    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        return list(self.info.suggested_models)
