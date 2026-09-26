# email-router

Python based email router with a local LLM. A LangChain agent calls `send_email`; the department catalog is `data/departments.csv`.

## Run

```bash
docker compose up -d --build
```

No `.env` file is required. Defaults are model `qwen2.5:7b`, timeout 180 seconds, context 2048 tokens, and `LOG_LEVEL=warning`. Copy `.env.example` to `.env` only when you want to override them.

The API container starts after `ollama-pull` has finished, so the model is downloaded before the first request.

| Service | URL |
| --- | --- |
| API docs | <http://localhost:8000/api/v1/docs> |
| MailHog UI | <http://localhost:8025> |
| Ollama | <http://localhost:11434> |

`LOG_LEVEL=warning` hides the one-line access log. Set it to `info` or `debug` to see those lines. `OLLAMA_DEBUG=1` turns Ollama's extra trace on.

## Departments

`data/departments.csv` has three columns: `name`, `email`, `description`. The system prompt is built from the name and the description. The model never sees the address. `send_email` uses the email from that row, and `Reply-To` is the sender from the request. Add a department by adding a row. The file must include a row named `other`.

Long base64 (a footer image) and a `--` signature are removed from the text sent to the model. The mail body stays the original message. Context 2048 is for the words, not for the image.

## Architecture decisions

- One tool, `send_email`. The department is an argument, and the allowed names come from the CSV catalog. There is not a separate tool for each department.
- Departments live in `data/departments.csv` (`name`, `email`, `description`). They are not environment variables, and they are not hardcoded in the prompt. The prompt is built from each row's name and description. The model does not see the address.
- A LangChain agent (`ChatOllama` and `create_agent`) calls that tool. The application does not parse a department name out of free-text prose. If the model answers with prose and never calls the tool, nothing is sent.
- Compose uses the official MailHog image. The API sends the message to it over SMTP. `Reply-To` is the requester address. `To` is the department address.
- Ollama uses `qwen2.5:7b` by default, with `num_ctx` 2048. The timeout comes from the environment. The `ollama-pull` one-shot must finish before the API starts.
- `docker compose up -d --build` works with those defaults. No hand-made `.env` file is required.
- Text sent to the model drops data-URI and long base64 blobs, then drops a signature that starts on a line of `--`. The email that is sent keeps the original message.

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
