Implement step 8 of SPEC.md: public API and CLI. Read existing `rmg/*.py` modules.

Create `rmg/api.py`, `rmg/cli.py`, `rmg/__main__.py` (calls cli.main()), `tests/test_api_cli.py`.

`rmg/api.py`: module-level functions taking an optional `ledger=None` kwarg (default: a module-level Ledger from env RMG_DB, created lazily):
- `reject(idea, reason, *, aliases=None, category="", scope=Scope.ENTIRE_CONCEPT, rejection_type=RejectionType.HARD, reconsider_if="", evidence="", original_discussion="", replacement="", ledger=None) -> Record` (builds fingerprint: objective=category or idea, mechanism=idea, why_failed=reason, conditions_to_reconsider=reconsider_if, replacement); logs event "reject".
- `reopen(id, reason)` (status REOPENED, event "reopen"), `supersede(id, new_idea)` (status SUPERSEDED, superseded_by=new_idea), `archive(id)`, `update_conditions(id, conditions)` (sets reconsider_if and fingerprint.conditions_to_reconsider), `check(candidate, context=None) -> list[dict]` (Guard results as dicts), `search_rejections(query, limit=10) -> list[Record]` (by similarity), `ingest(messages)` (extract_rejections then add each, returns list).
- `mark_false_positive(record_id)` logs event "false_positive".

`rmg/cli.py` using argparse, global `--db PATH`. Subcommands: `reject IDEA --reason R [--reconsider-if X] [--alias A ...]`, `reopen ID --reason R`, `supersede ID NEW_IDEA`, `archive ID`, `conditions ID TEXT`, `check TEXT [--require REQ ...]` (prints JSON list), `search QUERY`, `list`, `inject TASK [--handoff] [--approach A]`, `stats`, `serve [--port 8765]` (stats/serve may import modules created later: import them lazily inside the handler and print a clear message on ImportError). `main(argv=None) -> int`.

Tests (RMG_OFFLINE=1, tmp db): API reject/reopen/supersede/archive/update_conditions update status history; check returns BLOCK for paraphrase; search finds the record; CLI `main(["--db", path, "reject", "poll the api every second", "--reason", "latency"])` returns 0 and then `check` prints JSON containing "BLOCK" (use capsys).
