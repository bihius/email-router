# email-router

Python based email router with a local LLM. The model picks a department by calling `send_email` (raw Ollama tools; LangChain comes later).

## Run

```bash
cp .env.example .env   # once; edit OLLAMA_MODEL if you want
docker compose up -d --build
```

| Service | URL |
| --- | --- |
| API docs | <http://localhost:8000/api/v1/docs> |
| MailHog UI | <http://localhost:8025> |
| Ollama | <http://localhost:11434> |

Default model is `OLLAMA_MODEL` in `.env` (`qwen2.5:3b`). `OLLAMA_TIMEOUT` is how many seconds one Ollama reply may take. `OLLAMA_NUM_CTX` is the context size reserved when the model loads (default 2048). The `ollama-pull` one-shot downloads that model once Ollama is healthy.

## Example request

The model chooses the department by calling `send_email`. The request has no department field.

```bash
curl -sS -X POST http://localhost:8000/api/v1/route \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jan.nowak@example.com",
    "message": "Nie działa mi komputer"
  }'
```

Then open MailHog and check `To: it@example.com` and `Reply-To: jan.nowak@example.com`.
