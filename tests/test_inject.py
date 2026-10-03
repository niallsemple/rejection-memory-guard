import pytest
from rmg.ledger import Ledger
from rmg.models import Record, RecordType, Status
from rmg.inject import relevant_rejections, compaction_block, handoff_block

@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

@pytest.fixture
def ledger(tmp_path):
    l = Ledger(str(tmp_path / "t.db"))
    yield l
    l.close()

def add_two(ledger):
    ledger.add(Record(id="poll1", record_type=RecordType.REJECTION, status=Status.ACTIVE,
        canonical_idea="poll the price API every second for real-time price updates",
        rejection_reason="rate limits"))
    ledger.add(Record(id="mongo1", record_type=RecordType.REJECTION, status=Status.ACTIVE,
        canonical_idea="use MongoDB for storage", rejection_reason="ops burden"))

def test_compaction_block(ledger):
    add_two(ledger)
    result = compaction_block(ledger, "design real-time price updates")
    assert result.startswith("REJECTED APPROACHES — DO NOT REPROPOSE")
    assert "poll1" in result
    assert "rate limits" in result
    assert "mongo1" not in result

def test_relevant_rejections(ledger):
    add_two(ledger)
    results = relevant_rejections(ledger, "design real-time price updates")
    assert [r.id for r in results] == ["poll1"]

def test_handoff_block(ledger):
    add_two(ledger)
    result = handoff_block(ledger, "design real-time price updates", "use websockets")
    
    idx_task = result.index("TASK:")
    idx_known = result.index("KNOWN REJECTIONS:")
    idx_current = result.index("CURRENT APPROACH:")
    
    assert idx_task < idx_known < idx_current
    assert "poll1" in result
    assert "use websockets" in result

def test_empty_ledger(ledger):
    result_comp = compaction_block(ledger, "some task")
    assert "- (none relevant)" in result_comp
    
    result_hand = handoff_block(ledger, "some task")
    assert "- none" in result_hand
    assert "(not decided)" in result_hand
