import os
import json
import pytest

os.environ["RMG_OFFLINE"] = "1"

from rmg.cli import main
from rmg.ledger import Ledger

def test_cli_reject_and_check(tmp_path, capsys):
    db_path = str(tmp_path / "test.db")
    
    # Test reject
    ret = main(["--db", db_path, "reject", "poll the api every second", "--reason", "latency"])
    assert ret == 0
    capsys.readouterr() # Clear output from reject
    
    # Test check
    ret = main(["--db", db_path, "check", "hit the REST endpoint once a second"])
    assert ret == 0
    captured = capsys.readouterr()
    output = captured.out
    # The check command prints JSON. We expect it to find the rejection.
    # The GuardResult to_dict likely contains a status or verdict.
    # Based on typical guard implementations, it might say "BLOCK" or similar.
    # Let's verify the JSON structure loosely.
    try:
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) > 0
        # The spec says "prints JSON containing 'BLOCK'"
        assert "BLOCK" in output or "block" in output.lower()
    except json.JSONDecodeError:
        pytest.fail(f"Output was not valid JSON: {output}")

def test_cli_list(tmp_path, capsys):
    db_path = str(tmp_path / "test.db")
    
    # Reject something
    main(["--db", db_path, "reject", "use a monolith", "--reason", "scalability"])
    
    # List
    ret = main(["--db", db_path, "list"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "use a monolith" in captured.out

def test_cli_inject(tmp_path, capsys):
    db_path = str(tmp_path / "test.db")
    
    # Reject something relevant
    main(["--db", db_path, "reject", "poll the api", "--reason", "latency"])
    
    # Inject
    ret = main(["--db", db_path, "inject", "real-time price updates"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "REJECTED APPROACHES" in captured.out

def test_cli_stats(tmp_path, capsys):
    db_path = str(tmp_path / "test.db")
    
    # Reject something
    main(["--db", db_path, "reject", "poll the api every second", "--reason", "latency"])
    
    # Stats
    ret = main(["--db", db_path, "stats"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "rejected_ideas_total" in captured.out


def test_cli_add_alias_and_inject(tmp_path, capsys):
    db_path = str(tmp_path / "test.db")
    ret = main(["--db", db_path, "add", "poll the api every second", "--reason", "rate limits",
                "--reconsider-if", "sub-second updates are no longer required"])
    assert ret == 0
    record_id = capsys.readouterr().out.strip()
    assert record_id

    assert main(["--db", db_path, "list"]) == 0
    assert record_id in capsys.readouterr().out

    assert main(["--db", db_path, "inject", "keep the API data fresh by polling"]) == 0
    out = capsys.readouterr().out
    assert "REJECTED APPROACHES" in out
    assert "poll the api every second" in out

    assert main(["--db", db_path, "inject", "sync data", "--handoff", "--approach", "webhooks"]) == 0
    out = capsys.readouterr().out
    assert "TASK:" in out and "KNOWN REJECTIONS:" in out and "webhooks" in out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "rmg" in capsys.readouterr().out
