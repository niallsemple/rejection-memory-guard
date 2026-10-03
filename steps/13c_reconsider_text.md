Keep the reply short: use small SEARCH/REPLACE blocks on rmg/guard.py and tests/test_guard_reconsider.py (do NOT rewrite whole files). Do not edit any other file.

Step 13c: grammatical RECONSIDER text and no truncated proposals in `rmg/guard.py`. Bugs seen today:
- reason text "This was previously rejected because We already tried that, ... below 100ms.. I am reconsidering it because our execution latency now drops below 100ms has changed." (capital letter mid-sentence, double period, wrong template);
- `extract_proposals("How about we mirror the positions of top-performing whale addresses?")` returns "How about we mirror the positions of top" because the bullet regex `re.sub(r'[-*•]\s*', '\n', message)` also splits on hyphens inside words.

Changes in rmg/guard.py:
1. In `extract_proposals`, replace `cleaned_message = re.sub(r'[-*•]\s*', '\n', message)` with `cleaned_message = re.sub(r'(?m)^\s*[-*•]\s+', '\n', message)` (only bullets at the start of a line).
2. Add a module-level helper:
```python
def _clause(text) -> str:
    t = (text or "").strip().rstrip(".!?;, ").strip()
    if t.lower().startswith("if "):
        t = t[3:].strip()
    if len(t) > 1 and t[0].isupper() and not t[1].isupper():
        t = t[0].lower() + t[1:]
    return t
```
3. Replace `Guard.reconsider_text` with:
```python
    def reconsider_text(self, record, change) -> str:
        reason = _clause(record.rejection_reason) or "it did not fit the earlier constraints"
        condition = _clause(record.reconsider_if) or _clause(change)
        return f"This was previously rejected because {reason}. I am reconsidering it because {condition} now appears to be true."
```
Keep the rest of check_one unchanged.

tests/test_guard_reconsider.py:
- change the expected string in test_reconsider_text_format to `"This was previously rejected because we need sub-second latency. I am reconsidering it because X now appears to be true."`
- append:
```python
def test_reconsider_text_clean_grammar(ledger):
    record = Record(record_type=RecordType.REJECTION, canonical_idea="Copy trades of top-performing on-chain wallets",
        rejection_reason="Edge decays before execution.", reconsider_if="execution latency drops below 100ms.",
        status=Status.ACTIVE)
    text = Guard(ledger).reconsider_text(record, "our execution latency now drops below 100ms")
    assert text == ("This was previously rejected because edge decays before execution. "
                    "I am reconsidering it because execution latency drops below 100ms now appears to be true.")
    assert ".." not in text

def test_reconsider_text_keeps_acronym_and_uses_change(ledger):
    record = Record(record_type=RecordType.REJECTION, canonical_idea="poll the API", rejection_reason="API rate limits",
        status=Status.ACTIVE)
    text = Guard(ledger).reconsider_text(record, "Budget increased.")
    assert text == "This was previously rejected because API rate limits. I am reconsidering it because budget increased now appears to be true."

def test_extract_proposals_keeps_hyphenated_words():
    assert extract_proposals("How about we mirror the positions of top-performing whale addresses?") == ["How about we mirror the positions of top-performing whale addresses"]
    assert extract_proposals("- use websockets\n- try polling") == ["use websockets", "try polling"]
```
