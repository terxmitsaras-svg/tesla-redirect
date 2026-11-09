# plato — PLATO in your terminal

Run and watch your AI agent team from **PowerShell**, **Windows Terminal**, **macOS Terminal**, or any
**Linux / Kali / Chromebook** shell. Pure Python (3.11+), no compiler needed.

## Install

```bash
pipx install ./cli          # recommended: isolated, puts `plato` on your PATH
# or
pip install ./cli
```

The PLATO installers (`scripts/install.sh`, `scripts/install.ps1`) install it for you into `.venv`.

## Use

```powershell
plato login --server http://localhost:8000        # or: plato register
plato connect anthropic                           # key is prompted (hidden), never typed as an argument
plato connect ollama --base-url http://192.168.1.10:11434/v1
plato new-project "Launch plan"
plato add-agent "Launch plan" Architect --provider anthropic --model claude-opus-5-5 --role "Software architect"
plato add-agent "Launch plan" Developer --provider ollama --model llama3.2 --role "Lead developer"
plato run "Launch plan" "Design the data model and API for a task tracker"
```

`plato run` streams the conversation live. When several agents speak at once it follows one speaker
and prints the others' replies in full when they finish. **Ctrl+C stops the run** on the server (use
`--detach-on-ctrl-c` to leave it running).

From a second terminal while a run is active:

```bash
plato say "Launch plan" "Focus on the API first" --to Developer
plato pause "Launch plan"      # resume / stop / interrupt "Launch plan" Developer
plato watch "Launch plan"      # attach to the live run
plato history "Launch plan"    # replay the latest run
```

## Scripting

Every listing accepts `--json`; `plato run --json` emits one JSON event per line (NDJSON).

```powershell
# Parentheses make this work in both Windows PowerShell 5.1 and PowerShell 7
(plato agents "Launch plan" --json | ConvertFrom-Json) | Select-Object name, provider, model
```

```bash
plato run "Launch plan" "Summarise the spec" --json | jq -r 'select(.type=="agent.turn.completed") | .data.visible_text'
```

Exit codes for `run`/`watch`: `0` completed, `3` limit reached, `4` stopped, `1` error.

Environment overrides: `PLATO_SERVER`, `PLATO_TOKEN`, `PLATO_CONFIG_DIR`, `NO_COLOR`.
Secrets in scripts: `--password-env VAR`, `--key-env VAR`, or `--key-stdin`.

## Where the session is stored

| OS | Path |
|---|---|
| Windows | `%APPDATA%\PLATO\config.json` |
| macOS | `~/Library/Application Support/PLATO/config.json` |
| Linux, Kali, ChromeOS | `~/.config/plato/config.json` (mode 600) |

`plato logout` removes the saved token.
