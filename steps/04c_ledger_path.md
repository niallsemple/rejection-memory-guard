Fix a bug in `rmg/ledger.py`: the default path `os.path.join("~", ".rmg", "ledger.db")` is never expanded and creates a literal "~" folder. Apply `os.path.expanduser` to the default and to the `RMG_DB` value.

Add to `tests/test_ledger.py`: with RMG_DB unset (monkeypatch HOME to tmp_path), Ledger() creates tmp_path/.rmg/ledger.db and no literal "~" directory exists in the cwd.
