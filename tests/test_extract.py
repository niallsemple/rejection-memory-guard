import pytest
from rmg.extract import extract_rejections, is_uncertain, find_rejection_phrase, clean_idea, clean_reason, parse_reconsider_if
from rmg.models import RejectionType

@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("RMG_OFFLINE", "1")

def test_rejection_phrases():
    phrases = [
        "we already tried that",
        "already tried",
        "didn't work",
        "did not work",
        "don't suggest that again",
        "scrap that",
        "ruled that out",
        "ruled it out",
        "not profitable",
        "too expensive",
        "latency kills it",
        "decided against",
        "failed in testing",
        "move on",
        "that approach is dead",
        "only reconsider if latency is under 50ms",
        "no more polling",
        "forget about polling"
    ]
    
    assistant_msg = {"role": "assistant", "content": "I suggest we poll the API every second."}
    
    for phrase in phrases:
        messages = [assistant_msg, {"role": "user", "content": phrase}]
        records = extract_rejections(messages)
        assert len(records) == 1, f"Expected 1 record for '{phrase}', got {len(records)}"
        assert records[0].canonical_idea, f"Expected non-empty canonical_idea for '{phrase}'"
        assert records[0].canonical_idea == "Poll API every second", f"{phrase}: {records[0].canonical_idea}"

def test_conditional_rejection():
    assistant_msg = {"role": "assistant", "content": "I suggest we poll the API every second."}
    user_msg = {"role": "user", "content": "only reconsider if latency is under 50ms"}
    messages = [assistant_msg, user_msg]
    records = extract_rejections(messages)
    assert len(records) == 1
    assert records[0].rejection_type == RejectionType.CONDITIONAL
    assert "latency" in records[0].reconsider_if

def test_uncertainty_no_records():
    uncertain_messages = [
        "not sure about that",
        "maybe",
        "let's think about it",
        "another way?"
    ]
    
    assistant_msg = {"role": "assistant", "content": "I suggest we poll the API every second."}
    
    for msg in uncertain_messages:
        messages = [assistant_msg, {"role": "user", "content": msg}]
        records = extract_rejections(messages)
        assert len(records) == 0, f"Expected 0 records for '{msg}', got {len(records)}"

def test_assistant_only_no_records():
    messages = [{"role": "assistant", "content": "I suggest we poll the API every second."}]
    records = extract_rejections(messages)
    assert len(records) == 0

def test_hedged_rejection_no_records():
    # "maybe scrap that?" should be hedged
    assistant_msg = {"role": "assistant", "content": "I suggest we poll the API every second."}
    user_msg = {"role": "user", "content": "maybe scrap that?"}
    messages = [assistant_msg, user_msg]
    records = extract_rejections(messages)
    assert len(records) == 0, f"Expected 0 records for hedged rejection, got {len(records)}"

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
