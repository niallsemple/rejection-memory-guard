Implement step 11 of SPEC.md: the key acceptance demo. Read `rmg/api.py`, `rmg/inject.py`, `rmg/guard.py`, `rmg/extract.py`.

Create `demo.py` (repo root) and `tests/test_demo.py`.

`demo.py` defines `run_demo(db_path=None, verbose=True) -> dict` and a `__main__` block:
1. Session 1 conversation (list of role/content messages): assistant suggests "I suggest we copy the trades of the most profitable wallets on-chain."; user replies "We already tried that, it didn't work — the edge decays before we can execute. Don't suggest that again. Only reconsider if our execution latency drops below 100ms."
2. `api.ingest(conversation)` stores the rejection (assert at least one record).
3. Compaction: the conversation is discarded; only a summary string ("Working on a Solana trading strategy; several ideas evaluated.") plus `inject.compaction_block(ledger, task)` remain. Print both.
4. A fresh agent (no access to the conversation) proposes, in new words: "How about we mirror the positions of top-performing whale addresses?"
5. `api.check(proposal)` -> decision must be BLOCK, and the reason must include the original rejection reason. Print the JSON result.
6. Return {"injection": ..., "summary": ..., "result": <first result dict>, "record_id": ...}.
Make sure `api.ingest` produces a record whose match text covers copy trading (if extraction alone is not enough, add the idea's aliases in ingest via `similarity.concepts`).

`tests/test_demo.py` (RMG_OFFLINE=1, tmp_path db): result decision == "BLOCK"; reason mentions "edge decays"; injection contains "REJECTED APPROACHES — DO NOT REPROPOSE"; the original conversation text "copy the trades" is NOT required for the check (the guard only uses the ledger).
