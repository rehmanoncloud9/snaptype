"""Where SnapType keeps its data."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import APP_NAME

LEGACY_DIR = Path.home() / ".snaptype"


def data_dir() -> Path:
    """Per-user data directory.

    Override with the SNAPTYPE_HOME environment variable (used by tests and
    portable installs). On Windows this is %APPDATA%\\SnapType; elsewhere
    ~/.snaptype.
    """
    override = os.environ.get("SNAPTYPE_HOME")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME
    return LEGACY_DIR


def migrate_legacy(target: Path) -> bool:
    """Copy v1.2 data from ~/.snaptype into the new location (once)."""
    if target == LEGACY_DIR or target.exists() or not LEGACY_DIR.is_dir():
        return False
    try:
        shutil.copytree(LEGACY_DIR, target)
        return True
    except OSError:
        return False


DATA_DIR = data_dir()
CONFIG_FILE = DATA_DIR / "config.json"
SNIPPETS_FILE = DATA_DIR / "snippets.json"
STATS_FILE = DATA_DIR / "stats.json"
LOG_FILE = DATA_DIR / "snaptype.log"
