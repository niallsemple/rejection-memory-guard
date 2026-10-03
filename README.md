# Rejection Memory Guard (RMG)

Stops AI agents from re-proposing ideas the user has already rejected, after context
compaction, summarisation, handoffs, or restarts.

## What it does

RMG maintains a persistent SQLite ledger of rejected ideas. It provides a "guard"
pipeline that checks new agent proposals against this ledger to prevent
re-proposing dead ends. It also provides injection blocks for context compaction
and sub-agent handoffs.

## Install

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### API

```python
from rmg import api

# Record a rejection
rec = api.reject(
    idea="poll the API every second",
    reason="latency kills it",
    category="data-sync",
    reconsider_if="if sub-second updates are no longer required",
)

# Check a candidate agent message
results = api.check("Let's poll the API every second to keep data fresh.")
for r in results:
    print(r["decision"], r["reason"])

# Search the ledger
for r in api.search_rejections("polling"):
    print(r.id, r.canonical_idea)
```

### CLI

```bash
# Record a rejection
rmg reject "poll the API every second" "latency kills it"

# Check a candidate
rmg check "Let's poll the API every second"

# Search
rmg search "polling"

# Stats
rmg stats

# Generate injection block
rmg inject "sync data from the API"

# Start web UI
rmg serve
```

## Embeddings & Offline Mode

Semantic matching uses a local llama-server at `http://127.0.0.1:8080/v1`
(`/v1/embeddings` for embeddings, `/v1/chat/completions` for the optional LLM judge).

Environment variables:

- `RMG_LLM_BASE`: Base URL of the local LLM server (default `http://127.0.0.1:8080/v1`).
- `RMG_OFFLINE`: Set to `1` to force offline mode (no network calls).
- `RMG_DB`: Path to the SQLite ledger (default `~/.rmg/ledger.db`).

When the server is unreachable or `RMG_OFFLINE=1`, RMG falls back to a pure-Python
TF-IDF similarity plus rule-based mechanism/objective/alias comparison.

## Guard Decision Rules

`check(candidate)` extracts proposals from the candidate message, matches each against
ACTIVE/REOPENED ledger records using semantic similarity **plus** rule-based
fingerprint comparison, and classifies:

- **BLOCK**: Same idea, same scope. Increments `times_reproposed`.
- **WARN**: Similar but meaningfully different (e.g., implementation detail vs concept).
- **RECONSIDER**: A `reconsider_if` condition has been met by the new context.
- **ALLOW**: No meaningful match.

Decisions are never based on similarity alone.

## Injection Blocks

- **Compaction**: A short block titled `REJECTED APPROACHES — DO NOT REPROPOSE`
  containing only records relevant to the current task.
- **Handoff**: A block with `TASK:`, `KNOWN REJECTIONS:`, `CURRENT APPROACH:` sections
  for sub-agents.

## Analytics

`rmg stats` prints a dashboard with:
- rejected_ideas_total
- blocked_reproposals
- warning_matches
- reopened_ideas
- most_repeated_rejection
- agent_reproposal_rate
- false_positive_rate

## Web UI

`rmg serve` starts a small web page listing rejected ideas with date, reason, and
status. Clicking one shows the original discussion, evidence, related rejections,
status history, reconsider conditions, and reproposal attempts.

## Demo

```bash
python demo.py
```

A conversation rejects an idea, the context is compacted away, and a fresh agent
proposes the same idea in new words — it is BLOCKed with the reason.

## Architecture Notes

The ledger stores a generic `Record` with a `record_type` field
(`rejection`, `accepted`, `failed_experiment`, `open_question`, `assumption`,
`constraint`, `decision`, `trigger`). This lays the groundwork for a future
**Decision Memory** layer where the same persistent ledger can hold all kinds of
agent decisions, not just rejections.

## Tests

```bash
pytest -q
```

All tests pass offline (no network required).
