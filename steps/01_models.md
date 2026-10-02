Implement step 1 of SPEC.md (read it). Create the package skeleton and data models only.

Create these files:
- `rmg/__init__.py` (exports `__version__ = "0.1.0"`)
- `rmg/models.py`
- `tests/__init__.py` (empty)
- `tests/test_models.py`

`rmg/models.py` (stdlib only: dataclasses, enum, json, uuid, datetime):
- `class Status(str, Enum)`: ACTIVE, REOPENED, SUPERSEDED, ARCHIVED
- `class Scope(str, Enum)`: EXACT_IMPLEMENTATION, MECHANISM, ARCHITECTURE, TECHNOLOGY, STRATEGY, VENDOR, ENTIRE_CONCEPT
- `class RejectionType(str, Enum)`: HARD, CONDITIONAL, TEMPORARY, SUPERSEDED, FAILED_EXPERIMENT, PREFERENCE
- `class RecordType(str, Enum)`: REJECTION, ACCEPTED, FAILED_EXPERIMENT, OPEN_QUESTION, ASSUMPTION, CONSTRAINT, DECISION, TRIGGER
- `class Decision(str, Enum)`: ALLOW, WARN, BLOCK, RECONSIDER
- `@dataclass Fingerprint`: objective, mechanism, why_failed, constraint_violated, conditions_to_reconsider, replacement (all str, default ""). Methods `to_dict()`, `from_dict(d)` classmethod, `text()` returning all non-empty fields joined by " | ".
- `@dataclass StatusChange`: status (Status), at (ISO str), reason (str). to_dict/from_dict.
- `@dataclass Record` (generic record for future Decision Memory) with fields:
  id (str, default uuid4 hex[:12]), record_type (RecordType, default REJECTION), canonical_idea (str), aliases (list[str]), category (str), description (str), rejected_at (ISO str, default now UTC), rejection_reason (str), evidence (str), constraints_at_time (str), status (Status, default ACTIVE), reconsider_if (str), superseded_by (str), times_reproposed (int, 0), last_reproposal (str), confidence (float, 0.8), scope (Scope, default ENTIRE_CONCEPT), rejection_type (RejectionType, default HARD), original_discussion (str), fingerprint (Fingerprint), status_history (list[StatusChange]).
  On creation, if status_history is empty, append StatusChange(status, rejected_at, "created").
  Methods: `to_dict()` (enums as their string values, nested objects as dicts), `from_dict(d)` classmethod (round-trips exactly), `to_json()`, `from_json(s)`, `set_status(new_status, reason)` which updates status and appends to status_history (never removes entries), `match_text()` returning canonical_idea + aliases + description + fingerprint.text() joined.

`tests/test_models.py`: test defaults, to_dict/from_dict round trip, JSON round trip, set_status appends history (history length grows, first entry is "created"), enums serialise as strings.
Keep code simple and complete. Do not leave TODOs.
