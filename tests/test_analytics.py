import os
import pytest
from rmg.ledger import Ledger
from rmg import api
from rmg.analytics import metrics, dashboard

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

def test_analytics(tmp_path):
    ledger = Ledger(str(tmp_path / "t.db"))
    
    # Setup data
    a = api.reject("poll the API every second", "rate limits", ledger=ledger)
    api.reject("use MongoDB for storage", "ops burden", ledger=ledger)
    
    # Checks (2 blocks expected based on similarity to "poll the API every second")
    api.check("Let's hit the REST endpoint once a second", ledger=ledger)
    api.check("poll the API every second please", ledger=ledger)
    
    # Check that might warn or block (depending on similarity threshold)
    api.check("Use WebSockets with REST polling only as a fallback on disconnect", ledger=ledger)
    
    # Reopen and mark false positive
    api.reopen(a.id, "new limits", ledger=ledger)
    api.mark_false_positive(a.id, ledger=ledger)
    
    # Get metrics
    m = metrics(ledger)
    
    # Assertions
    assert m["rejected_ideas_total"] == 2
    assert m["blocked_reproposals"] == 2
    assert m["reopened_ideas"] == 1
    assert m["most_repeated_rejection"] == "poll the API every second"
    assert 0 < m["agent_reproposal_rate"] <= 1
    assert m["false_positive_rate"] > 0
    assert m["warning_matches"] >= 0
    
    # Dashboard check
    d = dashboard(ledger)
    for key in m.keys():
        assert key in d

