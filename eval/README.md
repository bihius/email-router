# Routing evaluation

`tickets.csv` holds 100 tickets, 20 per department. Each ticket is written in Polish and in English with the same meaning, so a gap between the two columns comes from language, not content. Some Polish tickets have no diacritics or casual spelling, as real mail often does. The tickets were written without reusing the catalog keywords.

```bash
docker compose up -d --wait        # ROUTER_ENGINE in .env picks the engine
python eval/run.py pl              # then: python eval/run.py en
```

The runner sends every ticket through the API, so each one really arrives in MailHog. Per-ticket results are written to `results/<engine>-<lang>.csv`.

## Results

Catalog as committed (`data/departments.csv`, English keyword lists). Measured on CPU (Apple M4, Docker), time is the API round trip including SMTP. Result files are named after the engine, not the model: `results/ollama-*.csv` are the `qwen3:8b` runs, and the `qwen2.5:7b` runs were moved to `results/qwen2.5-7b/`.

| Engine | PL | EN | Median time |
| --- | --- | --- | --- |
| Ollama `qwen3:8b` agent (default) | **94/100** | **94/100** | 46–51 s |
| Ollama `qwen2.5:7b` agent (previous default) | 85/100 | 84/100 | 5.4–6.4 s |
| Laya `laya-multilingual` | 56/100 | 65/100 | 0.19 s |

Correct answers per department (out of 20):

| Department | qwen3 PL | qwen3 EN | qwen2.5 PL | qwen2.5 EN | Laya PL | Laya EN | Jev PL | Jev EN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kadry | 18 | 18 | 20 | 19 | 16 | 14 | 19 | 19 |
| human_resources | 19 | 19 | 18 | 18 | 12 | 18 | 20 | 20 |
| it | 20 | 20 | 20 | 19 | 19 | 18 | 20 | 19 |
| help_desk | 20 | 19 | 11 | 9 | 9 | 12 | 20 | 20 |
| other | 17 | 18 | 16 | 19 | 0 | 3 | 17 | 16 |

- **qwen3 gains mostly on `help_desk`.** How-to questions about IT tools ("how do I add an Outlook signature") are the least clear boundary in the brief's department list, and qwen2.5 often sent them to `it`. qwen3 gets 39 of the 40 `help_desk` tickets right (qwen2.5: 20). Overall it fixes 12 Polish and 13 English tickets and newly misses 3 in each language.
- **Its misses repeat across languages.** Four of its six misses per language are the same tickets, routed the same way in both: a missing annual tax statement (`kadry` to `other`), a surname change (`kadry` to `human_resources`), a move to another team (`human_resources` to `other`) and the company trip (`other` to `human_resources`). These are catalog boundaries rather than language problems, and some are debatable.
- **Language is not the main barrier.** Both Ollama models score the same in both languages. Laya loses 9 points on Polish, but most of its gap to the agent is on `other` and in both languages.
- **Laya almost never picks `other`.** The multilingual checkpoint cannot use a catch-all option ("everything else"). The English checkpoint can: it got 17/20 on `other` in the experiments below.
- **qwen3 is about 8× slower than qwen2.5.** It thinks before it answers (its default in Ollama), and the agent makes about 2.3 model calls per ticket, usually the `send_email` call and a final reply after the mail is sent. The 90th percentile is 88 s (PL) and 73 s (EN). The first ticket of the Polish run also loaded the model: 163 s in total, 147 s of it in a single Ollama call. That is too close to the old 180 s limit for a slower machine, so the default `OLLAMA_TIMEOUT` is now 300 s. Not measured yet: qwen3 with thinking turned off, and ending the agent right after `send_email`.
- **One HTTP 500.** Polish ticket `ot03` counts as a miss. The Ollama runner process was killed (signal 9) during the agent's follow-up call, after `send_email` had already forwarded the ticket to the right department (`other`). The mail went out, but the API reported an error.

## Reference: TypeSafe Jev (hosted, not part of the project)

For comparison, the same 200 tickets were sent once to TypeSafe's hosted System One model, Jev (`jev-1.13.0`). The request was the one the API sends to Laya, with the same question and catalog, because Laya serves a Jev-compatible protocol. The project does not call Jev and needs no API key. The brief asks for a local model, so this is a one-off reference measurement, and `results/jev-*.csv` holds its per-ticket output.

| Engine | PL | EN | Median time |
| --- | --- | --- | --- |
| Jev `jev-1.13.0` (hosted API) | **96/100** | **94/100** | 0.25 s (API call only) |

