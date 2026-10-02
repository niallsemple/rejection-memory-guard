# Rejection Memory Guard — SPEC (Python MVP)

Stops AI agents re-proposing ideas the user has already rejected, after context
compaction, summarisation, handoffs or restarts.

## Package layout (target)
- `rmg/models.py`      generic `Record` (record_type: rejection|accepted|failed_experiment|open_question|assumption|constraint|decision|trigger), `Fingerprint`, enums
- `rmg/ledger.py`      SQLite persistent ledger (outside conversation context), full status history, never delete
- `rmg/extract.py`     automatic rejection extraction from conversation text
- `rmg/similarity.py`  embeddings (local llama-server `/v1/embeddings`) with TF-IDF fallback
- `rmg/guard.py`       guard pipeline: proposal extraction, matching, ALLOW/WARN/BLOCK/RECONSIDER
- `rmg/inject.py`      compaction injection + handoff injection
- `rmg/analytics.py`   metrics + dashboard print
- `rmg/api.py`         public API functions
- `rmg/cli.py`         CLI (`python -m rmg ...`)
- `rmg/web.py`         small FastAPI or stdlib web UI
- `demo.py`            key acceptance demo
- `tests/`             pytest suite

Tests MUST pass offline: the LLM/embeddings server is optional; when unreachable
(or env `RMG_OFFLINE=1`), fall back to TF-IDF + rules with no network calls.

## 1. Persistent Rejection Ledger
SQLite (default `~/.rmg/ledger.db`, overridable path). Fields:
id, canonical_idea, aliases (list), category, description, rejected_at, rejection_reason,
evidence, constraints_at_time, status (ACTIVE / REOPENED / SUPERSEDED / ARCHIVED),
reconsider_if, superseded_by, times_reproposed, last_reproposal, confidence,
scope (EXACT_IMPLEMENTATION / MECHANISM / ARCHITECTURE / TECHNOLOGY / STRATEGY / VENDOR / ENTIRE_CONCEPT),
rejection_type (HARD / CONDITIONAL / TEMPORARY / SUPERSEDED / FAILED_EXPERIMENT / PREFERENCE),
original_discussion (source text), and full status history (every status change appended
with timestamp + reason; records are never deleted, only archived).

## 2. Rejection Fingerprint
Each rejection stores a fingerprint: OBJECTIVE, MECHANISM, WHY_IT_FAILED,
CONSTRAINT_VIOLATED, CONDITIONS_TO_RECONSIDER, REPLACEMENT. Matching uses the
fingerprint (objective + mechanism + entities + aliases), not just original wording.

## 3. Automatic extraction
Recognise rejection phrases such as: "we already tried that", "didn't work",
"don't suggest that again", "scrap that", "ruled that out", "not profitable",
"too expensive", "latency kills it", "decided against", "failed in testing",
"move on", "that approach is dead", "only reconsider if X" (X -> reconsider_if,
type CONDITIONAL). Mild uncertainty MUST NOT create records: "not sure", "maybe",
"let's think", "another way?".

## 4. Guard pipeline
check(candidate_message):
1. extract proposals from the candidate agent message (sentence/clause split);
2. match each against ACTIVE/REOPENED ledger records using semantic similarity
   (embeddings via local llama-server `/v1/embeddings` or small local model,
   fallback TF-IDF) PLUS rule-based mechanism/objective/entity/alias comparison,
   and an optional LLM judge via the local server (`http://127.0.0.1:8080/v1/chat/completions`);
3. classify ALLOW / WARN / BLOCK / RECONSIDER. Never decide on similarity alone.
Output JSON: `{candidate, decision, matched_rejection, similarity, reason, conditions_changed}`.
- BLOCK increments times_reproposed and sets last_reproposal.
- RECONSIDER produces: "This was previously rejected because X. I am reconsidering it because Y has changed."
- WARN explains how the idea differs from the rejected one.

## 5. False-positive protection
"Use WebSockets with REST polling only as a fallback on disconnect" is WARN or ALLOW,
NOT BLOCK, against rejected "poll an API every second". An implementation-specific
failure (scope EXACT_IMPLEMENTATION) does not blacklist the whole concept.

## 6. Contradiction detection
When the user's new requirement removes the reason for a rejection (e.g. "30 s updates
are now fine" vs rejection reason "latency, needs sub-second"), surface RECONSIDER
with conditions_changed. The user's latest explicit instruction always wins.

## 7. Injection
- Compaction: a short block titled `REJECTED APPROACHES — DO NOT REPROPOSE` containing
  only records relevant to the current task.
- Handoff: a block with sections `TASK:`, `KNOWN REJECTIONS:`, `CURRENT APPROACH:` for sub-agents.

## 8. API and CLI
reject(idea, reason, ...), reopen(id, reason), supersede(id, new_idea), archive(id),
update_conditions(id, conditions), check(candidate), search_rejections(query).
CLI subcommands mirror these plus `stats`, `inject`, `serve`.

## 9. Analytics
rejected_ideas_total, blocked_reproposals, warning_matches, reopened_ideas,
most_repeated_rejection, agent_reproposal_rate, false_positive_rate (from user-marked
false positives), plus a printed dashboard.

## 10. UI
Small web page (FastAPI or stdlib http.server) listing rejected ideas with date, reason,
status. Clicking one shows original discussion, reason, evidence, related rejections,
status (with history), reconsider conditions and reproposal attempts.

## 11. Future: Decision Memory
Generic `Record` with `record_type` so the ledger can later hold accepted ideas, failed
experiments, open questions, assumptions, constraints, decisions, triggers.

## 12. Tests (pytest)
- semantic duplicates: polling paraphrases ("poll the API every second", "hit the REST
  endpoint once a second", "query the endpoint at 1 Hz"); copy-trading paraphrases
  ("copy wallets", "mirror traders", "follow whales", "duplicate trades from top addresses") -> BLOCK
- false positive: WebSocket-with-polling-fallback -> WARN or ALLOW
- reconsider condition: rejection with reconsider_if met by new requirement -> RECONSIDER
- status history is appended, never deleted
- no records from mild uncertainty

## 13. Demo (key acceptance test)
`demo.py`: a conversation rejects an idea; the conversation is compacted away (only a
summary + injection block remain); a fresh agent proposes the same idea in new words
and is BLOCKed with the reason. Also covered by `tests/test_demo.py`.
