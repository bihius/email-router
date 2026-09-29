# email-router

[![CI](https://github.com/bihius/email-router/actions/workflows/ci.yml/badge.svg)](https://github.com/bihius/email-router/actions/workflows/ci.yml)

[Wersja polska](README.pl.md)

PoC of an AI message router. A FastAPI service passes the incoming message to a LangChain agent backed by a local Ollama model. The agent picks a department and calls the `send_email` tool, and MailHog captures the message.

It also contains an experiment: the same decision made by [Laya](https://huggingface.co/convaiinnovations/laya), a local System One decision model, instead of an LLM. On 100 Polish and 100 English test tickets it was over 30× faster than the default agent but far less accurate, so it is off by default (see [Experiment: System One engine](#experiment-system-one-engine-laya) and [`eval/`](eval/README.md)).

## Run

```bash
cp .env.example .env   # optional: only to override defaults
docker compose up -d
```

On first start, `ollama-pull` downloads the model (`qwen3:8b`, about 5.2 GB). The API waits for the download to finish, and its container reports `healthy` once it accepts requests (`docker compose up -d --wait` blocks until then). On CPU, the first request also loads the model into memory; on an Apple M4 it took about 70 s, and later requests, while the model stays loaded, take about 6.5 s each (see [Architecture decisions](#architecture-decisions)).

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

## Experiment: System One engine (Laya)

Routing a ticket is a classification: one choice out of five known options. An LLM does it by generating a tool call token by token. System One models, a new class introduced by TypeSafe AI with [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), answer a typed question such as "which of these options?" in a single forward pass. They return a probability for every option and no text. That fits routing well, so this project tries the approach. Jev is a hosted API, while the brief asks for the messages to be interpreted by a local model, so the experiment uses [Laya](https://huggingface.co/convaiinnovations/laya), an open-source (Apache-2.0) System One model that runs locally and serves a Jev-compatible HTTP API.

The brief does not ask for this, and the default engine does not depend on it. To try it, set one line in `.env`:

```bash
cp .env.example .env
# in .env: ROUTER_ENGINE=laya
docker compose up -d
```

`COMPOSE_PROFILES=${ROUTER_ENGINE}` in `.env` starts the `laya` container. It is built from `laya-serve/Dockerfile` (CPU PyTorch, about 1.5 GB) and downloads the `laya-multilingual` checkpoint (about 650 MB) into a volume. The API waits until the checkpoint is loaded. Ollama still starts, because the brief requires it. The response then reports `"engine": "laya"` and the probability Laya gave the chosen department. In this mode there is no tool calling. Laya's typed answer takes the place of the tool argument, and the same code sends the mail.

**Result: much faster, but accuracy dropped too far.** Measured on 100 tickets, each in Polish and in English with the same meaning ([`eval/`](eval/README.md), CPU, Apple M4, API round trip including SMTP):

| Engine | PL | EN | Median time |
| --- | --- | --- | --- |
| Ollama `qwen3:8b` agent (default) | 91/100 | 93/100 | 6.2–6.5 s |
| Ollama `qwen3:8b` agent, thinking (`OLLAMA_THINK=true`) | 94/100 | 94/100 | 46–51 s |
| Laya `laya-multilingual` | 56/100 | 65/100 | 0.19 s |

Laya is over 30× faster than the default agent and about 250× faster than the agent with thinking, but out of the box it sends 44 of the 100 Polish tickets to the wrong department, so the agent stays the default. Language explains only part of the gap. Laya almost never picks the catch-all `other`, and it often mixes up `help_desk` and `it`, the least clear boundary in the brief's department list. Changing the catalog wording, the checkpoint choice, a probability threshold and a Laya-then-agent cascade did not close the gap ([`eval/README.md`](eval/README.md)). The remaining lever is fine-tuning Laya on labelled tickets from the target domain, which is outside this PoC.

For reference, the same tickets were sent once to TypeSafe's hosted System One model, Jev. It scored 96/100 (PL) and 94/100 (EN), about the same as the qwen3 agent (91/100 and 93/100 by default, 94/100 in both languages with thinking), so on this set accuracy does not separate the two approaches. Speed and confidence do. Jev answers in about 0.25 s, roughly 25× faster than the default agent and 200× faster than the agent with thinking, and its probability reliably marks the answers that may be wrong. The two also mostly miss different tickets: taking Jev's answer when its probability is at least 0.95 and the agent's answer otherwise would score 97/100 (PL) and 95/100 (EN) at about 2 s per ticket on average, because only about a fifth of the tickets would reach the agent. With the agent's thinking on, the same combination scores 97/100 and 96/100 at about 13 s. That is computed from the saved per-ticket results and not implemented. The project does not call Jev, because the brief asks for a local model, and the open System One model that runs locally is not good enough yet. The measurement is documented in [`eval/README.md`](eval/README.md#reference-typesafe-jev-hosted-not-part-of-the-project).

## Architecture decisions

- **One tool with a constrained argument.** The agent has a single `send_email(department)` tool. The argument schema is a `Literal` of the department names from the catalog. If the model picks a name that is not in the catalog, validation rejects it and the agent gives the model the error so it can retry. The agent loop is capped, and each request sends at most one mail. If the model keeps calling the tool after the mail is sent, the call still succeeds.
- **Routing only through a structured decision.** The app never parses a department out of free-form model output. With Ollama the decision is the tool call, and no tool call means no mail. With Laya it is a typed `choice` answer that can only be one of the catalog names. Both engines then use the same code to send the mail.
- **The model chooses, the code addresses the mail.** The model sees department names and descriptions, never addresses. The mail's `To` comes from the catalog, `Reply-To` is the sender from the request, and the body is the original message.
- **Department catalog in `data/departments.csv`** (`name`, `email`, `description`). Both engines read their options from this file, so adding a department means adding one row. The file must include an `other` row as the fallback. The descriptions are short English keyword lists. Of the three wordings compared with Laya in [`eval/`](eval/README.md), this one scored best.
- **Cleaned text goes to the model, the original goes in the mail.** Before the message reaches either engine, data URIs and long base64 runs (such as inline images in an email footer) are replaced with `[attachment omitted]`, and everything after a signature delimiter line (`-- ` or `--`) is dropped. One embedded image can be larger than the 2048-token context, and signatures add words that only confuse routing. The forwarded mail keeps the full original message.
- **Ready after `docker compose up -d`.** A one-shot `ollama-pull` container downloads the weights, and the API starts only after it finishes successfully (and after Laya is healthy when it is enabled). Ollama, Laya and SMTP are reachable only inside the Compose network. Only the API and the MailHog UI are published. Image tags and Python dependencies are pinned.
- **Model `qwen3:8b` without thinking, temperature 0, context 2048.** It supports tool calling in Ollama and routes 91 of 100 Polish and 93 of 100 English test tickets correctly, at about 6.5 s per ticket on CPU. qwen3 thinks before it answers by default in Ollama. With thinking on (`OLLAMA_THINK=true`) it routed 94 of 100 in both languages, but a ticket took about 50 s, and the first request, which also loads the model, took almost 3 minutes. A difference of 1–3 tickets per 100 cannot confirm that thinking helps (see [`eval/README.md`](eval/README.md)), so it is off. The default Ollama timeout of 300 s leaves room for thinking and for slower machines. Engine, model, thinking, timeout, context size and log level can be changed in `.env` (see `.env.example`).

## Tests

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```

The tests replace Ollama with a scripted chat model, Laya with a mocked HTTP response, and SMTP with a mock, so they need no running containers.
