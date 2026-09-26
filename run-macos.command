#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ $(uname -s) == Darwin ]] || { echo 'Este lançador é para macOS.' >&2; exit 1; }
exec conda run --no-capture-output -n nexum-build python -m nexum.main
