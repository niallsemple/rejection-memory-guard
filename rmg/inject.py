from typing import List, Optional
from rmg.models import Record
from rmg.ledger import Ledger
from rmg.similarity import similarity, concepts, tokenize

GENERIC_TOKENS = {"use", "using", "work", "improv", "idea", "design", "build", "make", "add", "task", "plan", "approach", "strategy", "several", "evaluat", "system", "new", "get", "need"}

def relevant_rejections(ledger: Ledger, task: str, limit: int = 8, min_sim: float = 0.10) -> List[Record]:
    """
    Find relevant rejections for a given task.
    """
    active = ledger.active()
    scored = []
    for r in active:
        text = r.match_text()
        sim = similarity(task, text)
        shared = concepts(task) & concepts(text)
        shared_tokens = (set(tokenize(task)) & set(tokenize(text))) - GENERIC_TOKENS
        
        if sim >= min_sim or shared or shared_tokens:
            score = sim + 0.2 * len(shared) + 0.1 * len(shared_tokens)
            scored.append((score, r))
            
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    return [r for _, r in scored[:limit]]

def _strip_punct(s: str) -> str:
    return s.rstrip(".!? ")

def _bullet(r: Record) -> str:
    """
    Format a record as a bullet point string.
    """
    date_str = r.rejected_at[:10] if r.rejected_at else "unknown"
    reason = _strip_punct(r.rejection_reason)
    
    lines = [
        f"- {r.canonical_idea} [{r.id}, rejected {date_str}]",
        f"  Reason: {reason}"
    ]
    
    if r.reconsider_if:
        condition = _strip_punct(r.reconsider_if)
        lines.append(f"  Reconsider only if: {condition}")
        
    if r.fingerprint and r.fingerprint.replacement:
        replacement = _strip_punct(r.fingerprint.replacement)
        lines.append(f"  Use instead: {replacement}")
        
    return "\n".join(lines)

def compaction_block(ledger: Ledger, task: str, limit: int = 8) -> str:
    """
    Generate the compaction block string.
    """
    header = "REJECTED APPROACHES — DO NOT REPROPOSE"
    records = relevant_rejections(ledger, task, limit=limit)
    
    if not records:
        return f"{header}\n- (none relevant)"
        
    bullets = [_bullet(r) for r in records]
    return f"{header}\n" + "\n".join(bullets)

def handoff_block(ledger: Ledger, task: str, current_approach: str = "") -> str:
    """
    Generate the handoff block string.
    """
    records = relevant_rejections(ledger, task)
    
    if records:
        bullets = [_bullet(r) for r in records]
        rejections_str = "\n".join(bullets)
    else:
        rejections_str = "- none"
        
    approach_str = current_approach if current_approach else "(not decided)"
    
    return (
        "TASK:\n"
        f"{task}\n"
        "KNOWN REJECTIONS:\n"
        f"{rejections_str}\n"
        "CURRENT APPROACH:\n"
        f"{approach_str}"
    )
