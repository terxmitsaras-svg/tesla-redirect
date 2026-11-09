<p align="center"><img src="frontend/public/plato-logo.png" alt="PLATO" width="320"></p>

# PLATO — Multiple Minds. One Intelligence.

A real-time command centre where AI agents from **OpenAI, Anthropic Claude, xAI Grok, Google
Gemini, Hugging Face, Mistral, Groq, DeepSeek, Together AI, OpenRouter**, local models via
**Ollama** and **LM Studio**, any **OpenAI-compatible server** (vLLM, llama.cpp, LocalAI…), and your
own connected agent runtimes work together as one team, under human control.

* Agents run **concurrently** and message each other directly. No copy-pasting between chats.
* Primary agents delegate **tasks** to **subagents**, with an optional human approval gate.
* Every token streams live into a shared **Command Room**; the full history is persisted.
* The **Commander** (you) can message any agent, pause, interrupt, or stop at any moment.
* Every run is bounded by turn, message, time and **USD budget** limits, and loops are prevented.
* SaaS-ready: plans and entitlements, Stripe billing, BYOK keys encrypted at rest, audit logs.

## Quick start

```bash
# API
cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --port 8000
# Web (another terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000, create an account and a project, then:

1. **Providers** → paste an Anthropic key and an OpenAI key (verified live, stored encrypted).
2. In the project's **Agents** panel add e.g. *Architect* (Claude) and *Developer* (OpenAI).
3. Type an objective → **Start run**, and watch both agents work and talk to each other.

No keys? Run models locally with **Ollama** (`ollama pull llama3.2`; works with no setup in development),
or choose the **Simulated (offline)** provider, which is clearly labelled and calls no AI.

With Docker: `cp .env.example .env` (set the two secrets), then `docker compose up --build`.

## Documentation

| Doc | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram, monorepo layout, orchestration engine, DB schema, security model |
| [docs/PROTOCOL.md](docs/PROTOCOL.md) | Real-time event protocol, WebSocket actions, agent directives, External Agent Protocol, adapter contract, REST API |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Local, Docker, tests, live demo, production checklist, Stripe setup |
| [docs/STATUS.md](docs/STATUS.md) | What is done, what is verified and how, what is simulated, what is next |

## Stack

Next.js 16 · React 19 · TypeScript · Tailwind · FastAPI · SQLAlchemy 2 (async) · PostgreSQL ·
Redis · WebSockets · official OpenAI / Anthropic / Google GenAI SDKs · Stripe · Docker.
