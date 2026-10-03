Step 9: analytics. Create `rmg/analytics.py` and `tests/test_analytics.py`. Keep the reply short; write both files in full. Do NOT edit or mention any other file (the CLI is wired in a later step).

Existing API (read-only; do not change): `Ledger.all() -> list[Record]`, `Ledger.events(kind=None) -> list[dict]` (logged by the guard: "block" per blocked proposal, "warn" per warning, "reconsider"; by rmg.api: "check" once per result, "reopen", "false_positive"). Record fields: `record_type` (RecordType enum), `canonical_idea`, `status_history` (list of objects with `.status`), `times_reproposed` (int). Imports: `from rmg.models import RecordType, Status`.

rmg/analytics.py:
- `metrics(ledger) -> dict` with keys: rejected_ideas_total (records with record_type REJECTION, any status), blocked_reproposals (len of events "block"), warning_matches (events "warn"), reopened_ideas (records with any status_history entry whose status is Status.REOPENED), most_repeated_rejection (canonical_idea of the record with the highest times_reproposed if > 0, else None), agent_reproposal_rate (blocked_reproposals / len(events "check"), 0.0 if no checks), false_positive_rate (len(events "false_positive") / max(1, blocked_reproposals + warning_matches)).
- `dashboard(ledger) -> str`: a multi-line text table, one line per metric `f"{name:<26} {value}"`, then "Top rejections by re-proposals:" and up to 5 lines `f"  {r.times_reproposed:>3}  {r.canonical_idea}"`.
- `print_dashboard(ledger)`: print(dashboard(ledger)).

tests/test_analytics.py (autouse monkeypatch RMG_OFFLINE=1; `ledger = Ledger(str(tmp_path / "t.db"))`; `from rmg import api`, always pass `ledger=ledger`):
- `a = api.reject("poll the API every second", "rate limits", ledger=ledger)`; `api.reject("use MongoDB for storage", "ops burden", ledger=ledger)`;
- `api.check("Let's hit the REST endpoint once a second", ledger=ledger)` and `api.check("poll the API every second please", ledger=ledger)` (2 blocks);
- `api.check("Use WebSockets with REST polling only as a fallback on disconnect", ledger=ledger)`;
- `api.reopen(a.id, "new limits", ledger=ledger)`; `api.mark_false_positive(a.id, ledger=ledger)`.
- Assert: rejected_ideas_total == 2, blocked_reproposals == 2, reopened_ideas == 1, most_repeated_rejection == "poll the API every second", 0 < agent_reproposal_rate <= 1, false_positive_rate > 0. Do not assert an exact warning_matches value (>= 0).
- dashboard contains every metric key name.
