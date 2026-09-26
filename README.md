# email-router

PoC of an AI message router. A FastAPI service passes the incoming message to a LangChain agent backed by a local Ollama model. The agent picks a department and calls the `send_email` tool, and MailHog captures the message.

An optional second engine, [Laya](https://huggingface.co/convaiinnovations/laya), can make the same decision with a local System One decision model instead of an LLM (see [Optional: Laya engine](#optional-laya-engine)).

## Run

```bash
cp .env.example .env   # optional: only to override defaults
docker compose up -d
```

On first start, `ollama-pull` downloads the model (`qwen2.5:7b`, about 4.7 GB). The API waits for the download to finish, and its container reports `healthy` once it accepts requests (`docker compose up -d --wait` blocks until then). On CPU, the first request also loads the model into memory and can take a while.

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
{"status": "sent", "department": "it", "to": "it@example.com", "engine": "ollama", "probability": null}
```

In MailHog, the message has `To: it@example.com` and `Reply-To: jan.nowak@example.com`. If the model never makes a valid tool call, no mail is sent and the API returns `502`.

## Optional: Laya engine

Routing a ticket is a classification: one choice out of five known options. An LLM does it by generating a tool call token by token. System One models, a newer class introduced by TypeSafe AI with [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), answer a typed question such as "which of these options?" in a single forward pass. They return a probability for every option and no text. Jev is a hosted API and this task requires local models, so this project uses [Laya](https://huggingface.co/convaiinnovations/laya), an open-source (Apache-2.0) System One model that runs locally and serves a Jev-compatible HTTP API.

The brief does not ask for this. It is included because it fits the problem well. To switch engines, set one line in `.env`:

```bash
cp .env.example .env
# in .env: ROUTER_ENGINE=laya
docker compose up -d
```

`COMPOSE_PROFILES=${ROUTER_ENGINE}` in `.env` starts the `laya` container. It is built from `laya-serve/Dockerfile` (CPU PyTorch, about 1.5 GB) and downloads the `laya-multilingual` checkpoint (about 650 MB) into a volume. The API waits until the checkpoint is loaded. Ollama still starts, because the brief requires it. The response then reports `"engine": "laya"` and the probability Laya gave the chosen department.

Measured on the same 14 Polish and English tickets (CPU, Apple M4, Docker, warm models, including the API and SMTP round trip):

| Engine | Correct | Time per ticket |
| --- | --- | --- |
| Ollama `qwen2.5:7b` agent (default) | 14/14 | 5.5–19.6 s |
| Laya `laya-multilingual` | 11/14 | 0.27–0.61 s |

Laya was about 18× faster (median 0.36 s against 6.5 s) but zero-shot less accurate. It sent "cannot log in to VPN" to `kadry`, "when is payday" to `other`, and "conflict with my manager" to `kadry`. Its probabilities are uncalibrated. Its authors report the largest accuracy gains from fine-tuning on your own decisions, which is the natural next step and is outside this PoC. Ollama therefore stays the default. Fourteen tickets are a smoke check, not a benchmark.

## Architecture decisions

- **One tool with a constrained argument.** The agent has a single `send_email(department)` tool. The argument schema is a `Literal` of the department names from the catalog. If the model picks a name that is not in the catalog, validation rejects it and the agent gives the model the error so it can retry. The agent loop is capped, and each request sends at most one mail. If the model keeps calling the tool after the mail is sent, the call still succeeds.
- **Routing only through a structured decision.** The app never parses a department out of free-form model output. With Ollama the decision is the tool call, and no tool call means no mail. With Laya it is a typed `choice` answer that can only be one of the catalog names. Both engines then use the same code to send the mail.
- **The model chooses, the code addresses the mail.** The model sees department names and descriptions, never addresses. The mail's `To` comes from the catalog, `Reply-To` is the sender from the request, and the body is the original message.
- **Department catalog in `data/departments.csv`** (`name`, `email`, `description`). Both engines read their options from this file, so adding a department means adding one row. The file must include an `other` row as the fallback. The descriptions are short keyword lists with Polish terms. Compared with prose descriptions, this raised Laya from 7/14 to 11/14 and Ollama from 12/14 to 14/14 on the tickets above.
- **Cleaned text goes to the model, the original goes in the mail.** Before the message reaches either engine, data URIs and long base64 runs (such as inline images in an email footer) are replaced with `[attachment omitted]`, and everything after a signature delimiter line (`-- ` or `--`) is dropped. One embedded image can be larger than the 2048-token context, and signatures add words that only confuse routing. The forwarded mail keeps the full original message.
- **Ready after `docker compose up -d`.** A one-shot `ollama-pull` container downloads the weights, and the API starts only after it finishes successfully (and after Laya is healthy when it is enabled). Ollama, Laya and SMTP are reachable only inside the Compose network. Only the API and the MailHog UI are published. Image tags and Python dependencies are pinned.
- **Model `qwen2.5:7b`, temperature 0, context 2048.** It supports tool calling in Ollama and runs acceptably on CPU. Engine, model, timeout, context size and log level can be changed in `.env` (see `.env.example`).

## Tests

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```

The tests replace Ollama with a scripted chat model, Laya with a mocked HTTP response, and SMTP with a mock, so they need no running containers.
