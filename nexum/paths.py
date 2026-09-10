"""Writable user paths; keep existing Linux locations unchanged."""
from pathlib import Path
import os
import sys


def data_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local") / "Nexum"
    return Path.home() / ".local/share/nexum-lab"


def cache_dir():
    if sys.platform == "win32":
        return data_dir() / "Cache"
    return Path.home() / ".cache/nexum-lab"
