#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
exec "$PY" src/run/Run_Signal_Query.py
