"""`plato` — command-line client for PLATO.

Works the same in PowerShell, cmd, Windows Terminal, macOS Terminal, and Linux / Kali / ChromeOS shells.
Add --json to any listing command for machine-readable output
(PowerShell: `plato projects --json | ConvertFrom-Json`).
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import sys
from typing import Any

from . import __version__, term
from .client import ApiError, Client
from .config import Config, config_path
from .stream import watch

EXIT_OK, EXIT_ERR, EXIT_LIMIT, EXIT_STOPPED = 0, 1, 3, 4
MODES = ["open_discussion", "structured_delegation", "parallel", "debate", "independent_review"]


def emit(args: argparse.Namespace, data: Any, rows: list[dict] | None = None,
         columns: list[tuple[str, str]] | None = None, text: str | None = None) -> None:
    if args.json:
        print(json.dumps(data, indent=2, default=str))
    elif rows is not None and columns is not None:
        print(term.table(rows, columns))
    elif text is not None:
        print(text)


def _secret(prompt: str, *, env: str | None, stdin: bool) -> str:
    """Read a secret without it appearing on screen, in shell history, or in process listings."""
    if env:
        value = os.environ.get(env, "")
        if not value:
            raise ApiError(0, f"Environment variable {env} is empty or not set.")
        return value
    if stdin:
        return sys.stdin.readline().strip()
    return getpass.getpass(prompt)


# ------------------------------------------------------------------ account
def cmd_login(args, cfg: Config) -> int:
    if args.server:
        cfg.server = args.server.rstrip("/")
    email = args.email or input("Email: ").strip()
    password = _secret("Password: ", env=args.password_env, stdin=args.password_stdin)
    client = Client(cfg)
    path = "/api/auth/register" if args.register else "/api/auth/login"
    body = {"email": email, "password": password}
    if args.register and args.name:
        body["name"] = args.name
    r = client.request("POST", path, json=body, auth=False)
    cfg.token, cfg.email = r["token"], r["user"]["email"]
    saved = cfg.save()
    emit(args, {"email": cfg.email, "server": cfg.server, "config": str(saved)},
         text=term.c(f"✓ Signed in as {cfg.email} on {cfg.server}", "green") + term.c(f"  (saved to {saved})", "grey"))
    return EXIT_OK


def cmd_logout(args, cfg: Config) -> int:
    cfg.token = None
    cfg.save()
    emit(args, {"ok": True}, text="Signed out.")
    return EXIT_OK


def cmd_whoami(args, cfg: Config) -> int:
    me = Client(cfg).get("/api/auth/me")
    emit(args, {**me, "server": cfg.server},
         text=f"{me['email']} · plan {me['plan_code']} · credits ${me['credits_usd']:.2f} · {cfg.server}")
    return EXIT_OK


def cmd_server(args, cfg: Config) -> int:
    if args.url:
        cfg.server = args.url.rstrip("/")
        cfg.save()
    health = None
    try:
        health = Client(cfg, timeout=5).request("GET", "/api/health", auth=False)
    except ApiError as exc:
        health = {"status": f"unreachable ({exc})"}
    emit(args, {"server": cfg.server, "health": health, "config": str(config_path())},
         text=f"Server: {cfg.server} · {health.get('status')}\nConfig: {config_path()}")
    return EXIT_OK


# ------------------------------------------------------------------ providers
def cmd_providers(args, cfg: Config) -> int:
    ps = Client(cfg).get("/api/providers")
    rows = [{**p, "connected": "yes" if p["connected"] else "", "key": "required" if p["requires_api_key"] else
             "optional", "url": p.get("default_base_url") or ""} for p in ps]
    emit(args, ps, rows, [("id", "id"), ("display_name", "provider"), ("category", "category"),
                          ("connected", "connected"), ("key", "api key"), ("url", "default url")])
    return EXIT_OK


def cmd_connect(args, cfg: Config) -> int:
    client = Client(cfg)
    info = next((p for p in client.get("/api/providers") if p["id"] == args.provider), None)
    if not info:
        raise ApiError(404, f"Unknown provider '{args.provider}'. See: plato providers")
    key = ""
    if info["requires_api_key"] or args.key_env or args.key_stdin or args.ask_key:
        key = _secret(f"{info['display_name']} API key: ", env=args.key_env, stdin=args.key_stdin)
    cred = client.post("/api/credentials", {"provider": args.provider, "api_key": key, "base_url": args.base_url})
    emit(args, cred, text=term.c(f"✓ {info['display_name']} connected", "green")
         + (f" · {cred['base_url']}" if cred.get("base_url") else "") + f" · key {cred['key_hint']}")
    return EXIT_OK


def cmd_models(args, cfg: Config) -> int:
    r = Client(cfg).get(f"/api/providers/{args.provider}/models")
    emit(args, r, text="\n".join(r["models"]) or "(no models listed)")
    return EXIT_OK


# ------------------------------------------------------------------ projects & agents
def cmd_projects(args, cfg: Config) -> int:
    ps = Client(cfg).get("/api/projects")
    rows = [{**p, "mode": p["settings"].get("mode"), "budget": f"${p['settings'].get('budget_usd')}"} for p in ps]
    emit(args, ps, rows, [("name", "name"), ("id", "id"), ("mode", "mode"), ("budget", "budget/run")])
    return EXIT_OK


def cmd_new_project(args, cfg: Config) -> int:
    settings: dict[str, Any] = {}
    if args.mode:
        settings["mode"] = args.mode
    if args.budget is not None:
        settings["budget_usd"] = args.budget
    body: dict[str, Any] = {"name": args.name, "description": args.description or ""}
    if settings:
        body["settings"] = settings
    p = Client(cfg).post("/api/projects", body)
    emit(args, p, text=term.c(f"✓ Project “{p['name']}” created", "green") + f" ({p['id']})")
    return EXIT_OK


def cmd_agents(args, cfg: Config) -> int:
    client = Client(cfg)
    project = client.find_project(args.project)
    agents = client.get(f"/api/projects/{project['id']}/agents")
    names = {a["id"]: a["name"] for a in agents}
    rows = [{**a, "reports_to": names.get(a["parent_id"] or "", "Commander")} for a in agents]
    emit(args, agents, rows, [("name", "name"), ("role", "role"), ("provider", "provider"), ("model", "model"),
                              ("reports_to", "reports to")])
    return EXIT_OK


def cmd_add_agent(args, cfg: Config) -> int:
    client = Client(cfg)
    project = client.find_project(args.project)
    parent = client.find_agent(project["id"], args.parent)["id"] if args.parent else None
    kind = "external" if args.provider == "external" else "hosted"
    a = client.post(f"/api/projects/{project['id']}/agents", {
        "name": args.name, "role": args.role or "", "provider": args.provider, "model": args.model,
        "instructions": args.instructions or "", "parent_id": parent, "kind": kind, "external_url": args.url})
    emit(args, a, text=term.c(f"✓ Agent {a['name']} added", "green") + f" · {a['provider']}/{a['model']}")
    return EXIT_OK


def cmd_remove_agent(args, cfg: Config) -> int:
    client = Client(cfg)
    project = client.find_project(args.project)
    agent = client.find_agent(project["id"], args.agent)
    client.delete(f"/api/agents/{agent['id']}")
    emit(args, {"ok": True}, text=f"Removed {agent['name']}.")
    return EXIT_OK


# ------------------------------------------------------------------ runs
def _status_code(status: str) -> int:
    return {"completed": EXIT_OK, "limit_reached": EXIT_LIMIT}.get(status, EXIT_STOPPED)


def _stream(args, client: Client, project_id: str, **kw) -> int:
    try:
        status, _ = asyncio.run(watch(client, project_id, live=not args.no_stream, as_json=args.json, **kw))
        return _status_code(status)
    except KeyboardInterrupt:
        # Ctrl+C: stop the run cleanly on the server instead of leaving agents running and spending.
        run = client.active_run(project_id)
        if run and not args.detach_on_ctrl_c:
            client.post(f"/api/runs/{run['id']}/stop")
            print(term.c("\n■ Stopped by you (Ctrl+C). History is saved on the server.", "yellow"), file=sys.stderr)
        else:
            print(term.c("\nDetached. The run continues on the server: plato watch …", "yellow"), file=sys.stderr)
        return EXIT_STOPPED


def cmd_run(args, cfg: Config) -> int:
    client = Client(cfg)
    project = client.find_project(args.project)
    body: dict[str, Any] = {"objective": args.objective}
    if args.mode:
        body["mode"] = args.mode
    if args.budget is not None:
        body["limits"] = {"budget_usd": args.budget}
    return _stream(args, client, project["id"], start=body)


def cmd_watch(args, cfg: Config) -> int:
    client = Client(cfg)
    project = client.find_project(args.project)
    run = client.active_run(project["id"])
    if not run:
        raise ApiError(404, "No active run in this project. Start one with: plato run <project> \"objective\"")
    return _stream(args, client, project["id"], run_id=run["id"])


def _active(client: Client, project_ref: str) -> tuple[dict, dict]:
    project = client.find_project(project_ref)
    run = client.active_run(project["id"])
    if not run:
        raise ApiError(409, "No active run in this project.")
    return project, run


def cmd_say(args, cfg: Config) -> int:
    client = Client(cfg)
    project, run = _active(client, args.project)
    to = [client.find_agent(project["id"], n.strip())["id"] for n in args.to.split(",")] if args.to else None
    client.post(f"/api/runs/{run['id']}/messages", {"content": args.message, "to": to})
    emit(args, {"ok": True}, text="Sent.")
    return EXIT_OK


def cmd_control(args, cfg: Config) -> int:
    client = Client(cfg)
    _, run = _active(client, args.project)
    client.post(f"/api/runs/{run['id']}/{args.command}")
    emit(args, {"ok": True, "run_id": run["id"]}, text=f"Run {args.command} requested.")
    return EXIT_OK


def cmd_interrupt(args, cfg: Config) -> int:
    client = Client(cfg)
    project, run = _active(client, args.project)
    agent = client.find_agent(project["id"], args.agent)
    client.post(f"/api/runs/{run['id']}/agents/{agent['id']}/interrupt")
    emit(args, {"ok": True}, text=f"Interrupted {agent['name']}.")
    return EXIT_OK


def cmd_runs(args, cfg: Config) -> int:
    client = Client(cfg)
    project = client.find_project(args.project)
    runs = client.get(f"/api/projects/{project['id']}/runs", params={"limit": args.limit})
    rows = [{**r, "cost": f"${r['cost_usd']:.4f}", "objective": r["objective"][:50]} for r in runs]
    emit(args, runs, rows, [("id", "id"), ("status", "status"), ("cost", "est. cost"), ("created_at", "started"),
                            ("objective", "objective")])
    return EXIT_OK


def cmd_history(args, cfg: Config) -> int:
    from .stream import Renderer

    client = Client(cfg)
    project = client.find_project(args.project)
    run_id = args.run
    if not run_id:
        runs = client.get(f"/api/projects/{project['id']}/runs", params={"limit": 1})
        if not runs:
            raise ApiError(404, "This project has no runs yet.")
        run_id = runs[0]["id"]
    events = client.get(f"/api/runs/{run_id}/events")
    if args.json:
        emit(args, events)
        return EXIT_OK
    agents = {a["id"]: a for a in client.get(f"/api/projects/{project['id']}/agents")}
    r = Renderer(agents, live=False)
    for e in events:
        r.handle(e)
    return EXIT_OK


def cmd_tasks(args, cfg: Config) -> int:
    client = Client(cfg)
    project = client.find_project(args.project)
    tasks = client.get(f"/api/projects/{project['id']}/tasks")
    names = {a["id"]: a["name"] for a in client.get(f"/api/projects/{project['id']}/agents")}
    rows = [{**t, "assignee": names.get(t["assignee_agent_id"], "?"),
             "by": names.get(t["created_by_agent_id"] or "", "Commander")} for t in tasks]
    emit(args, tasks, rows, [("id", "id"), ("status", "status"), ("title", "title"), ("by", "from"),
                             ("assignee", "to")])
    return EXIT_OK


def cmd_decide(args, cfg: Config) -> int:
    client = Client(cfg)
    _, run = _active(client, args.project)
    client.post(f"/api/runs/{run['id']}/tasks/{args.task_id}/{args.command}")
    emit(args, {"ok": True}, text=f"Task {args.command}d.")
    return EXIT_OK


# ------------------------------------------------------------------ parser
def build_parser() -> argparse.ArgumentParser:
    # SUPPRESS: options accepted before or after the subcommand without the subparser resetting them.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="machine-readable JSON output")
    common.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS,
                        help="disable colours (also: NO_COLOR=1)")
    common.add_argument("--server", default=argparse.SUPPRESS,
                        help="PLATO API URL for this command (default: saved server)")

    p = argparse.ArgumentParser(prog="plato", description="PLATO — Multiple Minds. One Intelligence. "
                                "Command your AI agent team from the terminal.", parents=[common])
    p.add_argument("--version", action="version", version=f"plato-cli {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    def add(name: str, fn, help_: str, aliases: list[str] | None = None) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_, parents=[common], aliases=aliases or [])
        sp.set_defaults(fn=fn)
        return sp

    s = add("login", cmd_login, "sign in (saves the session for this OS user)")
    s.add_argument("--email")
    s.add_argument("--register", action="store_true", help="create a new account instead")
    s.add_argument("--name", help="display name when registering")
    s.add_argument("--password-stdin", action="store_true", help="read the password from stdin")
    s.add_argument("--password-env", metavar="VAR", help="read the password from an environment variable")
    s = add("register", cmd_login, "create an account and sign in")
    s.add_argument("--email")
    s.add_argument("--name")
    s.add_argument("--password-stdin", action="store_true")
    s.add_argument("--password-env", metavar="VAR")
    s.set_defaults(register=True)
    add("logout", cmd_logout, "forget the saved session")
    add("whoami", cmd_whoami, "show the signed-in account")
    s = add("server", cmd_server, "show or set the PLATO server URL")
    s.add_argument("url", nargs="?")

    add("providers", cmd_providers, "list AI providers and connection status")
    s = add("connect", cmd_connect, "connect a provider (key is prompted, never passed as an argument)")
    s.add_argument("provider", help="e.g. openai, anthropic, huggingface, ollama, openai_compatible")
    s.add_argument("--base-url", help="server URL for ollama / lmstudio / openai_compatible")
    s.add_argument("--key-env", metavar="VAR", help="read the API key from an environment variable")
    s.add_argument("--key-stdin", action="store_true", help="read the API key from stdin")
    s.add_argument("--ask-key", action="store_true", help="prompt for an optional key (e.g. Ollama Cloud)")
    s = add("models", cmd_models, "list models a provider offers you")
    s.add_argument("provider")

    add("projects", cmd_projects, "list projects")
    s = add("new-project", cmd_new_project, "create a project")
    s.add_argument("name")
    s.add_argument("--description")
    s.add_argument("--mode", choices=MODES)
    s.add_argument("--budget", type=float, help="USD budget per run")
    s = add("agents", cmd_agents, "list a project's agents")
    s.add_argument("project", help="project name or id")
    s = add("add-agent", cmd_add_agent, "add an agent to a project")
    s.add_argument("project")
    s.add_argument("name")
    s.add_argument("--provider", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--role")
    s.add_argument("--instructions")
    s.add_argument("--parent", help="make it a subagent of this agent")
    s.add_argument("--url", help="endpoint for --provider external")
    s = add("remove-agent", cmd_remove_agent, "delete an agent")
    s.add_argument("project")
    s.add_argument("agent")

    for name, fn, help_ in (("run", cmd_run, "start a run and stream it live (Ctrl+C stops it)"),
                            ("watch", cmd_watch, "attach to the project's active run")):
        s = add(name, fn, help_)
        s.add_argument("project")
        if name == "run":
            s.add_argument("objective")
            s.add_argument("--mode", choices=MODES)
            s.add_argument("--budget", type=float, help="USD budget for this run")
        s.add_argument("--no-stream", action="store_true", help="print whole replies instead of tokens")
        s.add_argument("--detach-on-ctrl-c", action="store_true", help="Ctrl+C leaves the run going")
    s = add("say", cmd_say, "message agents in the active run")
    s.add_argument("project")
    s.add_argument("message")
    s.add_argument("--to", help="comma-separated agent names (default: all primary agents)")
    for name in ("pause", "resume", "stop"):
        s = add(name, cmd_control, f"{name} the active run")
        s.add_argument("project")
    s = add("interrupt", cmd_interrupt, "cut off one agent's current reply")
    s.add_argument("project")
    s.add_argument("agent")
    s = add("runs", cmd_runs, "list recent runs")
    s.add_argument("project")
    s.add_argument("--limit", type=int, default=10)
    s = add("history", cmd_history, "replay a run's conversation (latest by default)")
    s.add_argument("project")
    s.add_argument("--run")
    s = add("tasks", cmd_tasks, "list tasks")
    s.add_argument("project")
    for name in ("approve", "reject"):
        s = add(name, cmd_decide, f"{name} a delegated task awaiting approval")
        s.add_argument("project")
        s.add_argument("task_id")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    for opt, default in (("json", False), ("no_color", False), ("server", None)):
        if not hasattr(args, opt):
            setattr(args, opt, default)
    term.setup(color=False if args.no_color else None)
    if not getattr(args, "fn", None):
        parser.print_help()
        return EXIT_OK
    cfg = Config.load()
    if args.server and args.fn is not cmd_server:
        cfg.server = args.server.rstrip("/")
    try:
        return args.fn(args, cfg)
    except ApiError as exc:
        print(term.c(f"error: {exc}", "red"), file=sys.stderr)
        return EXIT_ERR
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return EXIT_ERR


if __name__ == "__main__":
    raise SystemExit(main())
