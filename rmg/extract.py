import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone

from rmg.models import Record, Fingerprint, RejectionType, Status

# Patterns for detecting rejections
REJECTION_PATTERNS = [
    r"we already tried that",
    r"already tried",
    r"didn'?t work",
    r"did not work",
    r"don'?t suggest that again",
    r"scrap that",
    r"ruled (that|it) out",
    r"not profitable",
    r"too expensive",
    r"latency kills it",
    r"decided against",
    r"failed in testing",
    r"move on",
    r"that approach is dead",
    r"only reconsider if",
    r"no more",
    r"forget (about)?"
]

# Patterns for detecting uncertainty
UNCERTAINTY_PATTERNS = [
    r"not sure",
    r"maybe",
    r"let'?s think",
    r"another way\?",
    r"perhaps",
    r"might",
    r"I wonder"
]

# Pre-compile regexes for efficiency
_COMPILED_REJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in REJECTION_PATTERNS]
_COMPILED_UNCERTAINTY_PATTERNS = [re.compile(p, re.IGNORECASE) for p in UNCERTAINTY_PATTERNS]

def is_uncertain(text: str) -> bool:
    """Check if the text contains uncertainty markers."""
    for pattern in _COMPILED_UNCERTAINTY_PATTERNS:
        if pattern.search(text):
            return True
    return False

def find_rejection_phrase(text: str) -> Optional[str]:
    """Find the first matching rejection phrase in the text."""
    for pattern in _COMPILED_REJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None

def _is_hedged_rejection(text: str, rejection_match: re.Match) -> bool:
    """
    Check if a rejection phrase is hedged by an uncertainty word within 3 words before it.
    """
    start = rejection_match.start()
    # Get the substring before the match
    prefix = text[:start]
    # Split into words
    words = prefix.split()
    # Check the last 3 words
    last_words = words[-3:]
    last_words_str = " ".join(last_words).lower()
    
    # Check if any uncertainty pattern is in the last 3 words
    for pattern in _COMPILED_UNCERTAINTY_PATTERNS:
        if pattern.search(last_words_str):
            return True
    return False

def _extract_idea_from_assistant(message: str) -> str:
    """
    Extract the idea from an assistant message.
    Returns the first sentence stripped of trailing punctuation.
    """
    # Take the first sentence
    sentences = re.split(r'(?<=[.!?])\s+', message)
    if sentences:
        idea = sentences[0].strip()
        # Strip trailing punctuation
        idea = idea.rstrip('.!?')
        return idea
    return message.strip().rstrip('.!?')

