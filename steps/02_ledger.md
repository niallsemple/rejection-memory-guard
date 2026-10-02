Implement step 2 of SPEC.md: the persistent SQLite ledger. Models already exist in `rmg/models.py` (read it, do not change its public API).

Create `rmg/ledger.py` and `tests/test_ledger.py`.

`class Ledger`:
- `__init__(self, path=None)`: path defaults to env `RMG_DB` or `~/.rmg/ledger.db`; create parent dir; `":memory:"` allowed. Use sqlite3 with one table `records(id TEXT PRIMARY KEY, record_type TEXT, status TEXT, data TEXT)` where data is `Record.to_json()`; a second table `events(id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, kind TEXT, record_id TEXT, payload TEXT)` for analytics events.
- `add(record) -> Record`, `get(id) -> Record|None`, `update(record)`, `all(record_type=None, statuses=None) -> list[Record]`, `active()` (status ACTIVE or REOPENED, record_type REJECTION).
- `set_status(id, status, reason)` uses Record.set_status and saves.
- `increment_reproposal(id)`: times_reproposed += 1, last_reproposal = now ISO.
- `log_event(kind, record_id=None, payload=None)` and `events(kind=None) -> list[dict]`.
- There is NO delete method. Records are never deleted.
- `close()`, and context manager support.

`tests/test_ledger.py` (use `tmp_path` fixture for a db file): add/get round trip; persistence across two Ledger instances on the same file; set_status REOPENED then ARCHIVED keeps 3 history entries in order; `active()` excludes ARCHIVED/SUPERSEDED; increment_reproposal; events logging; assert `not hasattr(Ledger, "delete")`.
