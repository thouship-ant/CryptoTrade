#!/usr/bin/env bash
# Usage: Run_DB_Trading_BOT.sh <username> <api_key> <api_secret> [script]
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
[ $# -ge 3 ] || { echo "Usage: $0 <username> <api_key> <api_secret> [script]"; exit 1; }
SCRIPT="${4:-src/DB_Trading_BOT_Future.py}"
exec "$PY" "$SCRIPT" "$1" "$2" "$3"
