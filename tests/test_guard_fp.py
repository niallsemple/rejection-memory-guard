import pytest
from rmg.guard import Guard
from rmg.ledger import Ledger
from rmg.models import Record, RecordType, Status, Decision, Scope

@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

@pytest.fixture
def ledger(tmp_path):
    l = Ledger(str(tmp_path / "t.db"))
    yield l
    l.close()

def test_fallback_marker_prevents_block(ledger):
    rec = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll an API every second",
        rejection_reason="rate limits",
        status=Status.ACTIVE
    )
    ledger.add(rec)
    g = Guard(ledger)
    result = g.check_one("Use WebSockets with REST polling only as a fallback on disconnect")
    assert result.decision in (Decision.WARN, Decision.ALLOW)
    assert result.decision != Decision.BLOCK

def test_exact_scope_low_sim_warns(ledger):
    rec = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll the API every second",
        rejection_reason="rate limits",
        status=Status.ACTIVE,
        scope=Scope.EXACT_IMPLEMENTATION
    )
    ledger.add(rec)
    g = Guard(ledger)
    result = g.check_one("Let's hit the REST endpoint once a second")
    assert result.decision == Decision.WARN

def test_exact_scope_high_sim_blocks(ledger):
    rec = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll the API every second",
        rejection_reason="rate limits",
        status=Status.ACTIVE,
        scope=Scope.EXACT_IMPLEMENTATION
    )
    ledger.add(rec)
    g = Guard(ledger)
    result = g.check_one("poll the API every second using requests library")
    assert result.decision == Decision.BLOCK
    assert result.similarity >= 0.7

def test_default_scope_blocks(ledger):
    rec = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll the API every second",
        rejection_reason="rate limits",
        status=Status.ACTIVE
    )
    ledger.add(rec)
    g = Guard(ledger)
    result = g.check_one("Let's hit the REST endpoint once a second")
    assert result.decision == Decision.BLOCK
