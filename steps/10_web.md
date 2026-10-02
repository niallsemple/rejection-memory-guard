Implement step 10 of SPEC.md: a basic web UI using ONLY the Python standard library (http.server, json, html) so no extra deps are needed.

Create `rmg/web.py` and `tests/test_web.py`.
- `make_handler(ledger)` returns a BaseHTTPRequestHandler subclass. Routes:
  - `GET /` : HTML page with a table of rejected ideas (canonical idea as a link to `/record/<id>`, rejected date, reason, status, times re-proposed).
  - `GET /record/<id>` : detail page with original discussion, reason, evidence, fingerprint fields, related rejections (top 3 other records by similarity, linked), status and full status history, reconsider conditions, reproposal attempts (times_reproposed, last_reproposal). 404 if unknown.
  - `GET /api/records` and `GET /api/records/<id>` : JSON.
  - All user text HTML-escaped.
- `render_index(ledger) -> str`, `render_record(ledger, id) -> str|None` (pure functions used by the handler, easy to test).
- `serve(ledger, host="127.0.0.1", port=8765)`. Wire CLI `serve`.

Tests: render_index contains each idea and status; render_record contains reason, history and reconsider_if; escaping of "<script>"; start the server on port 0 in a thread, fetch `/api/records` with urllib and parse JSON, then shut down.
