Keep the reply short: use small SEARCH/REPLACE blocks on rmg/guard.py (do NOT rewrite the whole file); write tests/test_guard_reconsider.py in full.

Step 6b: contradiction / reconsider detection in `rmg/guard.py`. Keep all existing tests passing. The user's latest explicit instruction always wins over a stored rejection.

1. Add a method `Guard.reconsider_text(self, record, change) -> str` returning exactly
   `f"This was previously rejected because {record.rejection_reason}. I am reconsidering it because {change} has changed."`
2. Add a module-level helper `_requirements(context) -> list`: None -> []; a str -> [context]; a dict -> list(context.get("requirements", [])).
3. Add a module-level helper `_relaxes(reason: str, requirement: str) -> bool`, lowercase both:
   True if reason mentions any of ("latency", "sub-second", "real-time", "realtime") and requirement mentions any of ("30 second", "30 s", "latency no longer matters", "slower updates", "updates are fine");
   True if reason mentions any of ("cost", "expensive") and requirement mentions any of ("budget increased", "cost is not an issue", "cost doesn't matter");
   else False.
4. In `check_one(self, proposal, context=None)`: after the loop has picked `best_record`, and before the side effects block, if `best_record` is not None and `best_decision in (Decision.BLOCK, Decision.WARN)`: for each requirement `req` in `_requirements(context)`: if (`best_record.reconsider_if` and `similarity(req, best_record.reconsider_if, embedder=self.embedder) >= 0.35`) or `_relaxes(best_record.rejection_reason, req)`: set `best_decision = Decision.RECONSIDER`, `best_conditions_changed = True`, `best_reason = self.reconsider_text(best_record, req)` and break.
   In the side effects block add: `elif best_decision == Decision.RECONSIDER: self.ledger.log_event("reconsider", best_record.id)`. A RECONSIDER must NOT call increment_reproposal.
   `check(message, context=None)` already passes context through; keep it.

tests/test_guard_reconsider.py uses the same imports and fixtures as tests/test_guard_basic.py (`offline_env` autouse monkeypatch of RMG_OFFLINE=1, `ledger` fixture with `Ledger(str(tmp_path / "t.db"))`). Tests:
- rejection canonical_idea "poll an API every second", rejection_reason "we need sub-second latency", reconsider_if "if 30 second updates become acceptable"; `Guard(ledger).check_one("poll the API every 30 seconds", context={"requirements": ["30 second updates are fine now"]})` -> decision RECONSIDER, conditions_changed True, reason startswith "This was previously rejected because we need sub-second latency", and `ledger.events("reconsider")` is non-empty.
- same record, same proposal, context=None -> BLOCK.
- same record, context as a plain string "latency no longer matters" -> RECONSIDER.
- rejection reason "too expensive" (no reconsider_if), canonical_idea "use a managed Kafka cluster"; proposal "use a managed Kafka cluster", context {"requirements": ["budget increased"]} -> RECONSIDER.
- `Guard(ledger).reconsider_text(record, "X")` == "This was previously rejected because we need sub-second latency. I am reconsidering it because X has changed."
