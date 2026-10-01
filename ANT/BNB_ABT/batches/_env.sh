#!/usr/bin/env bash
# Shared setup: resolves project root and the venv python (Windows Git Bash or Linux/macOS).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -x "$ROOT/venv/Scripts/python.exe" ]; then
    PY="$ROOT/venv/Scripts/python.exe"
elif [ -x "$ROOT/venv/bin/python" ]; then
    PY="$ROOT/venv/bin/python"
else
    PY="$(command -v python3 || command -v python)"
fi
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
