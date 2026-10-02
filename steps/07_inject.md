Implement step 7 of SPEC.md: context injection. Read `rmg/models.py`, `rmg/ledger.py`, `rmg/similarity.py`.

Create `rmg/inject.py` and `tests/test_inject.py`.
- `relevant_rejections(ledger, task, limit=8, min_sim=0.15) -> list[Record]`: ACTIVE/REOPENED rejections ranked by similarity(task, record.match_text()) plus concept overlap; drop those below min_sim unless they share a concept with the task.
- `compaction_block(ledger, task, limit=8) -> str`: starts with the line `REJECTED APPROACHES — DO NOT REPROPOSE`, then one bullet per relevant record: `- [<id>] <canonical_idea> — rejected <YYYY-MM-DD>: <rejection_reason>` and, if reconsider_if, ` (reconsider only if: <reconsider_if>)`, and if replacement, ` -> use instead: <replacement>`. If none: the header plus `- (none relevant)`. Keep it short (no other records).
- `handoff_block(ledger, task, current_approach="") -> str`: sections `TASK:\n<task>`, `KNOWN REJECTIONS:\n<bullets as above or "- none">`, `CURRENT APPROACH:\n<current_approach or "(not decided)">`.

Tests: with two unrelated rejections (polling the API; using MongoDB for storage) and task "design real-time price updates", compaction block contains the polling rejection, not MongoDB; handoff block has the three headers in order; empty ledger gives "(none relevant)".
