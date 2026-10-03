Implement the CLI (step 8b of SPEC.md): `rmg/cli.py`, `rmg/__main__.py` and `tests/test_cli.py`. `rmg/api.py` already exists (read-only here); call its functions, passing `ledger=Ledger(args.db)` when `--db` is given.

`rmg/cli.py` uses argparse with a global `--db PATH`. Subcommands:
`reject IDEA --reason R [--reconsider-if X] [--alias A ...]` (prints the new id), `reopen ID --reason R`, `supersede ID NEW_IDEA`, `archive ID`, `conditions ID TEXT`, `check TEXT [--require REQ ...]` (prints a JSON list; --require values become context {"requirements": [...]}), `search QUERY`, `list` (id, status, date, idea per line), `inject TASK [--handoff] [--approach A]` (uses rmg.inject compaction_block / handoff_block), `stats` and `serve [--port 8765]`. For stats/serve, import `rmg.analytics` / `rmg.web` lazily inside the handler and print "not available yet" on ImportError (exit code 0).
`main(argv=None) -> int`. `rmg/__main__.py`: `import sys; from rmg.cli import main; sys.exit(main())`.

Tests in `tests/test_cli.py` (RMG_OFFLINE=1, db under tmp_path): `main(["--db", p, "reject", "poll the api every second", "--reason", "latency"])` returns 0; `main(["--db", p, "check", "hit the REST endpoint once a second"])` prints JSON containing "BLOCK" (capsys); `list` prints the idea; `inject "real-time price updates"` prints "REJECTED APPROACHES".