- **About as accurate as the qwen3 agent.** Next to qwen2.5, Jev looked clearly better (96/94 against 85/84). qwen3 closes most of that gap (94/94), so on this set a capable local LLM agent and a System One model decide about equally well. Most of Jev's misses are debatable too (a broken elevator to `it`, a bike rack question to `help_desk`).
- **About 200× faster.** Jev answers in about a quarter of a second, the qwen3 agent in 46–51 s. Some of that is hosted hardware against a laptop CPU, but Laya, the same approach on the same CPU, also answers in 0.19 s. A System One model picks an option directly and returns its probability, while the agent writes out its reasoning and the tool call token by token, in two or more model calls per ticket.
- **Its probabilities are informative, unlike Laya's.** The 158 answers with a probability of 0.95 or more (about 80% of tickets) were all correct, and every miss had a probability of at most 0.82.
- **Together they beat both.** Only 2 of the agent's 6 misses per language are also Jev misses. Taking Jev's answer when its probability is at least 0.95 and the qwen3 agent's answer otherwise gives 97/100 (PL) and 96/100 (EN). About four in five tickets are then answered in a quarter of a second, and the average time per ticket drops from 50–56 s to about 13 s. With the faster qwen2.5 as the fallback, the same cascade scores 96/100 in both languages at under 2 s on average. These numbers are computed from the per-ticket files, not from a separate run, and the threshold was chosen on this same set, so treat them as slightly optimistic.
- **Why it is not the default.** It is a hosted model, and the brief asks for a local one. The local open model that follows the same approach (Laya) is not yet accurate enough without fine-tuning, so the qwen3 agent stays the default. The takeaway: a System One model does not make clearly better routing decisions than a capable LLM agent, but it makes them two orders of magnitude faster and knows when it is unsure, which makes it a good first stage in front of the agent.

## What was tried to improve Laya

Laya results come from calling the Laya container directly with the same question the API sends. Ollama runs go through the API. The catalog variants were compared on this same set, so treat the winning variant's score as slightly optimistic. The two right-hand columns are the previous default model, `qwen2.5:7b`; the variants were not re-run with `qwen3:8b`.

Per-ticket files in `results/` exist only for the committed configuration (the bold row); the other rows are summary measurements and no raw output was kept for them. Missing cells say why a run does not appear: `not run` when a variant had already lost on the other legs, `n/a` when the variant does not apply, `≤` when a sweep of the parameter did not help, and blank when there was nothing to run for that engine.

| Change | Laya PL | Laya EN | qwen2.5 PL | qwen2.5 EN |
| --- | --- | --- | --- | --- |
| Keyword lists with Polish terms (previous catalog) | 53 | 53 | 83 | 84 |
| **Keyword lists, English only (committed)** | **56** | **65** | **85** | **84** |
| Rule plus keywords ("something is broken..." / "nothing is broken...") | 47 | 46 | 80 | not run |
| English checkpoint for English text (English-only catalog) | n/a | 69 | | |
| Laya picks the checkpoint by language (`model="auto"`) | 56 | 69 | | |
| Route to `other` when Laya's probability is low (any threshold) | ≤56 | ≤66 | | |

- **Descriptions:** Laya works best with short English noun phrases, like the examples in its documentation. Mixing in Polish terms or full sentences made it worse, and neither helped qwen2.5.
- **Checkpoint choice:** automatic routing sent 15 of the 100 Polish tickets to the English checkpoint, even ones with diacritics. It gains 4 points on English only, and a second checkpoint doubles the memory, so the API keeps forcing `laya-multilingual`.
- **Probabilities:** they carry little signal. Above 0.95 Laya is right about 75% of the time, below 0.5 about half the time. A threshold that falls back to `other` does not help.
- **Laya first, the agent when unsure:** escalating the least confident half of the tickets to the qwen3 agent gives 77/100 (PL) and 79/100 (EN). Matching the agent alone (94) requires escalating 97% of the Polish and 82% of the English tickets, so the cascade trades accuracy for speed roughly linearly and has no sweet spot. The same cascade works with Jev (see above), because Jev's probabilities do separate right answers from wrong ones.

The remaining lever is the one Laya's authors document: fine-tuning on labelled decisions from the target domain (on their benchmark, 0.36 zero-shot to 0.77 fine-tuned). That needs a few hundred to a few thousand labelled tickets. These 100 are the test set, not training data. Training data could be generated by having the Ollama agent label synthetic tickets, with the fine-tuning run on a GPU using the authors' notebook. That is outside this PoC.
