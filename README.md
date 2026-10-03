# Rejection Memory Guard (RMG)

**Stop LLM agents from re-proposing ideas you already rejected.**

Long-running agents forget. Once a conversation is compacted, summarised, handed off
to a sub-agent or restarted, the "we tried that, it didn't work, don't suggest it
again" part of the history is usually the first thing to go — and the agent cheerfully
proposes the same dead end again, often in different words.

RMG keeps rejected ideas in a small persistent ledger **outside** the context window and
gives you two hooks:

1. **Inject** — a short `REJECTED APPROACHES — DO NOT REPROPOSE` block (or a sub-agent
   handoff block) to put in the system prompt after compaction.
2. **Check** — run a candidate agent message through a guard before acting on it and get
   `BLOCK`, `WARN`, `RECONSIDER` or `ALLOW`, with the matched rejection and reason.

Pure Python standard library, no required dependencies, works fully offline. An
OpenAI-compatible LLM server (llama.cpp, Ollama, LM Studio, vLLM, OpenAI, ...) is optional.

## How it works

- **Ledger** (`rmg/ledger.py`): SQLite at `~/.rmg/ledger.db` (override with `RMG_DB` or
  `--db`). Each rejection stores the idea, aliases, reason, evidence, scope, rejection type,
  `reconsider_if` condition, a fingerprint (objective / mechanism / why it failed /
  replacement), reproposal counts and a full status history. Records are never deleted,
  only reopened, superseded or archived.
- **Extraction** (`rmg/extract.py`): `api.ingest(messages)` finds rejections in a chat
  transcript from phrases like "we already tried that", "didn't work", "don't suggest that
  again", "scrap that", "decided against", "only reconsider if X". Mild uncertainty
  ("not sure", "maybe") does not create records. If an LLM server is reachable, it is used
  to tidy the extracted idea/reason into short phrases.
- **Guard** (`rmg/guard.py`): splits a candidate message into proposals and compares each
  with active rejections using concept-normalised TF-IDF similarity **plus** rule signals
  (shared concepts, aliases, mechanism overlap, "only as a fallback" wording, scope).
  Decisions are never made on similarity alone:
  - **BLOCK** — same idea; increments `times_reproposed`.
  - **WARN** — similar but meaningfully different (e.g. the rejected thing only as a fallback).
  - **RECONSIDER** — the rejection's `reconsider_if` condition (or the reason it was
    rejected) is relaxed by a requirement you pass in; returns
    "This was previously rejected because X. I am reconsidering it because Y now appears to be true."
  - **ALLOW** — no meaningful match.
- **Injection** (`rmg/inject.py`): picks only the rejections relevant to the current task.
- **Analytics** (`rmg stats`) and a small **web UI** (`rmg serve`) over the ledger.

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/niallsemple/rejection-memory-guard.git
cd rejection-memory-guard
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .                   # or: pip install -e ".[dev]" for pytest
rmg --help
```

### Demo

```bash
RMG_OFFLINE=1 python demo.py
```

A conversation rejects "copy the trades of the most profitable wallets", the conversation
is compacted away (only a summary and the injection block remain), and a fresh agent
proposes "mirror the positions of top-performing whale addresses". It is **BLOCK**ed with
the reason. The demo also shows a **WARN** (WebSockets with REST polling only as a
fallback, against a rejected "poll the API every second") and a **RECONSIDER** (the
"execution latency below 100ms" condition is now met). It uses a throwaway temp ledger.

### Web demo

```bash
python web_demo.py                 # http://127.0.0.1:8765 (next free port if taken)
```

Paste a candidate idea (plus optional "conditions now true", one per line) and the real
guard shows BLOCK / WARN / RECONSIDER / ALLOW with similarity, the matched rejection, the
reason and the raw JSON. The sidebar lists active rejections and the injection block; you
can add rejections or reset. Three example buttons reproduce the demo cases.

It seeds its own throwaway ledger (never your `~/.rmg` ledger) and runs offline by
default. Options: `--host`, `--port`, `--data-dir`. JSON API: `GET /api/state`,
`POST /api/check {"candidate", "conditions"}`,
`POST /api/reject {"idea", "reason", "reconsider_if"}`, `POST /api/reset`.

## Use with your LLM

RMG does not wrap your model. Your agent loop keeps calling whatever LLM it uses; RMG sits
around it:

```python
from rmg import api
from rmg.inject import compaction_block, handoff_block

ledger = api.get_ledger()          # ~/.rmg/ledger.db, or $RMG_DB

# 1. Record rejections: explicitly...
api.reject(
    "poll the API every second",
    "rate limits",
    aliases=["hit the endpoint once a second"],
    reconsider_if="sub-second updates are no longer required",
)
# ...or extracted from the conversation as it happens
api.ingest([
    {"role": "assistant", "content": "I suggest we copy the trades of the most profitable wallets."},
    {"role": "user", "content": "We already tried that, it didn't work. Don't suggest that again. "
                                "Only reconsider if our execution latency drops below 100ms."},
])

# 2. After compaction / on handoff, put the relevant rejections in the system prompt
task = "keep the dashboard data fresh from the API"
system_prompt = BASE_SYSTEM_PROMPT + "\n\n" + compaction_block(ledger, task)
subagent_prompt = handoff_block(ledger, task, current_approach="webhooks")

# 3. Before acting on a candidate, check it
reply = call_my_llm(system_prompt, messages)          # your own LLM call
results = api.check(reply, context={"requirements": user_requirements})  # context optional
for r in results:
    if r["decision"] == "BLOCK":
        # e.g. regenerate with r["reason"] appended as feedback, or refuse the action
        ...
    elif r["decision"] == "RECONSIDER":
        # surface r["reason"] to the user; their latest instruction wins
        ...
