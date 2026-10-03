import pytest
import os
from rmg.ledger import Ledger
from rmg.models import Status
import rmg.api as api

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

@pytest.fixture
def ledger(tmp_path):
    l = Ledger(str(tmp_path / "t.db"))
    yield l
    l.close()

def test_reject_reopen_supersede_archive(ledger):
    rec = api.reject("poll the API every second", "rate limits", ledger=ledger)
    assert rec.status == Status.ACTIVE
    
    api.reopen(rec.id, "rethinking", ledger=ledger)
    updated = ledger.get(rec.id)
    assert updated.status == Status.REOPENED
    assert len(updated.status_history) == 2

    api.supersede(rec.id, "use websockets", ledger=ledger)
    updated = ledger.get(rec.id)
    assert updated.status == Status.SUPERSEDED
    assert updated.superseded_by == "use websockets"

    api.archive(rec.id, ledger=ledger)
    updated = ledger.get(rec.id)
    assert updated.status == Status.ARCHIVED

def test_update_conditions(ledger):
    rec = api.reject("poll the API every second", "rate limits", ledger=ledger)
    api.update_conditions(rec.id, "if rate limits are removed", ledger=ledger)
    updated = ledger.get(rec.id)
    assert updated.reconsider_if == "if rate limits are removed"
    assert updated.fingerprint.conditions_to_reconsider == "if rate limits are removed"

def test_check(ledger):
    api.reject("poll the API every second", "rate limits", ledger=ledger)
    results = api.check("Let's hit the REST endpoint once a second", ledger=ledger)
    assert len(results) > 0
    assert results[0]["decision"] == "BLOCK"

def test_search_rejections(ledger):
    rec = api.reject("poll the API every second", "rate limits", ledger=ledger)
    results = api.search_rejections("poll the API", ledger=ledger)
    assert len(results) == 1
    assert results[0].id == rec.id

def test_ingest(ledger):
    messages = [
        {"role": "assistant", "content": "I suggest we poll the API every second."},
        {"role": "user", "content": "We already tried that, didn't work."}
    ]
    records = api.ingest(messages, ledger=ledger)
    assert len(records) == 1
    assert len(ledger.all()) == 1
