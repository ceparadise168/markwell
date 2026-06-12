"""Persisted GUI preferences — one small JSON file at ~/.markwell/config.json.

The only key today is `"data_dir"`: where the GUI keeps backups and exports.
The GUI lets the reader relocate that folder (e.g. into an iCloud/Dropbox/Drive
sync folder for cloud backup without any APIs), and the choice must survive
restarts — hence this file. The CLI is unaffected: it takes flags only and
never reads or writes this config.

Resilience contract: `load()` never raises. A missing, unreadable, corrupt, or
wrong-shaped config means `{}` — falling back to defaults must never block the
app from starting. `save()` writes atomically (tmp file + `os.replace`) so a
crash mid-write can never leave a half-written config behind.

`MARKWELL_CONFIG_DIR` overrides the directory (used by tests to stay out of the
real home folder).
"""
from __future__ import annotations

import json
import os
import pathlib


def config_path() -> pathlib.Path:
    """The config file's location, honoring the MARKWELL_CONFIG_DIR override."""
    base = pathlib.Path(os.environ.get("MARKWELL_CONFIG_DIR", "~/.markwell"))
    return base.expanduser() / "config.json"


def load() -> dict:
    """Read the config; any problem at all means `{}`, never an exception."""
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):  # missing, unreadable, or invalid JSON
        return {}
    return data if isinstance(data, dict) else {}


def save(cfg: dict) -> None:
    """Write the whole config atomically.

    The tmp file has a fixed name, so even a write that dies before the
    `os.replace` leaves at most one stray file, overwritten by the next save —
    nothing accumulates and the real config is never half-written.
    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(str(tmp), str(path))
