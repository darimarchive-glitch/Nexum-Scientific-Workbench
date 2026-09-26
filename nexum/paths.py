"""Platform-native user data; preserve existing Linux and Windows locations."""
from pathlib import Path
import os
import sys


def data_dir():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Nexum"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local") / "Nexum"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "nexum-lab"


def cache_dir():
    if sys.platform == "darwin":
        return Path.home() / "Library/Caches/Nexum"
    if sys.platform == "win32":
        return data_dir() / "Cache"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "nexum-lab"

