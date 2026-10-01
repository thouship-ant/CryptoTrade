#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
exec "$PY" src/telegram/message_listener.py
