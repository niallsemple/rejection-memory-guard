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
    db_path = tmp_path / "t.db"
    l = Ledger(str(db_path))
    yield l
    l.close()

def test_reconsider_dict_context(ledger):
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll an API every second",
        rejection_reason="we need sub-second latency",
        reconsider_if="if 30 second updates become acceptable",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    result = guard.check_one(
        "poll the API every 30 seconds", 
        context={"requirements": ["30 second updates are fine now"]}
    )
    
    assert result.decision == Decision.RECONSIDER
    assert result.conditions_changed is True
    assert result.reason.startswith("This was previously rejected because we need sub-second latency")
    events = ledger.events("reconsider")
    assert events is not None and len(events) > 0

def test_reconsider_none_context_blocks(ledger):
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll an API every second",
        rejection_reason="we need sub-second latency",
        reconsider_if="if 30 second updates become acceptable",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    result = guard.check_one("poll the API every 30 seconds", context=None)
    assert result.decision == Decision.BLOCK

def test_reconsider_string_context(ledger):
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll an API every second",
        rejection_reason="we need sub-second latency",
        reconsider_if="if 30 second updates become acceptable",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    result = guard.check_one(
        "poll the API every 30 seconds", 
        context="latency no longer matters"
    )
    assert result.decision == Decision.RECONSIDER

def test_reconsider_cost_relaxation(ledger):
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="use a managed Kafka cluster",
        rejection_reason="too expensive",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    result = guard.check_one(
        "use a managed Kafka cluster", 
        context={"requirements": ["budget increased"]}
    )
    assert result.decision == Decision.RECONSIDER

def test_reconsider_text_format(ledger):
    record = Record(
        record_type=RecordType.REJECTION,
        canonical_idea="poll an API every second",
        rejection_reason="we need sub-second latency",
        status=Status.ACTIVE
    )
    ledger.add(record)
    
    guard = Guard(ledger)
    text = guard.reconsider_text(record, "X")
    assert text == "This was previously rejected because we need sub-second latency. I am reconsidering it because X now appears to be true."

def test_reconsider_text_clean_grammar(ledger):
    record = Record(record_type=RecordType.REJECTION, canonical_idea="Copy trades of top-performing on-chain wallets",
        rejection_reason="Edge decays before execution.", reconsider_if="execution latency drops below 100ms.",
        status=Status.ACTIVE)
    text = Guard(ledger).reconsider_text(record, "our execution latency now drops below 100ms")
    assert text == ("This was previously rejected because edge decays before execution. "
                    "I am reconsidering it because execution latency drops below 100ms now appears to be true.")
    assert ".." not in text

def test_reconsider_text_keeps_acronym_and_uses_change(ledger):
    record = Record(record_type=RecordType.REJECTION, canonical_idea="poll the API", rejection_reason="API rate limits",
        status=Status.ACTIVE)
    text = Guard(ledger).reconsider_text(record, "Budget increased.")
    assert text == "This was previously rejected because API rate limits. I am reconsidering it because budget increased now appears to be true."

def test_extract_proposals_keeps_hyphenated_words():
    assert extract_proposals("How about we mirror the positions of top-performing whale addresses?") == ["How about we mirror the positions of top-performing whale addresses"]
    assert extract_proposals("- use websockets\n- try polling") == ["use websockets", "try polling"]
