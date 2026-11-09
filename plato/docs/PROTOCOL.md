# PLATO — Protocols & contracts

## 1. Real-time event protocol (server → client)

Every event uses one envelope:

```json
{
  "type": "message.sent",
  "project_id": "…", "run_id": "…", "agent_id": "…|null",
  "seq": 17,                       // per-run, gap-free; null for ephemeral events
  "ts": "2026-11-09T05:57:33.120Z",
  "data": { … }
}
```

| type | persisted | data |
|---|---|---|
| `snapshot` | – | `{active_runs: [{run_id, status, seq, cost_usd, agents: [{id, name, status, turns, turn_id, partial}], awaiting_approval}]}` (first frame after connect) |
| `run.status` | ✓ | `{status, reason?, objective?, mode?, limits?, agents?, cost_usd?, input_tokens?, output_tokens?}` |
| `agent.status` | ✓ | `{status: idle\|thinking\|streaming\|done\|error\|limit_reached, name}` |
| `agent.turn.started` | ✓ | `{turn_id, turn, name, inputs: [{kind, from}]}` |
| `agent.delta` | ✗ | `{turn_id, text}` — token stream |
| `agent.turn.completed` | ✓ | `{turn_id, name, text, visible_text, done, usage: {input_tokens, output_tokens, cost_usd, cost_is_estimate, price_known}}` |
| `agent.turn.interrupted` | ✓ | `{turn_id, partial, reason?}` |
| `message.sent` | ✓ | `{from: agent_id\|"commander", from_name, to: [agent_id], to_names, content, kind: message\|commander}` |
| `task.created` / `task.updated` | ✓ | `{task_id, title, status, assignee_agent_id, …}` |
| `usage.updated` | ✓ | `{cost_usd, input_tokens, output_tokens, budget_usd}` |
| `limit.reached` | ✓ | `{limit, value, agent?}` |
| `directive.rejected` | ✓ | `{reason, name}` |
| `error` | ✓ | `{message, retrying}` |

Run statuses: `pending → running ⇄ paused → completed | stopped | limit_reached | interrupted`.

## 2. WebSocket

`GET /ws/projects/{project_id}?ticket=…` — obtain a ticket with `POST /api/auth/ws-ticket`
(Bearer auth; valid 60 s; single use). Close codes: `4401` bad ticket, `4404` project not found.

Client → server actions (optional `ref` is echoed in the reply):

```json
{"action": "user.message", "run_id": "…", "content": "…", "to": ["agent_id"] | null, "ref": "1"}
{"action": "run.pause" | "run.resume" | "run.stop", "run_id": "…"}
{"action": "agent.interrupt", "run_id": "…", "agent_id": "…"}
{"action": "task.approve" | "task.reject", "run_id": "…", "task_id": "…"}
{"action": "ping"}
```

Replies: `{"type": "ack", "ref": "1"}` or `{"type": "error", "ref": "1", "data": {"message": "…"}}`.
Frames > 64 KB and > 60 actions/minute per user are rejected.

## 3. Agent directive language

Agents act on the team by embedding tags in their reply (provider-agnostic; parsed by the engine):

```
<message to="Developer">Which storage engine are you assuming?</message>
<message to="Architect, Reviewer">Draft is in the workspace.</message>
<message to="all">Switching to plan B.</message>
<task to="Researcher" title="Compare queues">Kafka vs SQS for 10k msg/s; return a table.</task>
<done>Data model agreed: 3 tables, see summary above.</done>
```

The engine resolves names case-insensitively, rejects unknown recipients and recipients the
current collaboration mode forbids (the sender is told why on its next turn), and counts each
delivered directive against the run's message limit.

Inbox items are rendered for the receiving agent as:

```
<kickoff><commander_message>…</commander_message> Begin your work now.</kickoff>
<commander_message>…</commander_message>
<agent_message from="Architect">…</agent_message>
<task from="Lead" title="…"><agent_message from="Lead">…</agent_message></task>
<system_notice>…</system_notice>
```

Directive and envelope tags occurring inside untrusted content are neutralised (`<` → `‹`).

## 4. External Agent Protocol v1

For connected runtimes (`provider: "external"`). PLATO → agent:

```http
POST <endpoint>
Authorization: Bearer <optional key stored as a credential>
Content-Type: application/json
Accept: text/event-stream

{"protocol": "plato.agent.v1", "model": "default", "system": "…",
 "messages": [{"role": "user", "content": "…"}, {"role": "assistant", "content": "…"}],
 "max_output_tokens": 2048}
```

Agent → PLATO (SSE):

```
data: {"type": "text", "text": "partial output…"}
data: {"type": "usage", "input_tokens": 120, "output_tokens": 45}
data: {"type": "error", "message": "…"}
data: [DONE]
```

The agent replies in the same directive language as hosted agents. Endpoints must be `https` and
publicly routable unless `PLATO_ALLOW_PRIVATE_EXTERNAL_AGENTS=true` (local development).

## 5. Provider adapter contract (`app/providers/base.py`)

```python
class ProviderAdapter(ABC):
    info: ProviderInfo   # id, display_name, integration: hosted|external|simulated, requires_api_key, …

    def stream(self, request: GenerationRequest, *, api_key: str | None,
               endpoint: str | None = None) -> AsyncIterator[StreamEvent]:
        """Yield StreamEvent(type="text", text=…) deltas, then exactly one
        StreamEvent(type="usage", input_tokens=…, output_tokens=…, stop_reason=…)."""

    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        """Live model list; also used to verify a key when it is connected."""
```

`GenerationRequest = {model, system, messages: [ChatMessage(role, content)], max_output_tokens}`.
Errors are raised as `ProviderError(message, retryable=bool, status=int|None)`; the engine retries
retryable errors. Register new adapters in `providers/registry.py`.

## 6. REST API summary

Interactive docs at `http://localhost:8000/docs` (disabled in production).

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/ws-ticket` |
| Providers | `GET /api/providers`, `GET /api/providers/{p}/models`, `GET/POST /api/credentials`, `DELETE /api/credentials/{id}` |
| Projects | `GET/POST /api/projects`, `GET/PATCH/DELETE /api/projects/{id}`, `GET/PUT /api/projects/{id}/files`, `DELETE …/files/{fid}` |
| Agents | `GET/POST /api/projects/{id}/agents`, `PATCH/DELETE /api/agents/{id}` |
| Runs | `POST/GET /api/projects/{id}/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/events?after_seq=`, `GET /api/projects/{id}/tasks`, `POST /api/runs/{id}/messages`, `POST /api/runs/{id}/{pause\|resume\|stop}`, `POST /api/runs/{id}/agents/{aid}/interrupt`, `POST /api/runs/{id}/tasks/{tid}/{approve\|reject}` |
| Billing | `GET /api/billing/plans`, `GET /api/billing/summary`, `POST /api/billing/checkout`, `POST /api/billing/portal`, `POST /api/billing/webhook` |
| Admin | `PATCH /api/admin/plans/{code}`, `GET /api/audit-logs` |
| Misc | `GET /api/health`, `GET /api/modes` |
