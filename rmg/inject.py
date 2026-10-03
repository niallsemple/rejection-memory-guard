from typing import List, Optional
from rmg.models import Record
from rmg.ledger import Ledger
from rmg.similarity import similarity, concepts

def relevant_rejections(ledger: Ledger, task: str, limit: int = 8, min_sim: float = 0.15) -> List[Record]:
    """
    Find relevant rejections for a given task.
    """
    active = ledger.active()
    scored = []
    for r in active:
        match_text = r.match_text()
        sim = similarity(task, match_text)
        shared = concepts(task) & concepts(match_text)
        
        if sim >= min_sim or shared:
            score = sim + 0.2 * len(shared)
            scored.append((score, r))
            
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    return [r for _, r in scored[:limit]]

def _bullet(r: Record) -> str:
    """
    Format a record as a bullet point string.
    """
    # rejected_at is an ISO string, first 10 chars are YYYY-MM-DD
    date_str = r.rejected_at[:10] if r.rejected_at else "unknown"
    
    base = f"- [{r.id}] {r.canonical_idea} — rejected {date_str}: {r.rejection_reason}"
    
    if r.reconsider_if:
        base += f" (reconsider only if: {r.reconsider_if})"
        
    if r.fingerprint and r.fingerprint.replacement:
        base += f" -> use instead: {r.fingerprint.replacement}"
        
    return base

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
