#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Ambiente não instalado. Rode ./install-fedora.sh primeiro." >&2
  exit 1
fi
exec .venv/bin/python -m nexum.main
