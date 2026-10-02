import pytest
from rmg.ledger import Ledger
from rmg.models import Record, Status, RecordType


def test_add_get_round_trip(tmp_path):
    db_path = str(tmp_path / "test.db")
    with Ledger(db_path) as ledger:
        record = Record(
            id="test-id",
            canonical_idea="Test Idea",
            rejection_reason="Too slow",
            status=Status.ACTIVE
        )
        ledger.add(record)
        
        fetched = ledger.get("test-id")
        assert fetched is not None
        assert fetched.canonical_idea == "Test Idea"
        assert fetched.rejection_reason == "Too slow"
        assert fetched.status == Status.ACTIVE


def test_persistence_across_instances(tmp_path):
    db_path = str(tmp_path / "test.db")
    
    record = Record(
        id="persist-id",
        canonical_idea="Persistent Idea",
        status=Status.ACTIVE
    )
    
    with Ledger(db_path) as ledger1:
        ledger1.add(record)
        
    with Ledger(db_path) as ledger2:
        fetched = ledger2.get("persist-id")
        assert fetched is not None
        assert fetched.canonical_idea == "Persistent Idea"


def test_set_status_history(tmp_path):
    db_path = str(tmp_path / "test.db")
    with Ledger(db_path) as ledger:
        record = Record(
            id="status-id",
            canonical_idea="Status Test",
            status=Status.ACTIVE
        )
        ledger.add(record)
        
        ledger.set_status("status-id", Status.REOPENED, "Reopened for testing")
        ledger.set_status("status-id", Status.ARCHIVED, "Archived after test")
        
        fetched = ledger.get("status-id")
        assert fetched is not None
        assert len(fetched.status_history) == 3
        assert fetched.status_history[0].status == Status.ACTIVE
        assert fetched.status_history[1].status == Status.REOPENED
        assert fetched.status_history[2].status == Status.ARCHIVED
        assert fetched.status == Status.ARCHIVED


def test_active_excludes_archived_superseded(tmp_path):
    db_path = str(tmp_path / "test.db")
    with Ledger(db_path) as ledger:
        active_rec = Record(
            id="active-1",
            canonical_idea="Active Idea",
            status=Status.ACTIVE,
            record_type=RecordType.REJECTION
        )
        reopened_rec = Record(
            id="reopened-1",
            canonical_idea="Reopened Idea",
            status=Status.REOPENED,
            record_type=RecordType.REJECTION
        )
        archived_rec = Record(
            id="archived-1",
            canonical_idea="Archived Idea",
            status=Status.ARCHIVED,
            record_type=RecordType.REJECTION
        )
        superseded_rec = Record(
            id="superseded-1",
            canonical_idea="Superseded Idea",
            status=Status.SUPERSEDED,
            record_type=RecordType.REJECTION
        )
        
        ledger.add(active_rec)
        ledger.add(reopened_rec)
        ledger.add(archived_rec)
        ledger.add(superseded_rec)
        
        active_records = ledger.active()
        active_ids = [r.id for r in active_records]
        
        assert "active-1" in active_ids
        assert "reopened-1" in active_ids
        assert "archived-1" not in active_ids
        assert "superseded-1" not in active_ids


def test_increment_reproposal(tmp_path):
    db_path = str(tmp_path / "test.db")
    with Ledger(db_path) as ledger:
        record = Record(
            id="reprop-id",
            canonical_idea="Reprop Idea",
            status=Status.ACTIVE,
            times_reproposed=0
        )
        ledger.add(record)
        
        ledger.increment_reproposal("reprop-id")
        
        fetched = ledger.get("reprop-id")
        assert fetched is not None
        assert fetched.times_reproposed == 1
        assert fetched.last_reproposal != ""


def test_events_logging(tmp_path):
    db_path = str(tmp_path / "test.db")
    with Ledger(db_path) as ledger:
        ledger.log_event("test_event", record_id="rec-1", payload={"key": "value"})
        ledger.log_event("test_event", record_id="rec-2")
        ledger.log_event("other_event", record_id="rec-3")
        
        test_events = ledger.events(kind="test_event")
        assert len(test_events) == 2
        assert test_events[0]["kind"] == "test_event"
        assert test_events[0]["record_id"] == "rec-1"
        assert test_events[0]["payload"] == {"key": "value"}
        
        all_events = ledger.events()
        assert len(all_events) == 3


def test_no_delete_method():
    assert not hasattr(Ledger, "delete")