```

`api.check` returns one dict per proposal found in the message:
`{candidate, decision, matched_rejection: {id, canonical_idea, rejection_reason} | None,
similarity, reason, conditions_changed}`. Every public function accepts `ledger=` to use a
specific `rmg.ledger.Ledger(path)`. Other API functions: `reopen(id, reason)`,
`supersede(id, new_idea)`, `archive(id)`, `update_conditions(id, text)`,
`search_rejections(query)`, `mark_false_positive(id)`.

For a model-based second opinion, `rmg.guard.Guard(ledger, llm_judge=fn)` accepts a
callable `fn(proposal, record) -> "BLOCK" | "WARN" | "ALLOW" | None` that can confirm or
downgrade the rule-based decision (not wired to any server; bring your own).

### Configuring the LLM endpoint (optional)

The guard works without any model. An OpenAI-compatible server is used for two optional
things: tidying ideas/reasons during `api.ingest` (chat completions), and — only if you
set `RMG_EMBEDDINGS=1` — blending embedding similarity into `check` (`/embeddings`).
Any network error silently falls back to the offline path.

| Variable | Default | Purpose |
|---|---|---|
| `RMG_LLM_BASE_URL` | `http://127.0.0.1:8080/v1` | Base URL of the OpenAI-compatible API (`RMG_LLM_BASE` also accepted) |
| `RMG_LLM_URL` | `$RMG_LLM_BASE_URL/chat/completions` | Full chat-completions URL override |
| `RMG_LLM_MODEL` | `qwen3.8-27b` | Chat model for ingest tidying (llama.cpp single-model servers ignore it) |
| `RMG_EMBED_MODEL` | *(not sent)* | Embedding model name |
| `RMG_LLM_API_KEY` | *(none)* | Sent as `Authorization: Bearer ...` |
| `RMG_EMBEDDINGS` | `0` | `1` = use server embeddings in `check` |
| `RMG_LLM_DISABLE_THINKING` | `1` (`0` for api.openai.com) | Send `chat_template_kwargs: {enable_thinking: false}` (Qwen-style templates) |
| `RMG_OFFLINE` | unset | `1` = no network calls at all |
| `RMG_DB` | `~/.rmg/ledger.db` | Ledger path |

**OpenAI**

```bash
export RMG_LLM_BASE_URL=https://api.openai.com/v1
export RMG_LLM_API_KEY=sk-...
export RMG_LLM_MODEL=gpt-4o-mini
export RMG_EMBED_MODEL=text-embedding-3-small RMG_EMBEDDINGS=1
```

**Ollama** (`ollama serve`, then `ollama pull llama3.2 && ollama pull nomic-embed-text`)

```bash
export RMG_LLM_BASE_URL=http://localhost:11434/v1
export RMG_LLM_MODEL=llama3.2
export RMG_EMBED_MODEL=nomic-embed-text RMG_EMBEDDINGS=1
```

**llama.cpp server** (the default; nothing to set if it runs on port 8080)

```bash
llama-server -m your-model.gguf --port 8080
export RMG_LLM_BASE_URL=http://127.0.0.1:8080/v1
# embeddings need a server started with --embeddings (and an embedding model); chat and
# embeddings share RMG_LLM_BASE_URL, so use a router such as llama-swap if you want both
```

**LM Studio** (start the local server in the Developer tab)

```bash
export RMG_LLM_BASE_URL=http://localhost:1234/v1
export RMG_LLM_MODEL=<model identifier shown in LM Studio>
export RMG_EMBED_MODEL=<loaded embedding model> RMG_EMBEDDINGS=1
```

## CLI

`rmg` (or `python -m rmg`) works on `~/.rmg/ledger.db` unless `--db PATH` or `RMG_DB` is set.

```bash
# record a rejection (alias: rmg add)
rmg reject "poll the API every second" --reason "rate limits" \
    --reconsider-if "sub-second updates are no longer required" --alias "hit the endpoint every second"

# check a candidate message -> JSON list of decisions
rmg check "Let's hit the REST endpoint once a second to keep data fresh."
rmg check "Poll the API every second" --require "sub-second updates are no longer required"   # -> RECONSIDER

rmg list                                   # id, status, date, idea
rmg search "polling"
rmg inject "keep dashboard data fresh from the API"   # compaction block for a system prompt
rmg inject "sync data" --handoff --approach "webhooks"   # sub-agent handoff block
rmg reopen <id> --reason "requirements changed"
rmg supersede <id> "use webhooks instead"
rmg archive <id>
rmg conditions <id> "new reconsider-if text"
rmg stats                                  # analytics dashboard
rmg serve --port 8765                      # web UI over your ledger
```

`reject` also takes `--category`, `--scope` (`entire_concept`), `--rejection-type`
(`hard` / `conditional`), `--evidence`, `--original-discussion` and `--replacement`.

## Tests

```bash
pip install -e ".[dev]"
RMG_OFFLINE=1 python -m pytest -q
```

All tests run offline.

## Project notes

- `SPEC.md` is the original design spec. The ledger stores a generic `Record` with a
  `record_type` (`rejection`, `accepted`, `failed_experiment`, `open_question`,
  `assumption`, `constraint`, `decision`, `trigger`) as groundwork for a broader
  "decision memory"; only rejections are used today.
- The code was built step by step by a local model through [aider](https://aider.chat):
  `steps/` holds the per-step prompts, `run_build.sh` / `launch_detached.sh` the build
  driver (macOS, expects a local llama-server and an aider install) and `.aider.*` its
  config. None of this is needed to use RMG.

## License

MIT — see [LICENSE](LICENSE).
