"""Per-user config (server URL + session token), stored where each OS expects it.

Windows: %APPDATA%\\PLATO\\config.json        macOS: ~/Library/Application Support/PLATO/config.json
Linux / Kali / ChromeOS: $XDG_CONFIG_HOME/plato/config.json (default ~/.config/plato)

Overrides (handy for CI and scripts): PLATO_CONFIG_DIR, PLATO_SERVER, PLATO_TOKEN.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SERVER = "http://localhost:8000"


def config_dir() -> Path:
    if os.environ.get("PLATO_CONFIG_DIR"):
        return Path(os.environ["PLATO_CONFIG_DIR"])
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "PLATO"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "PLATO"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "plato"


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class Config:
    server: str = DEFAULT_SERVER
    token: str | None = None
    email: str | None = None

    @classmethod
    def load(cls) -> Config:
        data: dict = {}
        try:
            data = json.loads(config_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        cfg = cls(server=data.get("server") or DEFAULT_SERVER, token=data.get("token"), email=data.get("email"))
        cfg.server = os.environ.get("PLATO_SERVER") or cfg.server
        cfg.token = os.environ.get("PLATO_TOKEN") or cfg.token
        cfg.server = cfg.server.rstrip("/")
        return cfg

    def save(self) -> Path:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"server": self.server, "token": self.token, "email": self.email}, indent=2)
        # Create with owner-only permissions on POSIX (the token is a credential). On Windows the file
        # lives in the user's profile, which is already private to that account.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        if os.name == "posix":
            os.chmod(path, 0o600)
        return path
