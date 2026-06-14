#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 offline/verify_demo.py "${1:-http://127.0.0.1:8000}"
