#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
exec "$PY" src/DB_BreakOut_trade.py
