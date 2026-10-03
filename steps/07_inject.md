Step 7: context injection. Create `rmg/inject.py` and `tests/test_inject.py`. Keep the reply short; write both files in full. Do not edit any other file.

Existing API you can rely on (do not re-read or change these modules):
- `from rmg.models import Record, RecordType, Status, Scope` ; Record fields: `id, canonical_idea, rejected_at` (ISO string, first 10 chars are YYYY-MM-DD), `rejection_reason, reconsider_if, fingerprint` (a `Fingerprint` with `.replacement` str), method `record.match_text() -> str`.
- `from rmg.ledger import Ledger` ; `Ledger(path)`, `ledger.add(record)`, `ledger.active() -> list[Record]` (ACTIVE/REOPENED rejections), `ledger.close()`.
- `from rmg.similarity import similarity, concepts` ; `similarity(a, b) -> float` in [0,1] (lexical TF-IDF offline), `concepts(text) -> set[str]`.

rmg/inject.py:
- `relevant_rejections(ledger, task, limit=8, min_sim=0.15) -> list[Record]`: for each `r` in `ledger.active()`: `sim = similarity(task, r.match_text())`, `shared = concepts(task) & concepts(r.match_text())`; keep if `sim >= min_sim or shared`; score = `sim + 0.2 * len(shared)`; return the top `limit` by score descending.
- `_bullet(r) -> str`: `f"- [{r.id}] {r.canonical_idea} — rejected {r.rejected_at[:10]}: {r.rejection_reason}"`, plus `f" (reconsider only if: {r.reconsider_if})"` if reconsider_if, plus `f" -> use instead: {r.fingerprint.replacement}"` if replacement.
- `compaction_block(ledger, task, limit=8) -> str`: `"REJECTED APPROACHES — DO NOT REPROPOSE"` then one bullet per relevant record, joined by "\n"; if none, the header then `- (none relevant)`.
- `handoff_block(ledger, task, current_approach="") -> str`: `"TASK:\n" + task + "\nKNOWN REJECTIONS:\n" + (bullets joined by "\n" or "- none") + "\nCURRENT APPROACH:\n" + (current_approach or "(not decided)")`.

tests/test_inject.py must use exactly this setup and data (similarity is lexical, so the relevant record must share words with the task):
```python
import pytest
from rmg.ledger import Ledger
from rmg.models import Record, RecordType, Status
from rmg.inject import relevant_rejections, compaction_block, handoff_block

@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

@pytest.fixture
def ledger(tmp_path):
    l = Ledger(str(tmp_path / "t.db"))
    yield l
    l.close()

def add_two(ledger):
    ledger.add(Record(id="poll1", record_type=RecordType.REJECTION, status=Status.ACTIVE,
        canonical_idea="poll the price API every second for real-time price updates",
        rejection_reason="rate limits"))
    ledger.add(Record(id="mongo1", record_type=RecordType.REJECTION, status=Status.ACTIVE,
        canonical_idea="use MongoDB for storage", rejection_reason="ops burden"))
```
Tests:
- `add_two`; `compaction_block(ledger, "design real-time price updates")` starts with the header line, contains "poll1" and "rate limits", does not contain "mongo1".
- `add_two`; `relevant_rejections(ledger, "design real-time price updates")` ids == ["poll1"].
- `add_two`; `handoff_block(ledger, "design real-time price updates", "use websockets")`: the indexes of "TASK:", "KNOWN REJECTIONS:", "CURRENT APPROACH:" in the text are increasing; contains "poll1" and "use websockets".
- empty ledger: compaction_block contains "- (none relevant)"; handoff_block contains "- none" and "(not decided)".
