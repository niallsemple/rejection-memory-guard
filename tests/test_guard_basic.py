import pytest
import os
import json
from rmg.guard import Guard, extract_proposals, GuardResult
from rmg.ledger import Ledger
from rmg.models import Record, RecordType, Status, Decision

@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

@pytest.fixture
def ledger(tmp_path):
    db_path = tmp_path / "test_ledger.db"
    l = Ledger(str(db_path))
    yield l
    l.close()

def test_extract_proposals():
    msg = "Let's hit the REST endpoint once a second. We could query the endpoint at 1 Hz. Just a note."
    proposals = extract_proposals(msg)
    assert "Let's hit the REST endpoint once a second" in proposals
    assert "We could query the endpoint at 1 Hz" in proposals
    # "Just a note" doesn't have a verb, so it shouldn't be there if others are found
    assert "Just a note." not in proposals

def test_extract_proposals_no_verbs():
    msg = "Hello world. This is a test."
    proposals = extract_proposals(msg)
    assert "Hello world" in proposals
    assert "This is a test" in proposals

def test_guard_block_polling(ledger):
    # Setup rejection
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll the API every second",
        rejection_reason="rate limits and latency",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    
    # Test 1
    result = guard.check_one("Let's hit the REST endpoint once a second")
    assert result.decision == Decision.BLOCK
    assert result.matched_rejection is not None
    assert result.matched_rejection["id"] == record.id
    assert result.similarity > 0.45
    
    # Check increment
    updated_record = ledger.get(record.id)
    assert updated_record.times_reproposed == 1
    
    # Test 2
    result2 = guard.check_one("We could query the endpoint at 1 Hz")
    assert result2.decision == Decision.BLOCK
    assert result2.matched_rejection is not None
    assert result2.matched_rejection["id"] == record.id
    
    updated_record2 = ledger.get(record.id)
    assert updated_record2.times_reproposed == 2

def test_guard_block_copy_trading(ledger):
    # Setup rejection
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="copy profitable wallets",
        aliases=["copy trading"],
        rejection_reason="too risky",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    
    # Test 1
    result = guard.check_one("mirror the top traders")
    assert result.decision == Decision.BLOCK
    assert result.matched_rejection is not None
    assert result.matched_rejection["id"] == record.id
    
    # Test 2
    result2 = guard.check_one("follow whales")
    assert result2.decision == Decision.BLOCK
    assert result2.matched_rejection is not None
    assert result2.matched_rejection["id"] == record.id
    
    # Test 3
    result3 = guard.check_one("duplicate trades from top addresses")
    assert result3.decision == Decision.BLOCK
    assert result3.matched_rejection is not None
    assert result3.matched_rejection["id"] == record.id

def test_guard_allow_unrelated(ledger):
    # Setup rejection
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll the API every second",
        rejection_reason="rate limits",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    
    result = guard.check_one("bake a cake")
    assert result.decision == Decision.ALLOW
    assert result.matched_rejection is None
    assert result.reason == "No matching rejection"

def test_guard_result_json_keys(ledger):
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll the API every second",
        rejection_reason="rate limits",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    result = guard.check_one("Let's hit the REST endpoint once a second")
    
    d = result.to_dict()
    expected_keys = {"candidate", "decision", "matched_rejection", "similarity", "reason", "conditions_changed"}
    assert set(d.keys()) == expected_keys
    assert d["decision"] == "BLOCK"
    
    j = result.to_json()
    parsed = json.loads(j)
    assert set(parsed.keys()) == expected_keys
