Step 10: a basic web UI using ONLY the Python standard library (http.server, json, html, urllib.parse). Create `rmg/web.py` and `tests/test_web.py`. Keep the reply short; write both files in full. Do NOT edit or mention any other file (the CLI is wired in a later step).

Existing API (read-only): `Ledger(path)`, `ledger.all() -> list[Record]`, `ledger.get(id) -> Record|None`; `record.to_dict()` (JSON-safe dict); Record fields `id, canonical_idea, rejected_at, rejection_reason, evidence, original_discussion, status` (enum, use `.value`), `reconsider_if, times_reproposed, last_reproposal, fingerprint` (has `to_dict()`), `status_history` (entries with `.status`, `.at`, `.reason`), `record.match_text()`; `from rmg.similarity import similarity`.

rmg/web.py:
- `render_index(ledger) -> str`: HTML page with a table: canonical idea as `<a href="/record/<id>">`, rejected date (rejected_at[:10]), reason, status, times re-proposed.
- `render_record(ledger, id) -> str | None`: None if unknown; else a detail page: original discussion, reason, evidence, fingerprint fields, related rejections (top 3 other records by similarity(record.match_text(), other.match_text()), linked), status and full status history, reconsider conditions, times_reproposed and last_reproposal.
- All user text through `html.escape`.
- `make_handler(ledger)` returns a `BaseHTTPRequestHandler` subclass: `GET /` -> render_index; `GET /record/<id>` -> render_record or 404; `GET /api/records` -> JSON list of to_dict(); `GET /api/records/<id>` -> JSON or 404. Silence logging (`log_message` does nothing).
- `serve(ledger, host="127.0.0.1", port=8765)`: `ThreadingHTTPServer((host, port), make_handler(ledger)).serve_forever()`.

tests/test_web.py (autouse monkeypatch RMG_OFFLINE=1; ledger on tmp_path; add Records with `ledger.add(Record(canonical_idea=..., rejection_reason=..., reconsider_if=...))`): render_index contains each idea and "ACTIVE"; render_record contains the reason, "created" (history) and the reconsider_if text; an idea "<script>x</script>" is escaped in render_index; start `ThreadingHTTPServer(("127.0.0.1", 0), make_handler(ledger))` in a daemon thread, fetch `/api/records` with urllib.request, json-parse, assert one entry per record, then `server.shutdown()`.
