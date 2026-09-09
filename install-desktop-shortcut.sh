#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/io.github.nexum.ScientificWorkbench.desktop" <<EOF
[Desktop Entry]
Name=Nexum Scientific Workbench
Comment=Ambiente computacional de química
Exec=$ROOT/run.sh
Path=$ROOT
Terminal=false
Type=Application
Icon=applications-science
Categories=Education;Science;Chemistry;
StartupNotify=true
EOF
update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "Atalho instalado no menu de aplicativos."
