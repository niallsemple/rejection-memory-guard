import os
from typing import List, Optional, Dict, Any

from rmg.models import Record, Fingerprint, RecordType, Status, Scope, RejectionType
from rmg.ledger import Ledger
from rmg.guard import Guard
from rmg.extract import extract_rejections
from rmg.similarity import similarity

_LEDGER = None

def get_ledger() -> Ledger:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = Ledger(os.environ.get("RMG_DB"))
    return _LEDGER

def set_ledger(ledger: Ledger):
    global _LEDGER
    _LEDGER = ledger

def _l(ledger: Optional[Ledger]) -> Ledger:
    return ledger or get_ledger()

def reject(
    idea: str,
    reason: str,
    *,
    aliases: Optional[List[str]] = None,
    category: str = "",
    scope: Scope = Scope.ENTIRE_CONCEPT,
    rejection_type: RejectionType = RejectionType.HARD,
    reconsider_if: str = "",
    evidence: str = "",
    original_discussion: str = "",
    replacement: str = "",
    ledger: Optional[Ledger] = None
) -> Record:
    l = _l(ledger)
    
    if reconsider_if and rejection_type == RejectionType.HARD:
        rejection_type = RejectionType.CONDITIONAL

    fingerprint = Fingerprint(
        objective=category or idea,
        mechanism=idea,
        why_failed=reason,
        constraint_violated="",
        conditions_to_reconsider=reconsider_if,
        replacement=replacement
    )

    record = Record(
        canonical_idea=idea,
        aliases=aliases or [],
        category=category,
        rejection_reason=reason,
        evidence=evidence,
        original_discussion=original_discussion,
        status=Status.ACTIVE,
        reconsider_if=reconsider_if,
        superseded_by="",
        scope=scope,
        rejection_type=rejection_type,
        fingerprint=fingerprint
    )
    
    l.add(record)
    l.log_event("reject", record.id)
    return record

def reopen(id: str, reason: str, ledger: Optional[Ledger] = None):
    l = _l(ledger)
    l.set_status(id, Status.REOPENED, reason)
    l.log_event("reopen", id)

def supersede(id: str, new_idea: str, ledger: Optional[Ledger] = None):
    l = _l(ledger)
    record = l.get(id)
    if record:
        record.superseded_by = new_idea
        l.update(record)
        l.set_status(id, Status.SUPERSEDED, f"Superseded by {new_idea}")
        l.log_event("supersede", id)

def archive(id: str, ledger: Optional[Ledger] = None):
    l = _l(ledger)
    l.set_status(id, Status.ARCHIVED, "archived")
    l.log_event("archive", id)

def update_conditions(id: str, conditions: str, ledger: Optional[Ledger] = None):
    l = _l(ledger)
    record = l.get(id)
    if record:
        record.reconsider_if = conditions
        record.fingerprint.conditions_to_reconsider = conditions
        l.update(record)

def check(candidate: str, context: Optional[str] = None, ledger: Optional[Ledger] = None) -> List[Dict[str, Any]]:
    l = _l(ledger)
    guard = Guard(l)
    results = guard.check(candidate, context)
    for r in results:
        l.log_event("check", r.matched_rejection.get("id") if r.matched_rejection else None)
    return [r.to_dict() for r in results]

def search_rejections(query: str, limit: int = 10, ledger: Optional[Ledger] = None) -> List[Record]:
    l = _l(ledger)
    records = l.all()
    scored = []
    for r in records:
        sim = similarity(query, r.match_text())
        if sim > 0.1:
            scored.append((sim, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]

def ingest(messages: List[Dict[str, str]], ledger: Optional[Ledger] = None) -> List[Record]:
    l = _l(ledger)
    records = extract_rejections(messages)
    for r in records:
        l.add(r)
    return records

def mark_false_positive(record_id: str, ledger: Optional[Ledger] = None):
    l = _l(ledger)
    l.log_event("false_positive", record_id)
