#!/usr/bin/env sh
# Tarjuman: run ./start.sh. The first run installs everything (a few minutes).
set -e
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/backend${PYTHONPATH:+:$PYTHONPATH}"

if [ ! -x .venv/bin/python ]; then
  echo "\n  First run: setting up Tarjuman..."
  PY=$(command -v python3.13 || command -v python3 || command -v python || true)
  if [ -z "$PY" ]; then
    echo "  Python 3.11+ was not found. Install it from https://www.python.org/downloads/ and run this again."
    exit 1
  fi
  "$PY" -m venv .venv
  .venv/bin/python -m tarjuman setup
fi

exec .venv/bin/python -m tarjuman "$@"
