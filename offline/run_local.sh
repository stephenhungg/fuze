#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
