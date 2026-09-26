# email-router

PoC of an AI message router. A FastAPI service passes the incoming message to a LangChain agent backed by a local Ollama model. The agent picks a department and calls the `send_email` tool, and MailHog captures the message.

## Run

```bash
cp .env.example .env   # optional: only to override defaults
docker compose up -d
```

On first start, `ollama-pull` downloads the model (`qwen2.5:7b`, about 4.7 GB). The API waits for the download to finish, so it is ready as soon as its container is up. On CPU, the first request also loads the model into memory and can take a while.

| Service | URL |
| --- | --- |
| API docs (Swagger) | <http://localhost:8000/api/v1/docs> |
| MailHog UI | <http://localhost:8025> |

## Example request

```bash
curl -sS -X POST http://localhost:8000/api/v1/route \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jan.nowak@example.com",
    "message": "Nie działa mi komputer"
  }'
```

```json
{"status": "sent", "department": "it", "to": "it@example.com"}
```

In MailHog, the message has `To: it@example.com` and `Reply-To: jan.nowak@example.com`. If the model answers with plain text instead of calling the tool, no mail is sent and the API returns `502`.

## Architecture decisions

- **One tool with a constrained argument.** The agent has a single `send_email(department)` tool. The argument schema is a `Literal` of the department names from the catalog. If the model picks a name that is not in the catalog, validation rejects it and the agent gives the model the error so it can retry. The agent loop is capped, and each request sends at most one mail.
- **Routing only through the tool call.** The app never parses a department out of free-form model output. No tool call means no mail.
- **The model chooses, the code addresses the mail.** The tool closes over the original message and the sender, so the model sees department names and descriptions but never the addresses. The mail's `To` comes from the catalog, `Reply-To` is the sender from the request, and the body is the original message.
- **Department catalog in `data/departments.csv`** (`name`, `email`, `description`). The system prompt is built from this file, so adding a department means adding one row. The file must include an `other` row as the fallback.
- **Cleaned text goes to the model, the original goes in the mail.** Before the message reaches the model, data URIs and long base64 runs (such as inline images in an email footer) are replaced with `[attachment omitted]`, and everything after a signature delimiter line (`-- ` or `--`) is dropped. One embedded image can be larger than the 2048-token context, and signatures add words that only confuse routing. The forwarded mail keeps the full original message.
- **Ready after `docker compose up -d`.** A one-shot `ollama-pull` container downloads the weights, and the API starts only after it finishes successfully. Ollama and SMTP are reachable only inside the Compose network. Only the API and the MailHog UI are published.
- **Model `qwen2.5:7b`, temperature 0, context 2048.** It supports tool calling in Ollama and runs acceptably on CPU. Model, timeout, context size and log level can be changed in `.env` (see `.env.example`).

## Tests

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```

The tests replace Ollama with a scripted chat model and replace SMTP with a mock, so they need no running containers.
