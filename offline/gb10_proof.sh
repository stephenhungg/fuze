#!/usr/bin/env bash
set -euo pipefail

base_url="${1:-http://127.0.0.1:8000}"
goal="${2:-get us ready for the anderson foundation report}"

header() {
  printf "\n\\033[1;38;5;208m== %s ==\\033[0m\n" "$1"
}

json() {
  python3 -m json.tool
}

header "fuze gb10 proof"
date
printf "host: "
hostname
printf "user: "
whoami
printf "base url: %s\n" "$base_url"

header "local network"
hostname -I 2>/dev/null || ip addr show 2>/dev/null | sed -n '1,80p' || true

header "gpu proof"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits
else
  echo "nvidia-smi not found"
fi

header "service proof"
if command -v systemctl >/dev/null 2>&1; then
  systemctl is-active fuze-api || true
  systemctl is-active ollama || true
else
  echo "systemctl not available"
fi

if command -v docker >/dev/null 2>&1; then
  docker ps --filter name=fuze-qdrant --format 'qdrant={{.Names}} status={{.Status}} ports={{.Ports}}' || true
fi

header "runtime health"
curl -fsS "$base_url/health" | json

header "trigger live agent run"
curl -fsS -X POST "$base_url/agent/run" \
  -H 'content-type: application/json' \
  -d "$(python3 - <<PY
import json
print(json.dumps({"goal": "$goal", "role": "grant_manager", "user_id": "morgan"}))
PY
)" | python3 - <<'PY'
import json
import sys

data = json.load(sys.stdin)
audit = data["audit"]
packet = data["context_packet"]
print(f"status: {data['status']}")
print(f"readiness: {packet['readiness_score']}%")
print(f"cloud_llm_calls: {audit['model_runtime']['cloud_calls']}")
print(f"runtime_provider: {audit['model_runtime']['provider']}")
print(f"sources: {', '.join(audit['sources_used'][:6])}")
print(f"blocked_context: {len(audit['context_blocked'])}")
print(f"tasks: {len(data['tasks'])}")
print(f"approvals: {len(data['approvals'])}")
PY

header "recent fuze api logs"
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u fuze-api -n 40 --no-pager || true
else
  echo "journalctl not available"
fi

header "watch mode"
echo "leave this running during the pitch, then click run in the browser."
echo "press ctrl-c when done."
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u fuze-api -f --no-pager
else
  echo "fallback: polling /agents/events every 2s"
  while true; do
    curl -fsS "$base_url/agents/events" | python3 - <<'PY' || true
import json
import sys
from datetime import datetime

data = json.load(sys.stdin)
events = data.get("events", [])[:5]
print(f"\n{datetime.now().isoformat(timespec='seconds')}")
for event in events:
    print(f"{event.get('created_at')} {event.get('agent_id')} {event.get('type')} {event.get('message')}")
PY
    sleep 2
  done
fi
