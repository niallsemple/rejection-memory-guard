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

def add_wallet(ledger):
    ledger.add(Record(id="copy1", record_type=RecordType.REJECTION, status=Status.ACTIVE,
        canonical_idea="Copy trades of top-performing on-chain wallets",
        rejection_reason="Edge decays before execution.",
        reconsider_if="execution latency drops below 100ms"))

SOLANA_TASKS = ["improve the Solana trading strategy using top wallets",
                "Working on a Solana trading strategy; several ideas evaluated."]

def test_compaction_lists_relevant_wallet_rejection(ledger):
    add_two(ledger)
    add_wallet(ledger)
    for task in SOLANA_TASKS:
        result = compaction_block(ledger, task)
        assert "(none relevant)" not in result
        assert "- Copy trades of top-performing on-chain wallets [copy1, rejected " in result
        assert "\n  Reason: Edge decays before execution\n" in result
        assert result.endswith("  Reconsider only if: execution latency drops below 100ms")
        assert "mongo1" not in result
        assert "poll1" not in result

def test_handoff_lists_relevant_wallet_rejection(ledger):
    add_two(ledger)
    add_wallet(ledger)
    result = handoff_block(ledger, SOLANA_TASKS[1], "momentum signals")
    known = result.split("KNOWN REJECTIONS:\n")[1].split("\nCURRENT APPROACH:")[0]
    assert known.startswith("- Copy trades of top-performing on-chain wallets [copy1")
    assert "  Reason: Edge decays before execution" in known
    assert "  Reconsider only if: execution latency drops below 100ms" in known
    assert "- none" not in known
    assert "mongo1" not in known
