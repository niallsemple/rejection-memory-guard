from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any
import uuid
import json
from datetime import datetime, timezone


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    REOPENED = "REOPENED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class Scope(str, Enum):
    EXACT_IMPLEMENTATION = "EXACT_IMPLEMENTATION"
    MECHANISM = "MECHANISM"
    ARCHITECTURE = "ARCHITECTURE"
    TECHNOLOGY = "TECHNOLOGY"
    STRATEGY = "STRATEGY"
    VENDOR = "VENDOR"
    ENTIRE_CONCEPT = "ENTIRE_CONCEPT"


class RejectionType(str, Enum):
    HARD = "HARD"
    CONDITIONAL = "CONDITIONAL"
    TEMPORARY = "TEMPORARY"
    SUPERSEDED = "SUPERSEDED"
    FAILED_EXPERIMENT = "FAILED_EXPERIMENT"
    PREFERENCE = "PREFERENCE"


class RecordType(str, Enum):
    REJECTION = "REJECTION"
    ACCEPTED = "ACCEPTED"
    FAILED_EXPERIMENT = "FAILED_EXPERIMENT"
    OPEN_QUESTION = "OPEN_QUESTION"
    ASSUMPTION = "ASSUMPTION"
    CONSTRAINT = "CONSTRAINT"
    DECISION = "DECISION"
    TRIGGER = "TRIGGER"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    RECONSIDER = "RECONSIDER"


@dataclass
class Fingerprint:
    objective: str = ""
    mechanism: str = ""
    why_failed: str = ""
    constraint_violated: str = ""
    conditions_to_reconsider: str = ""
    replacement: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "objective": self.objective,
            "mechanism": self.mechanism,
            "why_failed": self.why_failed,
            "constraint_violated": self.constraint_violated,
            "conditions_to_reconsider": self.conditions_to_reconsider,
            "replacement": self.replacement,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "Fingerprint":
        return cls(
            objective=d.get("objective", ""),
            mechanism=d.get("mechanism", ""),
            why_failed=d.get("why_failed", ""),
            constraint_violated=d.get("constraint_violated", ""),
            conditions_to_reconsider=d.get("conditions_to_reconsider", ""),
            replacement=d.get("replacement", ""),
        )

    def text(self) -> str:
        parts = [
            self.objective,
            self.mechanism,
            self.why_failed,
            self.constraint_violated,
            self.conditions_to_reconsider,
            self.replacement,
        ]
        return " | ".join(p for p in parts if p)


@dataclass
class StatusChange:
    status: Status
    at: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "at": self.at,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StatusChange":
        return cls(
            status=Status(d["status"]),
            at=d["at"],
            reason=d["reason"],
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Record:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    record_type: RecordType = RecordType.REJECTION
    canonical_idea: str = ""
    aliases: List[str] = field(default_factory=list)
    category: str = ""
    description: str = ""
    rejected_at: str = field(default_factory=_now_iso)
    rejection_reason: str = ""
    evidence: str = ""
    constraints_at_time: str = ""
    status: Status = Status.ACTIVE
    reconsider_if: str = ""
    superseded_by: str = ""
    times_reproposed: int = 0
    last_reproposal: str = ""
    confidence: float = 0.8
    scope: Scope = Scope.ENTIRE_CONCEPT
    rejection_type: RejectionType = RejectionType.HARD
    original_discussion: str = ""
    fingerprint: Fingerprint = field(default_factory=Fingerprint)
    status_history: List[StatusChange] = field(default_factory=list)

    def __post_init__(self):
        if not self.status_history:
            self.status_history.append(
                StatusChange(
                    status=self.status,
                    at=self.rejected_at,
                    reason="created",
                )
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "record_type": self.record_type.value,
            "canonical_idea": self.canonical_idea,
            "aliases": self.aliases,
            "category": self.category,
            "description": self.description,
            "rejected_at": self.rejected_at,
            "rejection_reason": self.rejection_reason,
            "evidence": self.evidence,
            "constraints_at_time": self.constraints_at_time,
            "status": self.status.value,
            "reconsider_if": self.reconsider_if,
            "superseded_by": self.superseded_by,
            "times_reproposed": self.times_reproposed,
            "last_reproposal": self.last_reproposal,
            "confidence": self.confidence,
            "scope": self.scope.value,
            "rejection_type": self.rejection_type.value,
            "original_discussion": self.original_discussion,
            "fingerprint": self.fingerprint.to_dict(),
            "status_history": [sc.to_dict() for sc in self.status_history],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Record":
        return cls(
            id=d["id"],
            record_type=RecordType(d["record_type"]),
            canonical_idea=d["canonical_idea"],
            aliases=d["aliases"],
            category=d["category"],
            description=d["description"],
            rejected_at=d["rejected_at"],
            rejection_reason=d["rejection_reason"],
            evidence=d["evidence"],
            constraints_at_time=d["constraints_at_time"],
            status=Status(d["status"]),
            reconsider_if=d["reconsider_if"],
            superseded_by=d["superseded_by"],
            times_reproposed=d["times_reproposed"],
            last_reproposal=d["last_reproposal"],
            confidence=d["confidence"],
            scope=Scope(d["scope"]),
            rejection_type=RejectionType(d["rejection_type"]),
            original_discussion=d["original_discussion"],
            fingerprint=Fingerprint.from_dict(d["fingerprint"]),
            status_history=[StatusChange.from_dict(sc) for sc in d["status_history"]],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, s: str) -> "Record":
        return cls.from_dict(json.loads(s))

    def set_status(self, new_status: Status, reason: str) -> None:
        self.status = new_status
        self.status_history.append(
            StatusChange(
                status=new_status,
                at=_now_iso(),
                reason=reason,
            )
        )

    def match_text(self) -> str:
        parts = [
            self.canonical_idea,
            " ".join(self.aliases),
            self.description,
            self.fingerprint.text(),
        ]
        return " ".join(p for p in parts if p)
