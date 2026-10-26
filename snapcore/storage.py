"""Crash-safe JSON persistence.

* Writes are atomic (temp file + fsync + os.replace) so a crash or power
  loss mid-write can never leave a half-written file.
* The previous good version is kept as ``<name>.bak``.
* A file that fails to parse is moved aside (``*.corrupt-<time>``) instead
  of being silently overwritten with defaults, so user data is never lost.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("snaptype.storage")
_write_lock = threading.Lock()


def _read(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_json(path: Path, default: Any) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    try:
        return _read(path)
    except (OSError, ValueError) as exc:
        log.error("Could not read %s: %s", path, exc)

    # Main file unreadable: quarantine it, then try the backup.
    try:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path.replace(path.with_name(f"{path.name}.corrupt-{stamp}"))
    except OSError:
        pass
    bak = path.with_name(path.name + ".bak")
    if bak.exists():
        try:
            data = _read(bak)
            log.warning("Recovered %s from backup", path.name)
            return data
        except (OSError, ValueError):
            pass
    return default


def save_json(path: Path, data: Any) -> bool:
    """Atomically write ``data`` as JSON. Returns False (and logs) on failure."""
    path = Path(path)
    with _write_lock:
        tmp_name = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp",
                                            dir=str(path.parent))
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            if path.exists():
                try:
                    shutil.copy2(path, path.with_name(path.name + ".bak"))
                except OSError:
                    pass
            os.replace(tmp_name, path)
            return True
        except (OSError, TypeError, ValueError) as exc:
            log.error("Could not save %s: %s", path, exc)
            if tmp_name:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
            return False
