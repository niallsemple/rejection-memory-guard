Keep the reply short: use small SEARCH/REPLACE blocks on rmg/guard.py (do NOT rewrite the whole file); write tests/test_guard_fp.py in full.

Step 6a: false-positive protection and scope rule in `rmg/guard.py` `Guard.check_one`. Keep all existing tests passing. Do not touch extract_proposals or the LLM judge code.

1. Fallback rule. Add a module-level tuple `FALLBACK_MARKERS = ("only as a fallback", "as a fallback", "fall back to", "fallback", "on disconnect", "as a backup", "instead of", "rather than")`. Inside the per-record loop, after the BLOCK/WARN decision is computed and before the LLM judge: if `decision == Decision.BLOCK` and the lowercased proposal contains any marker, set `decision = Decision.WARN` and `reason = f"Rejected approach '{record.canonical_idea}' appears only as a fallback/secondary mechanism"`.
2. Scope rule. Right after that: if `record.scope == Scope.EXACT_IMPLEMENTATION` and `decision == Decision.BLOCK` and `sim < 0.7`, set `decision = Decision.WARN` and `reason = f"Similar to rejected implementation '{record.canonical_idea}' (exact-implementation scope, similarity {sim:.2f} < 0.7)"`.
   Add `Scope` to the existing `from rmg.models import ...` line.

tests/test_guard_fp.py must start like this (same fixtures as tests/test_guard_basic.py):
```python
import pytest
from rmg.guard import Guard
from rmg.ledger import Ledger
from rmg.models import Record, RecordType, Status, Decision, Scope

@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

@pytest.fixture
def ledger(tmp_path):
    l = Ledger(str(tmp_path / "t.db"))
    yield l
    l.close()
```
Tests (each adds `Record(record_type=RecordType.REJECTION, canonical_idea=..., rejection_reason=..., status=Status.ACTIVE, ...)` with `ledger.add(...)` then calls `Guard(ledger).check_one(...)`):
- rejected "poll an API every second" (reason "rate limits"); proposal "Use WebSockets with REST polling only as a fallback on disconnect" -> decision in (WARN, ALLOW), never BLOCK.
- rejected "poll the API every second", scope=Scope.EXACT_IMPLEMENTATION; proposal "Let's hit the REST endpoint once a second" -> WARN.
- same EXACT_IMPLEMENTATION record; proposal "poll the API every second using requests library" -> BLOCK (similarity >= 0.7).
- default scope record "poll the API every second"; proposal "Let's hit the REST endpoint once a second" -> still BLOCK.
