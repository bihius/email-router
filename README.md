# email-router

Python based email router with local LLM (agent + tool calling). LLM wiring comes next; mail path already works.

## Run

```bash
docker compose up -d --build
```

| Service | URL |
| --- | --- |
| API docs | <http://localhost:8000/api/v1/docs> |
| MailHog UI | <http://localhost:8025> |

## Example request

Department is temporary in the JSON until the agent chooses it:

```bash
curl -sS -X POST http://localhost:8000/api/v1/route \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jan.nowak@example.com",
    "message": "Nie działa mi komputer",
    "department": "it"
  }'
```

Then open MailHog and check `To: it@example.com` and `Reply-To: jan.nowak@example.com`.
