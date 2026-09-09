#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY="python3"
if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; fi
"$PY" -m unittest discover -s tests -v
"$PY" -m compileall -q nexum
