# demo runbook

## gb10 url

open:

```text
http://promaxgb10-5d0c:8000
```

fallback ip from the venue setup:

```text
http://10.103.132.14:8000
```

## services

```bash
systemctl status fuze-api
systemctl status ollama
docker ps
```

expected:

- `fuze-api` active
- `ollama` active
- `fuze-qdrant` running

## restart

```bash
sudo systemctl restart fuze-api
sudo systemctl restart ollama
docker restart fuze-qdrant
```

## smoke test

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS -X POST http://127.0.0.1:8000/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"get us ready for the anderson foundation report","role":"grant_manager"}'
```

look for:

- `cloud_llm_calls: 0`
- `always_on.enabled: true`
- `skill_label: Nonprofit Grants`
- `readiness_score: 72`
- three tasks
- blocked context present
