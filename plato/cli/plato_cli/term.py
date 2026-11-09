"""Terminal output that behaves on Windows (PowerShell/cmd/Windows Terminal), macOS and Linux.

* Enables ANSI escape processing on Windows 10+ consoles (legacy conhost needs it switched on).
* Never crashes on characters the console encoding can't show (e.g. redirected output on cp1252).
* Honours NO_COLOR, --no-color, and disables colour when output is not a terminal.
"""
from __future__ import annotations

import os
import sys

_COLORS = {"cyan": 96, "blue": 94, "magenta": 95, "green": 92, "yellow": 93, "red": 91, "grey": 90, "white": 97}
AGENT_PALETTE = ["cyan", "blue", "magenta", "green", "yellow", "white"]
_enabled = False


def _enable_windows_vt() -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        return False


def setup(color: bool | None = None) -> None:
    global _enabled
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    if color is False or os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        _enabled = False
        return
    _enabled = _enable_windows_vt() if sys.platform == "win32" else True


def c(text: str, color: str, bold: bool = False) -> str:
    if not _enabled:
        return text
    code = _COLORS.get(color, 97)
    return f"\033[{'1;' if bold else ''}{code}m{text}\033[0m"


def table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    """Plain-text table. columns = [(key, header)]."""
    if not rows:
        return c("(none)", "grey")
    cells = [[str(r.get(k, "") if r.get(k) is not None else "") for k, _ in columns] for r in rows]
    widths = [max(len(h), *(len(row[i]) for row in cells)) for i, (_, h) in enumerate(columns)]
    head = "  ".join(h.upper().ljust(w) for (_, h), w in zip(columns, widths, strict=True))
    lines = [c(head, "grey")]
    lines += ["  ".join(v.ljust(w) for v, w in zip(row, widths, strict=True)) for row in cells]
    return "\n".join(lines)
