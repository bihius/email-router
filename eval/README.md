# Routing evaluation

`tickets.csv` holds 100 tickets, 20 per department. Each ticket is written in Polish and in English with the same meaning, so a gap between the two columns comes from language, not content. Some Polish tickets have no diacritics or casual spelling, as real mail often does. The tickets were written without reusing the catalog keywords.

```bash
docker compose up -d --wait        # ROUTER_ENGINE in .env picks the engine
python eval/run.py pl              # then: python eval/run.py en
```

The runner sends every ticket through the API, so each one really arrives in MailHog. Per-ticket results are written to `results/<engine>-<lang>.csv`. `--tag` adds a label to the file name: the runs with `OLLAMA_THINK=false` in `.env` were saved with `--tag nothink`.

## Results

Catalog as committed (`data/departments.csv`, English keyword lists). Measured on CPU (Apple M4, Docker), time is the API round trip including SMTP. `results/ollama-*.csv` are the `qwen3:8b` runs with thinking (the default), `results/ollama-nothink-*.csv` the runs without it.

| Engine | PL | EN | Median time |
| --- | --- | --- | --- |
| Ollama `qwen3:8b` agent, thinking (default) | **94/100** | **94/100** | 46–51 s |
| Ollama `qwen3:8b` agent, no thinking (`OLLAMA_THINK=false`) | 91/100 | 93/100 | 6.2–6.5 s |
| Laya `laya-multilingual` | 56/100 | 65/100 | 0.19 s |

Correct answers per department (out of 20):

| Department | Thinking PL | Thinking EN | No thinking PL | No thinking EN | Laya PL | Laya EN | Jev PL | Jev EN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kadry | 18 | 18 | 18 | 18 | 16 | 14 | 19 | 19 |
| human_resources | 19 | 19 | 18 | 19 | 12 | 18 | 20 | 20 |
| it | 20 | 20 | 20 | 20 | 19 | 18 | 20 | 19 |
| help_desk | 20 | 19 | 19 | 20 | 9 | 12 | 20 | 20 |
| other | 17 | 18 | 16 | 16 | 0 | 3 | 17 | 16 |

- **Thinking costs a lot of time and buys little accuracy.** qwen3 thinks before it answers (its default in Ollama). With thinking turned off, the agent is 7–8× faster: the median is 6.5 s instead of 51 s in Polish and 6.2 s instead of 46 s in English, and the 90th percentile is 11 s and 8 s instead of 88 s and 73 s. It scores 3 points lower in Polish and 1 in English. Only one of the two modes is right on 9 Polish and 7 English tickets, and a paired test on them (exact McNemar) finds no significant difference (p = 0.51 and 1.0), so on this set the accuracy cost of turning thinking off is not conclusive.
- **Without thinking, `other` suffers most.** It gets 16 of 20 in both languages, and tickets such as office plants or a bike rack go to `help_desk`.
- **`help_desk` against `it` is the least clear boundary.** In the brief's department list, a how-to question about an IT tool ("how do I add an Outlook signature") could go to either. The agent gets 39 of the 40 `help_desk` tickets right in both modes. Laya gets 21 and sends most of the rest to `it`.
- **The agent's misses repeat across languages.** With thinking, 4 of its 6 misses per language are the same tickets in both languages; without thinking, 5 of its 7–9 misses are. Three tickets are missed in all four qwen3 runs: a missing annual tax statement (`kadry`), a question about moving from support to the analytics team (`human_resources`) and the company trip (`other`). These are catalog boundaries rather than language problems, and some are debatable.
- **Language is not the main barrier.** The agent scores about the same in both languages in both modes. Laya loses 9 points on Polish, but most of its gap to the agent is on `other` and in both languages.
- **Laya almost never picks `other`.** The multilingual checkpoint cannot use a catch-all option ("everything else"). The English checkpoint can: it got 17/20 on `other` in the experiments below.
- **Where the thinking time goes.** In the thinking runs the agent made about 2.3 model calls per ticket, usually the `send_email` call and a final reply after the mail is sent, and each call starts with reasoning. The first ticket of the Polish run also loaded the model: 163 s in total, 147 s of it in a single Ollama call. The default `OLLAMA_TIMEOUT` is 300 s to leave room for slower machines. Not measured yet: ending the agent right after `send_email`, which would skip the final reply.
- **One failed request in each mode, both counted as misses.** With thinking, Polish ticket `ot03` got HTTP 500: the Ollama runner process was killed (signal 9) during the agent's final reply, after `send_email` had already forwarded the ticket to the right department (`other`). The mail went out, but the API reported an error. Without thinking, English ticket `hu15` got HTTP 502 after 2.7 s: the model returned no valid `send_email` call, so, as designed, no mail was sent.

## Reference: TypeSafe Jev (hosted, not part of the project)

