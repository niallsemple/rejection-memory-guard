Implement step 9 of SPEC.md: analytics. Read `rmg/ledger.py` (events table) and `rmg/api.py`.

Create `rmg/analytics.py` and `tests/test_analytics.py`.
- `metrics(ledger) -> dict` with keys: rejected_ideas_total (count of REJECTION records, any status), blocked_reproposals (events "block"), warning_matches (events "warn"), reopened_ideas (records with REOPENED in their status_history), most_repeated_rejection (canonical_idea with highest times_reproposed or None), agent_reproposal_rate (blocked_reproposals / number of "check" events, 0.0 if none — make the Guard or api.check log a "check" event per proposal checked if it does not already; rmg/api.py check already logs a "check" event per result), false_positive_rate (false_positive events / max(1, blocked_reproposals + warning_matches)).
- `dashboard(ledger) -> str`: a readable multi-line text table of all metrics plus top 5 rejections by times_reproposed. `print_dashboard(ledger)`.
- Wire CLI `stats` to print the dashboard if not already.

Tests (RMG_OFFLINE=1): after rejecting 2 ideas, 2 blocked paraphrases, 1 warn (WebSocket fallback), 1 reopen and 1 false positive mark: values are as expected; dashboard contains every metric name.
