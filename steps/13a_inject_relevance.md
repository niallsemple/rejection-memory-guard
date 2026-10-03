Keep the reply short: use small SEARCH/REPLACE blocks on rmg/inject.py and tests/test_inject.py (do NOT rewrite whole files). Do not edit any other file.

Step 13a: fix relevance retrieval and bullet format in `rmg/inject.py`. Bug: with a ledger record "Copy trades of top-performing on-chain wallets" and the task "Working on a Solana trading strategy; several ideas evaluated." the compaction block prints `- (none relevant)`, because the TF-IDF similarity (about 0.12) is under `min_sim=0.15` and no concept is shared. Keep all existing tests passing.

1. Import `tokenize` too: `from rmg.similarity import similarity, concepts, tokenize`.
2. Add a module-level set:
   `GENERIC_TOKENS = {"use", "using", "work", "improv", "idea", "design", "build", "make", "add", "task", "plan", "approach", "strategy", "several", "evaluat", "system", "new", "get", "need"}`
3. `relevant_rejections(ledger, task, limit=8, min_sim=0.10)`: for each `r` in `ledger.active()`: `text = r.match_text()`, `sim = similarity(task, text)`, `shared = concepts(task) & concepts(text)`, `shared_tokens = (set(tokenize(task)) & set(tokenize(text))) - GENERIC_TOKENS`. Keep the record if `sim >= min_sim or shared or shared_tokens`. Score = `sim + 0.2 * len(shared) + 0.1 * len(shared_tokens)`. Return the top `limit` records by score descending.
4. Replace `_bullet(r)` so it returns a multi-line bullet in this exact format (lines joined with "\n", no trailing newline; strip trailing ".!? " from reason, condition and replacement):
   line 1: `f"- {r.canonical_idea} [{r.id}, rejected {r.rejected_at[:10]}]"`
   line 2: `f"  Reason: {reason}"`
   line 3 (only if r.reconsider_if): `f"  Reconsider only if: {condition}"`
   line 4 (only if r.fingerprint.replacement): `f"  Use instead: {replacement}"`
5. `compaction_block` and `handoff_block` keep their structure and both use `relevant_rejections` + `_bullet` (so the handoff block gets the same fix). Empty cases stay `- (none relevant)` and `- none`.

Append these tests to tests/test_inject.py (keep the existing tests unchanged):
```python
def add_wallet(ledger):
    ledger.add(Record(id="copy1", record_type=RecordType.REJECTION, status=Status.ACTIVE,
        canonical_idea="Copy trades of top-performing on-chain wallets",
        rejection_reason="Edge decays before execution.",
        reconsider_if="execution latency drops below 100ms"))

SOLANA_TASKS = ["improve the Solana trading strategy using top wallets",
                "Working on a Solana trading strategy; several ideas evaluated."]

def test_compaction_lists_relevant_wallet_rejection(ledger):
    add_two(ledger)
    add_wallet(ledger)
    for task in SOLANA_TASKS:
        result = compaction_block(ledger, task)
        assert "(none relevant)" not in result
        assert "- Copy trades of top-performing on-chain wallets [copy1, rejected " in result
        assert "\n  Reason: Edge decays before execution\n" in result
        assert result.endswith("  Reconsider only if: execution latency drops below 100ms")
        assert "mongo1" not in result
        assert "poll1" not in result

def test_handoff_lists_relevant_wallet_rejection(ledger):
    add_two(ledger)
    add_wallet(ledger)
    result = handoff_block(ledger, SOLANA_TASKS[1], "momentum signals")
    known = result.split("KNOWN REJECTIONS:\n")[1].split("\nCURRENT APPROACH:")[0]
    assert known.startswith("- Copy trades of top-performing on-chain wallets [copy1")
    assert "  Reason: Edge decays before execution" in known
    assert "  Reconsider only if: execution latency drops below 100ms" in known
    assert "- none" not in known
    assert "mongo1" not in known
```
