import pytest
from rmg.extract import extract_rejections, is_uncertain, find_rejection_phrase
from rmg.models import RejectionType

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
        assert records[0].canonical_idea == "I suggest we poll the API every second" or "poll the API every second" in records[0].canonical_idea.lower()

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
