Keep the reply short: use small SEARCH/REPLACE blocks on rmg/extract.py and tests/test_extract.py (do NOT rewrite whole files, do NOT touch the long regexes in _extract_named_idea). Do not edit any other file.

Step 13b: store a clean, concise canonical idea, rejection reason and reconsider condition in `rmg/extract.py`. Today the record stores the raw sentence ("I suggest we copy the trades of the most profitable wallets on-chain") and the whole raw user message as the reason. Rule-based, stdlib only, must work offline (RMG_OFFLINE=1, no network). Keep all existing tests passing except the one assertion changed below.

Add these module-level helpers (use `re`, `os`, `json`, `urllib.request`):

1. `PHRASE_MAP = [(r"\b(?:the\s+)?most profitable\b", "top-performing"), (r"\b(?:the\s+)?best[- ]performing\b", "top-performing"), (r"\bbefore we can execute\b", "before execution")]` and `_apply_phrase_map(text)` applying each with `re.sub(..., flags=re.IGNORECASE)`.
2. `LEAD_IN = re.compile(r"^(?:i\s+(?:suggest|propose|think|recommend)\s+(?:that\s+)?(?:we\s+)?(?:should\s+)?|how about\s+(?:we\s+)?|what about\s+|let'?s\s+|why don'?t we\s+|maybe\s+we\s+(?:could|should)\s+|we\s+(?:could|should|can)\s+)", re.IGNORECASE)`
3. `clean_idea(text) -> str`, in this order: take the first sentence (`re.split(r'(?<=[.!?])\s+', text.strip())[0]`); strip and rstrip ".!?,; "; remove LEAD_IN; `_apply_phrase_map`; move a trailing on-chain before the last noun: `re.sub(r"\b(\w+) on-chain$", r"on-chain \1", t)`; remove articles `re.sub(r"\b(?:the|a|an)\s+", "", t, flags=re.IGNORECASE)`; collapse whitespace; strip; uppercase only the first character (keep the rest as is). Never cut words off.
4. `BOILERPLATE = re.compile(r"(?:we\s+)?already tried(?:\s+(?:that|it))?|(?:didn'?t|did not) work|don'?t suggest (?:that|it|this) again|scrap (?:that|it|this)|ruled (?:that|it) out|move on|decided against(?: (?:that|it))?|that approach is dead|forget(?: about)?(?: (?:that|it))?|no more", re.IGNORECASE)`
   `FILLER = {"it", "that", "this", "we", "so", "and", "but", "because", "since", "as", "the", "then", "again", "please", "ok", "okay"}`
5. `clean_reason(content) -> str`: `pre = re.split(r"\b(?:only reconsider if|unless)\b", content, flags=re.IGNORECASE)[0]`; split `pre` into clauses with `re.split(r"[.;!?,]|\s[—–-]\s|—|–", pre)`. For each clause: `res = BOILERPLATE.sub(" ", clause)`; split res into words and drop leading words while `word.lower() in FILLER`; if words remain, `reason = " ".join(words)` and stop. If no clause has a remainder, use the first non-empty stripped clause, or "Rejected by user" if none. Then `_apply_phrase_map`, rstrip ".!?,; ", uppercase the first character.
6. `parse_reconsider_if(content) -> str`: `m = re.search(r"\b(?:only reconsider if|unless)\s+(.+)", content, re.IGNORECASE | re.DOTALL)`; return "" if no match; take `m.group(1)`, cut at the first `re.split(r"[.!?](?:\s|$)", ...)[0]`, strip, rstrip ".!?,; ", remove one leading "our " / "the " / "if " (case-insensitive), return it.
7. `_llm_refine(idea, reason, raw) -> Optional[tuple]`: return None if `os.environ.get("RMG_OFFLINE") == "1"`. Otherwise POST JSON to `os.environ.get("RMG_LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")` with `{"model": os.environ.get("RMG_LLM_MODEL", "qwen3.8-27b"), "temperature": 0, "max_tokens": 120, "chat_template_kwargs": {"enable_thinking": False}, "messages": [{"role": "user", "content": "Rewrite as JSON {\"idea\": short imperative idea name, max 8 words, \"reason\": short rejection reason, max 8 words}. Idea: " + idea + "\nReason: " + reason + "\nConversation: " + raw}]}` via urllib with timeout=20; find the first `\{.*\}` (re.DOTALL) in `choices[0].message.content`, json.loads it, return `(idea2, reason2)` only if both are non-empty strings under 80 chars. Any exception -> None.

In `extract_rejections`: after the idea is chosen (named idea or assistant fallback), set `idea = clean_idea(idea)`, `reason = clean_reason(content)`, `reconsider_if = parse_reconsider_if(content)` (CONDITIONAL when non-empty, replacing the old "only reconsider if"/"unless" searches; keep the FAILED_EXPERIMENT/PREFERENCE logic). Then `refined = _llm_refine(idea, reason, content)`; if refined, `idea, reason = refined`. Build the Record with `canonical_idea=idea`, `rejection_reason=reason`, `fingerprint=Fingerprint(mechanism=idea, why_failed=reason, conditions_to_reconsider=reconsider_if)`, `reconsider_if=reconsider_if`, and keep `original_discussion` as the raw "Assistant: ...\nUser: ..." text.

tests/test_extract.py changes:
- import: `from rmg.extract import extract_rejections, is_uncertain, find_rejection_phrase, clean_idea, clean_reason, parse_reconsider_if`
- add an autouse fixture after the imports:
```python
@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")
```
- in test_rejection_phrases replace the last assertion with `assert records[0].canonical_idea == "Poll API every second", f"{phrase}: {records[0].canonical_idea}"`
- append:
```python
DEMO = [
    {"role": "assistant", "content": "I suggest we copy the trades of the most profitable wallets on-chain."},
    {"role": "user", "content": "We already tried that, it didn't work — the edge decays before we can execute. Don't suggest that again. Only reconsider if our execution latency drops below 100ms."},
]

def test_clean_demo_record():
    r = extract_rejections(DEMO)[0]
    assert r.canonical_idea == "Copy trades of top-performing on-chain wallets"
    assert r.rejection_reason == "Edge decays before execution"
    assert r.reconsider_if == "execution latency drops below 100ms"
    assert r.rejection_type == RejectionType.CONDITIONAL
    assert r.fingerprint.why_failed == "Edge decays before execution"
    assert "Don't suggest that again" in r.original_discussion

def test_clean_idea():
    assert clean_idea("How about we mirror the positions of top-performing whale addresses?") == "Mirror positions of top-performing whale addresses"
    assert clean_idea("Let's poll the API every second.") == "Poll API every second"

def test_clean_reason():
    assert clean_reason("Too expensive.") == "Too expensive"
    assert clean_reason("Scrap that, too expensive.") == "Too expensive"
    assert clean_reason("We already tried that, it didn't work because the API rate limits us.") == "API rate limits us"
    assert clean_reason("Don't suggest that again.") == "Don't suggest that again"

def test_parse_reconsider_if():
    assert parse_reconsider_if("Only reconsider if our execution latency drops below 100ms.") == "execution latency drops below 100ms"
    assert parse_reconsider_if("rate limits, unless the budget increases") == "budget increases"
    assert parse_reconsider_if("too expensive") == ""
```
