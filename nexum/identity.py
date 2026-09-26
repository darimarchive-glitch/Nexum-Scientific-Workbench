"""Stable application identity and distribution names, independent of the UI."""

import re

APP_NAME = "Nexum"
APP_DESCRIPTION = "Scientific Workbench"
APP_ID = "io.github.nexum.ScientificWorkbench"  # Legacy ID: retain installed-user continuity.
VERSION = "7.0.0-preview.1"
PROJECT_EXTENSION = ".nexum7"


def artifact_name(system, arch="x86_64", version=VERSION):
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?", version):
        raise ValueError("Versão inválida.")
    if arch not in ("x86_64", "arm64", "aarch64"):
        raise ValueError("Arquitetura não suportada.")
    if system == "source":
        return f"Nexum-{version}-source.zip"
    if system == "windows":
        if arch != "x86_64":
            raise ValueError("O instalador Windows atual é x86_64.")
        return f"Nexum-{version}-windows-x86_64-setup.exe"
    if system == "linux":
        return f"Nexum-{version}-linux-{'aarch64' if arch == 'arm64' else arch}.flatpak"
    if system == "macos":
        return f"Nexum-{version}-macos-{'arm64' if arch == 'aarch64' else arch}.dmg"
    raise ValueError("Sistema desconhecido.")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("field", choices=["version", "id", "artifact"])
    p.add_argument("--system", default="source")
    p.add_argument("--arch", default="x86_64")
    a = p.parse_args()
    print(
        VERSION
        if a.field == "version"
        else APP_ID
        if a.field == "id"
        else artifact_name(a.system, a.arch)
    )
