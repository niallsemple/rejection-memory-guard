Step 8a: the Python API. Create `rmg/api.py` and `tests/test_api.py`. Keep the reply short; write both files in full. Do not edit any other file.

Existing API you can rely on (do not change these modules):
- `rmg.models`: `Record, Fingerprint, RecordType, Status, Scope, RejectionType` (enums of str). Record fields include `id, canonical_idea, aliases, category, rejection_reason, evidence, original_discussion, status, reconsider_if, superseded_by, scope, rejection_type, fingerprint, status_history` (list; `record.set_status(new_status, reason)` appends an entry), `record.match_text()`. `Fingerprint(objective, mechanism, why_failed, constraint_violated, conditions_to_reconsider, replacement)`.
- `rmg.ledger.Ledger(path=None)`: `add(record) -> Record`, `get(id) -> Record|None`, `update(record)`, `all()`, `active()`, `set_status(id, status, reason)` (updates status + history and saves), `log_event(kind, record_id=None, payload=None)`, `events(kind=None) -> list[dict]`, `close()`.
- `rmg.guard.Guard(ledger)`: `.check(message, context=None) -> list[GuardResult]`; `GuardResult.to_dict()` gives keys candidate, decision (str), matched_rejection, similarity, reason, conditions_changed.
- `rmg.extract.extract_rejections(messages) -> list[Record]` (messages = list of {"role","content"} dicts).
- `rmg.similarity.similarity(a, b) -> float`.

`rmg/api.py`: module-level `_LEDGER = None`; `get_ledger()` lazily creates `Ledger(os.environ.get("RMG_DB"))`; `set_ledger(l)`; helper `_l(ledger)` returns `ledger or get_ledger()`. Functions, each with a `ledger=None` kwarg:
- `reject(idea, reason, *, aliases=None, category="", scope=Scope.ENTIRE_CONCEPT, rejection_type=RejectionType.HARD, reconsider_if="", evidence="", original_discussion="", replacement="", ledger=None) -> Record`: fingerprint objective = category or idea, mechanism = idea, why_failed = reason, conditions_to_reconsider = reconsider_if, replacement = replacement. If reconsider_if and rejection_type == HARD, use RejectionType.CONDITIONAL. Add to ledger, `log_event("reject", rec.id)`, return it.
- `reopen(id, reason, ledger=None)`: set_status REOPENED, event "reopen". `supersede(id, new_idea, ledger=None)`: get, set superseded_by=new_idea, update, then set_status SUPERSEDED, event "supersede". `archive(id, ledger=None)`: set_status ARCHIVED with reason "archived", event "archive". `update_conditions(id, conditions, ledger=None)`: set reconsider_if and fingerprint.conditions_to_reconsider, update.
- `check(candidate, context=None, ledger=None) -> list[dict]`: `[r.to_dict() for r in Guard(l).check(candidate, context)]`, `log_event("check", ...)` once per result.
- `search_rejections(query, limit=10, ledger=None) -> list[Record]`: records from `l.all()` with similarity(query, r.match_text()) > 0.1, sorted descending, top limit.
- `ingest(messages, ledger=None) -> list[Record]`: extract_rejections then `l.add` each; return them.
- `mark_false_positive(record_id, ledger=None)`: log_event("false_positive", record_id).

tests/test_api.py: autouse fixture monkeypatching RMG_OFFLINE=1; fixture `ledger` = `Ledger(str(tmp_path / "t.db"))` (close after yield); always pass `ledger=ledger`. Tests:
- reject("poll the API every second", "rate limits") then reopen -> `ledger.get(id).status == Status.REOPENED` and len(status_history) == 2; supersede -> SUPERSEDED and superseded_by set; archive -> ARCHIVED.
- update_conditions persists (re-read with ledger.get).
- after reject("poll the API every second", "rate limits"), `check("Let's hit the REST endpoint once a second", ledger=ledger)[0]["decision"] == "BLOCK"`.
- search_rejections("poll the API") returns the record.
- ingest([{"role": "assistant", "content": "I suggest we poll the API every second."}, {"role": "user", "content": "We already tried that, didn't work."}]) returns 1 record and ledger.all() has 1.
