"""Writable user paths; keep existing Linux locations unchanged."""
from pathlib import Path
import os
import sys


def data_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local") / "Nexum"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "nexum-lab"


def cache_dir():
    if sys.platform == "win32":
        return data_dir() / "Cache"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "nexum-lab"