For comparison, the same 200 tickets were sent once to TypeSafe's hosted System One model, Jev (`jev-1.13.0`). The request was the one the API sends to Laya, with the same question and catalog, because Laya serves a Jev-compatible protocol. The project does not call Jev and needs no API key. The brief asks for a local model, so this is a one-off reference measurement, and `results/jev-*.csv` holds its per-ticket output.

| Engine | PL | EN | Median time |
| --- | --- | --- | --- |
| Jev `jev-1.13.0` (hosted API) | **96/100** | **94/100** | 0.25 s (API call only) |

- **About as accurate as the qwen3 agent.** 96/100 and 94/100, against the agent's 94/100 in both languages with thinking and 91/100 and 93/100 without it. On this set a capable local LLM agent and a System One model decide about equally well. Most of Jev's misses are debatable too (a broken elevator to `it`, a bike rack question to `help_desk`).
- **Much faster.** Jev answers in about a quarter of a second: about 25× faster than the agent without thinking and about 200× faster than with it. Some of that is hosted hardware against a laptop CPU, but Laya, the same approach on the same CPU, also answers in 0.19 s. A System One model picks an option directly and returns its probability, while the agent generates the tool call token by token, after its reasoning when thinking is on, in two or more model calls per ticket.
- **Its probabilities are informative, unlike Laya's.** The 158 answers with a probability of 0.95 or more (about 80% of tickets) were all correct, and every miss had a probability of at most 0.82.
- **Together they beat both.** Jev and the agent mostly miss different tickets: only 2 of the thinking agent's 6 misses per language are also Jev misses, and only 1 of the 7–9 misses without thinking. Taking Jev's answer when its probability is at least 0.95 and the agent's answer otherwise gives 97/100 (PL) and 96/100 (EN) with thinking, at about 13 s per ticket on average instead of 50–56 s, and 97/100 and 95/100 without it, at about 2 s instead of 6.6–7.9 s. About four in five tickets are then answered by Jev alone, in a quarter of a second. These numbers are computed from the per-ticket files, not from a separate run, and the threshold was chosen on this same set, so treat them as slightly optimistic.
- **Why it is not the default.** It is a hosted model, and the brief asks for a local one. The local open model that follows the same approach (Laya) is not yet accurate enough without fine-tuning, so the qwen3 agent stays the default. The takeaway: a System One model does not make clearly better routing decisions than a capable LLM agent, but it makes them one to two orders of magnitude faster and knows when it is unsure, which makes it a good first stage in front of the agent.

## What was tried to improve Laya

Laya results come from calling the Laya container directly with the same question the API sends. The catalog variants were compared on this same set, so treat the winning variant's score as slightly optimistic.

Per-ticket files in `results/` exist only for the committed configuration (the bold row); the other rows are summary measurements and no raw output was kept for them. `n/a` marks a variant that does not apply, and `≤` a parameter sweep in which no value helped.

| Change | Laya PL | Laya EN |
| --- | --- | --- |
| Keyword lists with Polish terms (previous catalog) | 53 | 53 |
| **Keyword lists, English only (committed)** | **56** | **65** |
| Rule plus keywords ("something is broken..." / "nothing is broken...") | 47 | 46 |
| English checkpoint for English text (English-only catalog) | n/a | 69 |
| Laya picks the checkpoint by language (`model="auto"`) | 56 | 69 |
| Route to `other` when Laya's probability is low (any threshold) | ≤56 | ≤66 |

- **Descriptions:** Laya works best with short English noun phrases, like the examples in its documentation. Mixing in Polish terms or full sentences made it worse.
- **Checkpoint choice:** automatic routing sent 15 of the 100 Polish tickets to the English checkpoint, even ones with diacritics. It gains 4 points on English only, and a second checkpoint doubles the memory, so the API keeps forcing `laya-multilingual`.
- **Probabilities:** they carry little signal. Above 0.95 Laya is right about 75% of the time, below 0.5 about half the time. A threshold that falls back to `other` does not help.
- **Laya first, the agent when unsure:** escalating the least confident half of the tickets to the qwen3 agent (with thinking) gives 77/100 (PL) and 79/100 (EN). Matching the agent alone (94) requires escalating 97% of the Polish and 82% of the English tickets, so the cascade trades accuracy for speed roughly linearly and has no sweet spot. The same cascade works with Jev (see above), because Jev's probabilities do separate right answers from wrong ones.

The remaining lever is the one Laya's authors document: fine-tuning on labelled decisions from the target domain (on their benchmark, 0.36 zero-shot to 0.77 fine-tuned). That needs a few hundred to a few thousand labelled tickets. These 100 are the test set, not training data. Training data could be generated by having the Ollama agent label synthetic tickets, with the fine-tuning run on a GPU using the authors' notebook. That is outside this PoC.
