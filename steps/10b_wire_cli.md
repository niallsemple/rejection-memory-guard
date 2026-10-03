Keep the reply short: use small SEARCH/REPLACE blocks on rmg/cli.py and tests/test_cli.py (do NOT rewrite the whole files). Do not edit any other file.

Step 10b: wire the CLI `stats` and `serve` subcommands, which are currently placeholders that only `pass`. Existing API (do not change): `rmg.analytics.print_dashboard(ledger)` prints the metrics dashboard; `rmg.web.serve(ledger, host="127.0.0.1", port=8765)` runs the web UI until interrupted; `api.get_ledger()` returns the default ledger.

In `rmg/cli.py`:
1. Add `p_serve.add_argument("--host", default="127.0.0.1")` next to the existing `--port` argument.
2. In the `elif args.command == "stats":` branch replace the try body (the `import rmg.analytics`, comments and `pass`) with:
   `from rmg.analytics import print_dashboard` and `print_dashboard(ledger or api.get_ledger())`. Keep the `except ImportError: print("not available yet")`.
3. In the `elif args.command == "serve":` branch replace the try body with:
   `from rmg.web import serve` then `print(f"Serving on http://{args.host}:{args.port}")` then `serve(ledger or api.get_ledger(), host=args.host, port=args.port)`. Keep the ImportError handler.

Append one test to tests/test_cli.py: with a db under tmp_path, `main(["--db", p, "reject", "poll the api every second", "--reason", "latency"])`, then `main(["--db", p, "stats"]) == 0` and the captured stdout (capsys) contains "rejected_ideas_total".
