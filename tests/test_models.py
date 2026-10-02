import json
import pytest
from rmg.models import (
    Record,
    Fingerprint,
    StatusChange,
    Status,
    Scope,
    RejectionType,
    RecordType,
    Decision,
)


def test_defaults():
    r = Record(canonical_idea="test idea")
    assert r.id is not None
    assert len(r.id) == 12
    assert r.record_type == RecordType.REJECTION
    assert r.status == Status.ACTIVE
    assert r.scope == Scope.ENTIRE_CONCEPT
    assert r.rejection_type == RejectionType.HARD
    assert r.confidence == 0.8
    assert r.times_reproposed == 0
    assert len(r.status_history) == 1
    assert r.status_history[0].reason == "created"
    assert r.status_history[0].status == Status.ACTIVE


def test_fingerprint_round_trip():
    fp = Fingerprint(
        objective="obj",
        mechanism="mech",
        why_failed="why",
        constraint_violated="constraint",
        conditions_to_reconsider="cond",
        replacement="repl",
    )
    d = fp.to_dict()
    fp2 = Fingerprint.from_dict(d)
    assert fp == fp2
    assert fp.text() == "obj | mech | why | constraint | cond | repl"


def test_record_round_trip_dict():
    r = Record(
        canonical_idea="Poll API",
        aliases=["polling"],
        category="networking",
        description="Polling is bad",
        rejection_reason="Latency",
        evidence="Test logs",
        constraints_at_time="High traffic",
        reconsider_if="Low traffic",
        superseded_by="WebSockets",
        times_reproposed=2,
        last_reproposal="2023-01-01",
        confidence=0.9,
        scope=Scope.MECHANISM,
        rejection_type=RejectionType.HARD,
        original_discussion="User said no",
        fingerprint=Fingerprint(objective="Poll", mechanism="HTTP"),
    )
    d = r.to_dict()
    r2 = Record.from_dict(d)
    assert r.id == r2.id
    assert r.canonical_idea == r2.canonical_idea
    assert r.aliases == r2.aliases
    assert r.status == r2.status
    assert r.scope == r2.scope
    assert r.rejection_type == r2.rejection_type
    assert r.fingerprint == r2.fingerprint
    assert len(r.status_history) == len(r2.status_history)
    assert r.status_history[0] == r2.status_history[0]


def test_record_round_trip_json():
    r = Record(canonical_idea="Test JSON")
    j = r.to_json()
    r2 = Record.from_json(j)
    assert r.id == r2.id
    assert r.canonical_idea == r2.canonical_idea


def test_set_status_appends_history():
    r = Record(canonical_idea="Test Status")
    initial_len = len(r.status_history)
    r.set_status(Status.ARCHIVED, "User requested")
    assert len(r.status_history) == initial_len + 1
    assert r.status == Status.ARCHIVED
    assert r.status_history[-1].reason == "User requested"
    assert r.status_history[-1].status == Status.ARCHIVED
    # First entry should still be "created"
    assert r.status_history[0].reason == "created"


def test_enums_serialise_as_strings():
    r = Record(canonical_idea="Enum Test")
    d = r.to_dict()
    assert d["status"] == "ACTIVE"
    assert d["scope"] == "ENTIRE_CONCEPT"
    assert d["rejection_type"] == "HARD"
    assert d["record_type"] == "REJECTION"
    
    # Check that from_dict works with strings
    r2 = Record.from_dict(d)
    assert r2.status == Status.ACTIVE
    assert r2.scope == Scope.ENTIRE_CONCEPT
