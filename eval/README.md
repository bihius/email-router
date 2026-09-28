# Routing evaluation

`tickets.csv` holds 100 tickets, 20 per department. Each ticket is written in Polish and in English with the same meaning, so a gap between the two columns comes from language, not content. Some Polish tickets have no diacritics or casual spelling, as real mail often does. The tickets were written without reusing the catalog keywords.

```bash
docker compose up -d --wait        # ROUTER_ENGINE in .env picks the engine
python eval/run.py pl              # then: python eval/run.py en
```

The runner sends every ticket through the API, so each one really arrives in MailHog. Per-ticket results are written to `results/<engine>-<lang>.csv`.

## Results

Catalog as committed (`data/departments.csv`, English keyword lists). Measured on CPU (Apple M4, Docker), time is the API round trip including SMTP.

| Engine | PL | EN | Median time |
| --- | --- | --- | --- |
| Ollama `qwen2.5:7b` agent (default) | **85/100** | **84/100** | 5.4–6.4 s |
| Laya `laya-multilingual` | 56/100 | 65/100 | 0.19 s |

Correct answers per department (out of 20):

| Department | Ollama PL | Ollama EN | Laya PL | Laya EN | Jev PL | Jev EN |
| --- | --- | --- | --- | --- | --- | --- |
| kadry | 20 | 19 | 16 | 14 | 19 | 19 |
| human_resources | 18 | 18 | 12 | 18 | 20 | 20 |
| it | 20 | 19 | 19 | 18 | 20 | 19 |
| help_desk | 11 | 9 | 9 | 12 | 20 | 20 |
| other | 16 | 19 | 0 | 3 | 17 | 16 |

- **Language is not the main barrier.** Ollama scores the same in both languages. Laya loses 9 points on Polish, but most of its gap to Ollama is on `other` and in both languages.
- **Laya almost never picks `other`.** The multilingual checkpoint cannot use a catch-all option ("everything else"). The English checkpoint can: it got 17/20 on `other` in the experiments below.
- **Both local engines confuse `help_desk` with `it`.** How-to questions about IT tools ("how do I add an Outlook signature") are the least clear boundary in the brief's department list.

## Reference: TypeSafe Jev (hosted, not part of the project)

For comparison, the same 200 tickets were sent once to TypeSafe's hosted System One model, Jev (`jev-1.13.0`). The request was the one the API sends to Laya, with the same question and catalog, because Laya serves a Jev-compatible protocol. The project does not call Jev and needs no API key. The brief asks for a local model, so this is a one-off reference measurement, and `results/jev-*.csv` holds its per-ticket output.

| Engine | PL | EN | Median time |
| --- | --- | --- | --- |
| Jev `jev-1.13.0` (hosted API) | **96/100** | **94/100** | 0.25 s (API call only) |

- **The System One approach works.** Jev was the most accurate engine here and needed about a quarter of a second per ticket. It got every `help_desk` ticket right and scored the same in both languages. Most of its misses are debatable (a broken elevator to `it`, a bike rack question to `help_desk`).
- **Its probabilities are informative, unlike Laya's.** The 158 answers with a probability of 0.95 or more (about 80% of tickets) were all correct, and every miss had a probability below 0.82. That would allow confidence-gated routing: act on confident answers and send the rest to Ollama or a person.
- **Why it is not the default.** It is a hosted model, and the brief asks for a local one. The local open model that follows the same approach (Laya) is not yet accurate enough without fine-tuning, so Ollama stays the default.

## What was tried to improve Laya

Laya results come from calling the Laya container directly with the same question the API sends. Ollama runs go through the API. The catalog variants were compared on this same set, so treat the winning variant's score as slightly optimistic.

Per-ticket files in `results/` exist only for the committed configuration (the bold row); the other rows are summary measurements and no raw output was kept for them. Missing cells say why a run does not appear: `not run` when a variant had already lost on the other legs, `n/a` when the variant does not apply, `≤` when a sweep of the parameter did not help, and blank when there was nothing to run for that engine.

| Change | Laya PL | Laya EN | Ollama PL | Ollama EN |
| --- | --- | --- | --- | --- |
| Keyword lists with Polish terms (previous catalog) | 53 | 53 | 83 | 84 |
| **Keyword lists, English only (committed)** | **56** | **65** | **85** | **84** |
| Rule plus keywords ("something is broken..." / "nothing is broken...") | 47 | 46 | 80 | not run |
| English checkpoint for English text (English-only catalog) | n/a | 69 | | |
| Laya picks the checkpoint by language (`model="auto"`) | 56 | 69 | | |
| Route to `other` when Laya's probability is low (any threshold) | ≤56 | ≤66 | | |

- **Descriptions:** Laya works best with short English noun phrases, like the examples in its documentation. Mixing in Polish terms or full sentences made it worse, and neither helped Ollama.
- **Checkpoint choice:** automatic routing sent 15 of the 100 Polish tickets to the English checkpoint, even ones with diacritics. It gains 4 points on English only, and a second checkpoint doubles the memory, so the API keeps forcing `laya-multilingual`.
- **Probabilities:** they carry little signal. Above 0.95 Laya is right about 75% of the time, below 0.5 about half the time. A threshold that falls back to `other` does not help.
- **Laya first, Ollama when unsure:** escalating the least confident half of the Polish tickets to Ollama gives 74/100. Matching Ollama alone (85) requires escalating about 80%, so the cascade trades accuracy for speed roughly linearly and has no sweet spot.

The remaining lever is the one Laya's authors document: fine-tuning on labelled decisions from the target domain (on their benchmark, 0.36 zero-shot to 0.77 fine-tuned). That needs a few hundred to a few thousand labelled tickets. These 100 are the test set, not training data. Training data could be generated by having the Ollama agent label synthetic tickets, with the fine-tuning run on a GPU using the authors' notebook. That is outside this PoC.
