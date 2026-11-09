"""End-to-end tests for the `plato` CLI against a real PLATO API process (simulated provider)."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from plato_cli import config as cfgmod
from plato_cli.main import EXIT_ERR, EXIT_OK, EXIT_STOPPED, main
from plato_cli.stream import visible

BACKEND = Path(__file__).resolve().parents[2] / "backend"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    port = _free_port()
    db = tmp_path_factory.mktemp("db") / "cli.db"
    env = {**os.environ, "PLATO_ENV": "test", "PLATO_DATABASE_URL": f"sqlite+aiosqlite:///{db.as_posix()}",
           "PLATO_ENABLE_MOCK_PROVIDER": "true", "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
                            cwd=BACKEND, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if httpx.get(f"{url}/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError("API did not start:\n" + proc.stdout.read().decode(errors="replace"))
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def cli(server, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PLATO_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.delenv("PLATO_TOKEN", raising=False)
    monkeypatch.delenv("PLATO_SERVER", raising=False)

    def run(*argv: str) -> tuple[int, str, str]:
        capsys.readouterr()
        code = main(list(argv))
        out, err = capsys.readouterr()
        return code, out, err

    monkeypatch.setenv("PLATO_TEST_PW", "correct-horse-battery")
    email = f"cli-{time.time_ns()}@plato.dev"
    code, out, err = run("register", "--server", server, "--email", email, "--password-env", "PLATO_TEST_PW")
    assert code == EXIT_OK, err
    run.email = email  # type: ignore[attr-defined]
    return run


def _team(cli, slow: bool = False) -> str:
    name = f"proj-{time.time_ns()}"
    assert cli("new-project", name)[0] == EXIT_OK
    model = "sim-slow" if slow else "sim-fast"
    assert cli("add-agent", name, "Architect", "--provider", "mock", "--model", model, "--role", "architect")[0] == 0
    assert cli("add-agent", name, "Developer", "--provider", "mock", "--model", model, "--role", "developer")[0] == 0
    return name


def test_login_session_is_saved_with_private_permissions(cli, server):
    code, out, _ = cli("whoami", "--json")
    me = json.loads(out)
    assert code == 0 and me["email"] == cli.email and me["server"] == server
    path = cfgmod.config_path()
    saved = json.loads(path.read_text())
    assert saved["server"] == server and saved["token"]
    if os.name == "posix":
        assert (path.stat().st_mode & 0o777) == 0o600


def test_full_run_streams_agent_to_agent_conversation(cli):
    name = _team(cli)
    code, out, err = cli("run", name, "Design a URL shortener")
    assert code == EXIT_OK, err
    assert "▶ Run started" in out
    assert "[Architect]" in out and "[Developer]" in out          # both agents streamed
    assert "✉ Architect → Developer:" in out and "✉ Developer → Architect:" in out
    assert "<message" not in out and "</done>" not in out          # directives hidden from the stream
    assert "■ Run completed" in out

    code, out, _ = cli("history", name)
    assert code == 0 and "✉ Architect → Developer:" in out and "■ Run completed" in out
    code, out, _ = cli("runs", name, "--json")
    assert json.loads(out)[0]["status"] == "completed"
    code, out, _ = cli("tasks", name)
    assert code == 0 and "completed" in out
    code, out, _ = cli("agents", name, "--json")
    assert {a["name"] for a in json.loads(out)} == {"Architect", "Developer"}


def test_run_json_is_ndjson_for_scripting(cli):
    name = _team(cli)
    code, out, _ = cli("run", name, "x", "--json")
    events = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert code == 0
    assert any(e["type"] == "agent.delta" for e in events)
    assert events[-1]["type"] == "run.status" and events[-1]["data"]["status"] == "completed"


def test_stop_from_another_terminal(cli):
    """`plato run` in one process, `plato say` / `plato stop` from another, like two terminal windows."""
    name = _team(cli, slow=True)
    proc = subprocess.Popen([sys.executable, "-m", "plato_cli", "run", name, "slow job", "--no-stream"],
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"},  # Windows pipes default to cp1252
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def running() -> bool:
        runs = json.loads(cli("runs", name, "--json")[1])
        return bool(runs) and runs[0]["status"] == "running"

    deadline = time.time() + 20
    while not running():
        assert time.time() < deadline, "run never started"
        time.sleep(0.2)
    assert cli("say", name, "Focus on the API first", "--to", "Developer")[0] == EXIT_OK
    assert cli("stop", name)[0] == EXIT_OK
    out = proc.communicate(timeout=30)[0].decode(errors="replace")
    assert proc.returncode == EXIT_STOPPED, out
    assert "› You → Developer: Focus on the API first" in out and "■ Run stopped" in out
    assert json.loads(cli("runs", name, "--json")[1])[0]["status"] == "stopped"


def test_providers_and_connect_validation(cli):
    code, out, _ = cli("providers", "--json")
    ids = {p["id"] for p in json.loads(out)}
    assert {"openai", "anthropic", "huggingface", "ollama", "openai_compatible"} <= ids
    code, _, err = cli("connect", "nope")
    assert code == EXIT_ERR and "Unknown provider" in err
    code, _, err = cli("connect", "openai_compatible")  # base URL required
    assert code == EXIT_ERR and "base URL" in err


def test_helpful_errors(server, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PLATO_CONFIG_DIR", str(tmp_path / "empty"))
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["projects", "--server", server]) == EXIT_ERR
    assert "plato login" in capsys.readouterr().err
    monkeypatch.setenv("PLATO_TOKEN", "x")
    assert main(["projects", "--server", "http://127.0.0.1:9"]) == EXIT_ERR
    assert "Cannot reach the PLATO server" in capsys.readouterr().err


# ------------------------------------------------------------------ units
def test_stream_filter_only_ever_grows():
    final = ('Plan: split work. <message to="Dev">which part?</message> Then a < b and '
             '<task to="R" title="t">do</task> end <done>ok</done>')
    printed = ""
    for i in range(1, len(final) + 1):
        vis = visible(final[:i])
        assert vis.startswith(printed), (i, printed, vis)  # never retracts printed text
        printed = vis
    assert printed == "Plan: split work.  Then a < b and  end "


@pytest.mark.parametrize("platform,env,expected", [
    ("win32", {"APPDATA": r"C:\Users\ada\AppData\Roaming"}, ("PLATO",)),
    ("darwin", {}, ("Library", "Application Support", "PLATO")),
    ("linux", {"XDG_CONFIG_HOME": "/tmp/xdg"}, ("xdg", "plato")),
])
def test_config_dir_per_os(platform, env, expected, monkeypatch):
    monkeypatch.delenv("PLATO_CONFIG_DIR", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(sys, "platform", platform)
    parts = Path(cfgmod.config_dir()).parts
    assert tuple(parts[-len(expected):]) == expected


def test_renderer_keeps_concurrent_replies_readable():
    from plato_cli.stream import Renderer

    agents = {"a": {"name": "Architect"}, "d": {"name": "Developer"}}
    out: list[str] = []
    r = Renderer(agents, live=True, out=out.append)
    a_text = 'I will own the data model. <message to="Developer">Which DB?</message>'
    d_text = "I will own the API layer. <done>API drafted</done>"

    def ev(t, aid, **data):
        return {"type": t, "agent_id": aid, "data": data}

    r.handle(ev("agent.turn.started", "a", turn_id="ta"))
    r.handle(ev("agent.turn.started", "d", turn_id="td"))
    a_words, d_words = a_text.split(" "), d_text.split(" ")
    for i in range(max(len(a_words), len(d_words))):  # tokens arrive interleaved
        if i < len(a_words):
            r.handle(ev("agent.delta", "a", turn_id="ta", text=a_words[i] + " "))
        if i < len(d_words):
            r.handle(ev("agent.delta", "d", turn_id="td", text=d_words[i] + " "))
    # Developer finishes first while Architect is still the live speaker.
    r.handle(ev("agent.turn.completed", "d", turn_id="td", text=d_text, done="API drafted"))
    r.handle(ev("agent.turn.completed", "a", turn_id="ta", text=a_text, done=None))
    r.handle(ev("message.sent", "a", **{"from": "a", "from_name": "Architect", "to_names": ["Developer"],
                                         "content": "Which DB?", "kind": "message"}))
    text = "".join(out)
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]  # trailing spaces are invisible
    assert lines[0] == "[Architect] I will own the data model."
    assert lines[1] == "[Developer] I will own the API layer."
    assert lines[2] == "  ✓ Developer done: API drafted"
    assert lines[3] == "  ✉ Architect → Developer: Which DB?"
    assert text.count("[Architect]") == 1 and text.count("[Developer]") == 1