def _extract_named_idea(user_message: str) -> Optional[str]:
    """
    Try to extract a named idea from the user message.
    Looks for patterns like "Scrap the X", "we already tried X".
    """
    # This is a heuristic. We look for noun phrases after rejection verbs.
    # For simplicity, we'll look for the object of the rejection.
    
    # Pattern: "scrap the [noun phrase]"
    match = re.search(r"scrap\s+(?:the\s+)?([a-zA-Z0-9\s]+?)(?:\s+idea|\s+approach|\s+plan|\s+method|\s+strategy|\s+solution|\s+technique|\s+design|\s+architecture|\s+implementation|\s+code|\s+feature|\s+function|\s+module|\s+component|\s+system|\s+service|\s+api|\s+endpoint|\s+database|\s+table|\s+query|\s+algorithm|\s+model|\s+training|\s+inference|\s+deployment|\s+infrastructure|\s+network|\s+server|\s+client|\s+frontend|\s+backend|\s+middleware|\s+proxy|\s+cache|\s+queue|\s+worker|\s+job|\s+task|\s+process|\s+thread|\s+coroutine|\s+async|\s+sync|\s+blocking|\s+non-blocking|\s+event|\s+signal|\s+message|\s+packet|\s+frame|\s+segment|\s+chunk|\s+block|\s+page|\s+line|\s+character|\s+byte|\s+bit|\s+word|\s+phrase|\s+sentence|\s+paragraph|\s+section|\s+chapter|\s+book|\s+document|\s+file|\s+folder|\s+directory|\s+path|\s+url|\s+uri|\s+domain|\s+host|\s+port|\s+socket|\s+connection|\s+session|\s+transaction|\s+commit|\s+rollback|\s+save|\s+load|\s+read|\s+write|\s+delete|\s+insert|\s+update|\s+select|\s+create|\s+drop|\s+alter|\s+truncate|\s+vacuum|\s+analyze|\s+optimize|\s+reindex|\s+backup|\s+restore|\s+migrate|\s+upgrade|\s+downgrade|\s+install|\s+uninstall|\s+configure|\s+setup|\s+teardown|\s+init|\s+destroy|\s+start|\s+stop|\s+pause|\s+resume|\s+restart|\s+reload|\s+refresh|\s+sync|\s+async|\s+await|\s+yield|\s+return|\s+break|\s+continue|\s+pass|\s+raise|\s+throw|\s+catch|\s+finally|\s+try|\s+except|\s+else|\s+elif|\s+if|\s+for|\s+while|\s+do|\s+switch|\s+case|\s+default|\s+break|\s+continue|\s+goto|\s+label|\s+function|\s+method|\s+class|\s+interface|\s+struct|\s+enum|\s+union|\s+typedef|\s+define|\s+include|\s+import|\s+export|\s+from|\s+as|\s+with|\s+without|\s+using|\s+use)", user_message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # Pattern: "we already tried [noun phrase]"
    match = re.search(r"we already tried\s+(?:the\s+)?([a-zA-Z0-9\s]+?)(?:\s+idea|\s+approach|\s+plan|\s+method|\s+strategy|\s+solution|\s+technique|\s+design|\s+architecture|\s+implementation|\s+code|\s+feature|\s+function|\s+module|\s+component|\s+system|\s+service|\s+api|\s+endpoint|\s+database|\s+table|\s+query|\s+algorithm|\s+model|\s+training|\s+inference|\s+deployment|\s+infrastructure|\s+network|\s+server|\s+client|\s+frontend|\s+backend|\s+middleware|\s+proxy|\s+cache|\s+queue|\s+worker|\s+job|\s+task|\s+process|\s+thread|\s+coroutine|\s+async|\s+sync|\s+blocking|\s+non-blocking|\s+event|\s+signal|\s+message|\s+packet|\s+frame|\s+segment|\s+chunk|\s+block|\s+page|\s+line|\s+character|\s+byte|\s+bit|\s+word|\s+phrase|\s+sentence|\s+paragraph|\s+section|\s+chapter|\s+book|\s+document|\s+file|\s+folder|\s+directory|\s+path|\s+url|\s+uri|\s+domain|\s+host|\s+port|\s+socket|\s+connection|\s+session|\s+transaction|\s+commit|\s+rollback|\s+save|\s+load|\s+read|\s+write|\s+delete|\s+insert|\s+update|\s+select|\s+create|\s+drop|\s+alter|\s+truncate|\s+vacuum|\s+analyze|\s+optimize|\s+reindex|\s+backup|\s+restore|\s+migrate|\s+upgrade|\s+downgrade|\s+install|\s+uninstall|\s+configure|\s+setup|\s+teardown|\s+init|\s+destroy|\s+start|\s+stop|\s+pause|\s+resume|\s+restart|\s+reload|\s+refresh|\s+sync|\s+async|\s+await|\s+yield|\s+return|\s+break|\s+continue|\s+pass|\s+raise|\s+throw|\s+catch|\s+finally|\s+try|\s+except|\s+else|\s+elif|\s+if|\s+for|\s+while|\s+do|\s+switch|\s+case|\s+default|\s+break|\s+continue|\s+goto|\s+label|\s+function|\s+method|\s+class|\s+interface|\s+struct|\s+enum|\s+union|\s+typedef|\s+define|\s+include|\s+import|\s+export|\s+from|\s+as|\s+with|\s+without|\s+using|\s+use)", user_message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    return None

def extract_rejections(messages: Union[List[Dict[str, str]], str], now: Optional[datetime] = None) -> List[Record]:
    """
    Extract rejections from a list of messages or a single string.
    """
    if now is None:
        now = datetime.now(timezone.utc)
        
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
        
    records = []
    last_assistant_message = ""
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "assistant":
            last_assistant_message = content
            continue
            
        if role != "user":
            continue
            
        # Check for uncertainty
        if is_uncertain(content):
            # Check if it's a hedged rejection
            rejection_match = None
            for pattern in _COMPILED_REJECTION_PATTERNS:
                m = pattern.search(content)
                if m:
                    rejection_match = m
                    break
                    
            if rejection_match and _is_hedged_rejection(content, rejection_match):
                # Hedged rejection, no record
                continue
            elif not rejection_match:
                # Pure uncertainty, no record
                continue
            else:
                # Rejection present but not hedged by uncertainty in the last 3 words?
                # The spec says: "If a message contains a rejection pattern AND an uncertainty word, still no record only when the rejection phrase itself is hedged"
                # So if it's not hedged, we should proceed?
                # "treat a rejection phrase preceded within 3 words by maybe/perhaps/not sure as hedged"
                # If it's not preceded within 3 words, it's not hedged.
                # So we proceed to create a record.
                pass
        
        # Find rejection phrase
        rejection_phrase = find_rejection_phrase(content)
        if not rejection_phrase:
            continue
            
        # Determine the idea
        idea = None
        # First try to extract from user message
        named_idea = _extract_named_idea(content)
        if named_idea:
            idea = named_idea
        else:
            # Fall back to assistant message
            if last_assistant_message:
                idea = _extract_idea_from_assistant(last_assistant_message)
            else:
                # No idea found, skip? Or use the rejection phrase?
                # Spec says: "The rejected idea is the most recent assistant proposal... or, if the user message itself names it... the named noun phrase."
                # If neither, maybe skip.
                continue
        
        if not idea:
            continue
            
        # Determine rejection type and reconsider_if
        rejection_type = RejectionType.HARD
        reconsider_if = ""
        
        # Check for "only reconsider if"
        match = re.search(r"only reconsider if\s+(.+)", content, re.IGNORECASE)
        if match:
            rejection_type = RejectionType.CONDITIONAL
            reconsider_if = match.group(1).strip()
            
        # Check for "unless"
        if not reconsider_if:
            match = re.search(r"unless\s+(.+)", content, re.IGNORECASE)
            if match:
                rejection_type = RejectionType.CONDITIONAL
                reconsider_if = match.group(1).strip()
                
        # Check for FAILED_EXPERIMENT
        if re.search(r"tried|failed in testing|didn'?t work|did not work", content, re.IGNORECASE):
            if rejection_type != RejectionType.CONDITIONAL: # CONDITIONAL takes precedence? Or maybe FAILED_EXPERIMENT is more specific?
                # Spec: "FAILED_EXPERIMENT for 'tried'/'failed in testing'/'didn't work'"
                # "CONDITIONAL with reconsider_if = text after 'only reconsider if' / 'unless'"
                # If both are present, which wins?
                # "only reconsider if" implies a condition for reconsideration, which fits CONDITIONAL.
                # "tried" implies it was tested and failed, which fits FAILED_EXPERIMENT.
                # Let's prioritize CONDITIONAL if "only reconsider if" is present, as it's more specific about the condition.
                # Otherwise, FAILED_EXPERIMENT.
                rejection_type = RejectionType.FAILED_EXPERIMENT
                
        # Check for PREFERENCE
        if re.search(r"I don'?t like", content, re.IGNORECASE):
            rejection_type = RejectionType.PREFERENCE
            
        # Create Record
        record = Record(
            canonical_idea=idea,
            original_discussion=f"Assistant: {last_assistant_message}\nUser: {content}",
            rejection_reason=content,
            fingerprint=Fingerprint(
                mechanism=idea,
                why_failed=content,
                conditions_to_reconsider=reconsider_if
            ),
            rejection_type=rejection_type,
            reconsider_if=reconsider_if,
            rejected_at=now.isoformat()
        )
        records.append(record)
        
    return records
