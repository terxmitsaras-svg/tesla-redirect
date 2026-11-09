"""Run the §10 demonstration against LIVE provider APIs through a running PLATO server.

Usage (server running on :8000):
    export ANTHROPIC_API_KEY=sk-ant-...      OPENAI_API_KEY=sk-...
    export PLATO_DEMO_OPENAI_MODEL=<an OpenAI chat model your key can use>
    python scripts/live_demo.py [--api http://localhost:8000] [--claude-model claude-opus-5-5]

This makes real, billed API calls to OpenAI and Anthropic (budget-capped at $0.50 per run).
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
import time

import httpx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--claude-model", default="claude-opus-5-5")
    ap.add_argument("--objective", default="Design the data model and REST API for a small team task tracker. "
                                           "Agree on one design and summarise it.")
    args = ap.parse_args()

    akey, okey = os.environ.get("ANTHROPIC_API_KEY"), os.environ.get("OPENAI_API_KEY")
    if not (akey and okey):
        print("Set ANTHROPIC_API_KEY and OPENAI_API_KEY.", file=sys.stderr)
        return 2

    c = httpx.Client(base_url=args.api, timeout=60)
    email = f"demo-{secrets.token_hex(4)}@plato.local"
    tok = c.post("/api/auth/register", json={"email": email, "password": secrets.token_urlsafe(16)}).json()["token"]
    c.headers["Authorization"] = f"Bearer {tok}"

    for prov, key in (("anthropic", akey), ("openai", okey)):
        r = c.post("/api/credentials", json={"provider": prov, "api_key": key})
        if r.status_code != 201:
            print(f"{prov} key rejected: {r.text}", file=sys.stderr)
            return 1
        print(f"✓ connected {prov} (verified with a live models call)")

    omodel = os.environ.get("PLATO_DEMO_OPENAI_MODEL")
    if not omodel:
        models = c.get("/api/providers/openai/models").json().get("models", [])
        print("Set PLATO_DEMO_OPENAI_MODEL to one of:", ", ".join(models[:40]), file=sys.stderr)
        return 2

    pid = c.post("/api/projects", json={"name": "Live demo", "settings": {"budget_usd": 0.5,
                                                                          "max_turns_per_agent": 4}}).json()["id"]
    a = c.post(f"/api/projects/{pid}/agents", json={
        "name": "Architect", "role": "Software architect", "provider": "anthropic", "model": args.claude_model,
        "instructions": "Own the data model. Ask the Developer one concrete question early."}).json()
    b = c.post(f"/api/projects/{pid}/agents", json={
        "name": "Developer", "role": "Lead developer", "provider": "openai", "model": omodel,
        "instructions": "Own the REST API. Answer the Architect's questions precisely."}).json()
    names = {a["id"]: "Architect", b["id"]: "Developer"}

    run = c.post(f"/api/projects/{pid}/runs", json={"objective": args.objective})
    run.raise_for_status()
    run_id, seq = run.json()["id"], 0
    print(f"▶ run {run_id} started\n")
    while True:
        for e in c.get(f"/api/runs/{run_id}/events", params={"after_seq": seq}).json():
            seq = e["seq"]
            who = names.get(e["agent_id"] or "", "")
            d = e["data"]
            if e["type"] == "agent.turn.completed":
                print(f"── {who} ──\n{d['visible_text']}\n")
            elif e["type"] == "message.sent" and d["kind"] == "message":
                print(f"✉ {d['from_name']} → {', '.join(d['to_names'])}: {d['content']}\n")
            elif e["type"] in ("error", "limit.reached", "directive.rejected"):
                print(f"! {e['type']}: {d}\n")
        r = c.get(f"/api/runs/{run_id}").json()
        if r["status"] not in ("pending", "running", "paused"):
            print(f"■ {r['status']}: {r['stop_reason']} — est. cost ${r['cost_usd']:.4f}")
            return 0
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
