#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if command -v dnf5 >/dev/null 2>&1; then DNF=dnf5; else DNF=dnf; fi
if ! command -v "$DNF" >/dev/null 2>&1; then
  echo "Este instalador é para Fedora (dnf/dnf5 não encontrado)." >&2
  exit 1
fi

echo "Nexum GNOME · preparando dependências nativas para Fedora"
sudo "$DNF" install -y \
  python3 python3-pip python3-gobject gtk4 libadwaita \
  mesa-libGL mesa-libEGL xdg-utils

# PyGObject/GTK/libadwaita vêm do Fedora. O venv herda esses pacotes do sistema,
# enquanto as bibliotecas científicas/3D ficam isoladas no projeto.
if [[ ! -d .venv ]]; then
  python3 -m venv --system-site-packages .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# Diagnóstico explícito antes de abrir a GUI.
.venv/bin/python - <<'PY'
import gi
gi.require_version('Gtk','4.0')
gi.require_version('Adw','1')
from gi.repository import Gtk, Adw
import OpenGL, numpy, scipy, gemmi, rdkit
print('GTK4/libadwaita/NumPy/SciPy/PyOpenGL/gemmi/RDKit: OK')
PY

./test.sh
cat <<'EOF'

Instalação concluída.
Execute: ./run.sh
Opcional: ./install-desktop-shortcut.sh
EOF
