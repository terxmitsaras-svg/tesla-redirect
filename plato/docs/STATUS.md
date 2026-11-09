# PLATO — Implementation status

Honest status of each phase. "Verified" means covered by automated tests and/or exercised in the
browser end-to-end run; it does not mean verified against live provider accounts unless stated.

## §10 Mandatory demonstration

| Step | Status | How it was verified |
|---|---|---|
| 1. Open PLATO | ✅ | Playwright e2e (`frontend/e2e/demo.e2e.cjs`) |
| 2. Connect OpenAI and Claude via APIs | ✅ code / ⚠️ live | Keys are verified with a real `models.list` call through the official SDKs. Tested at wire level against a local server speaking each provider's real SSE format (`tests/test_adapters.py`, `tests/test_platform.py`). **No live OpenAI/Anthropic keys were available while building**, so live calls are not yet verified — run `scripts/live_demo.py` with your keys. |
| 3. Create two agents | ✅ | e2e + API tests |
| 4. Submit one objective | ✅ | e2e + API tests |
| 5. Both agents work concurrently | ✅ | test asserts both agents start before either finishes |
| 6–8. A → B, B responds, exchange info | ✅ | tests assert A→B and B→A `message.sent`, and B's reply after A's question |
| 9. Live streaming in the command room | ✅ | e2e waits for streaming bubbles and handoff cards |
| 10. Interrupt / stop | ✅ | tests: interrupt one agent mid-stream, pause/resume, stop; e2e: pause + stop from UI |
| 11. History after refresh | ✅ | e2e reloads and compares; API test checks gap-free `seq` and `after_seq` paging |

The browser demo used the **Simulated** provider (no API keys in the build environment). It is
labelled "simulated" everywhere in the UI and in usage records, costs $0, and is disabled in
production. The identical pipeline with the real Claude + OpenAI SDKs is covered by
`test_hosted_claude_and_openai_agents_run_through_real_sdks` (against a fake upstream).

Docker Compose (Postgres + Redis + API + web) was brought up and the e2e demo passed against it.

## Provider coverage

| Providers | Verified how |
|---|---|
| OpenAI, Anthropic, Gemini | wire-level tests against a local server speaking each provider's streaming format |
| xAI, Hugging Face, Mistral, Groq, DeepSeek, Together, OpenRouter, LM Studio, custom | shared OpenAI-compatible adapter, wire-tested against a strict compatible server (no OpenAI-only params, no usage → estimated) and Groq's `x_groq.usage`; base URLs checked to exist (401 without key / public model list for HF and OpenRouter) |
| Ollama | parameters taken from Ollama's OpenAI-compatibility docs; tested with a fake Ollama-style server through the API and in the browser (connect custom host → agent → run) |

None of these were exercised with real keys or a real Ollama install in the build environment.

## Platforms

Server: Windows, macOS, Linux, Kali, Chromebook (Linux), Docker. App (PWA): Windows, macOS, Linux,
ChromeOS, Android, iPhone/iPad. Terminal: the `plato` CLI (PowerShell, cmd, macOS/Linux shells).
What was verified on which platform, and how, is listed in [PLATFORMS.md](PLATFORMS.md#what-is-verified-and-how).
Windows and macOS have CI jobs but are not yet verified: GitHub Actions has not started any job on this repository (account-level setting). iOS Safari
(WebKit) was not available to test. No native app-store builds exist; the installable web app
covers phones and desktops.

## Phases

### Phase 1 — Functional foundation ✅
Auth (bcrypt + JWT), projects, agents, encrypted BYOK credentials with live verification,
4 provider adapters + external + simulated, dashboard UI.

### Phase 2 — Real-time command room ✅
WebSocket stream, token streaming, agent-to-agent messaging, Commander messages to one/many/all,
persisted ordered history, reconnect + gap-fill.

### Phase 3 — Subagent orchestration ✅ core / ⏳ scale-out
Done: hierarchy (primary → subagents), task delegation, Commander approval gate, collaboration
modes with enforced communication policies, per-run concurrency semaphore, plan entitlements.
Not yet: agents creating subagents dynamically at runtime; execution in separate worker processes
(runs currently execute in the API process — see ARCHITECTURE §6); Redis-backed control channel.

### Phase 4 — Advanced workspace ⏳ partial
Done: shared project context and files visible to agents (as untrusted data); external agent
protocol. Not yet: S3 storage for files, code editor, tool execution, sandboxed code runners,
persistent cross-run agent memory, native provider tool-calling (directives are used instead).

### Phase 5 — SaaS commercialisation ⏳ partial
Done: plans + entitlement enforcement, admin-editable prices, Stripe Checkout/Portal/webhooks
(signature-verified; webhook handling tested with signed payloads), usage metering, optional Stripe
meter events, platform credits, audit log, rate limits, production guardrails, Docker, CI.
Not yet: tested against a live Stripe account; team workspaces and roles (Business);
Alembic migrations; distributed rate limiting; observability (metrics/tracing); email verification
and password reset; MFA.

## Known limitations

* Costs are **estimates** from list prices (Anthropic built in; others via fallback or
  `PLATO_MODEL_PRICING_JSON`). Provider invoices are authoritative.
* Pause lets in-flight replies finish; it does not cut a stream mid-token (use Interrupt for that).
* A run cannot survive an API restart; it is marked `interrupted` on boot.
* JWT is stored in `localStorage` in the browser; moving to httpOnly cookies is planned.
