from typing import Dict, Any, List
from rmg.models import RecordType, Status
from rmg.ledger import Ledger

def metrics(ledger: Ledger) -> Dict[str, Any]:
    records = ledger.all()
    events = ledger.events()
    
    # 1. rejected_ideas_total
    rejected_ideas_total = sum(1 for r in records if r.record_type == RecordType.REJECTION)
    
    # 2. blocked_reproposals
    blocked_reproposals = sum(1 for e in events if e["kind"] == "block")
    
    # 3. warning_matches
    warning_matches = sum(1 for e in events if e["kind"] == "warn")
    
    # 4. reopened_ideas
    reopened_ideas = 0
    for r in records:
        if any(h.status == Status.REOPENED for h in r.status_history):
            reopened_ideas += 1
            
    # 5. most_repeated_rejection
    most_repeated_rejection = None
    max_reproposed = 0
    for r in records:
        if r.record_type == RecordType.REJECTION:
            if r.times_reproposed > max_reproposed:
                max_reproposed = r.times_reproposed
                most_repeated_rejection = r.canonical_idea
                
    # 6. agent_reproposal_rate
    check_events = sum(1 for e in events if e["kind"] == "check")
    if check_events > 0:
        agent_reproposal_rate = blocked_reproposals / check_events
    else:
        agent_reproposal_rate = 0.0
        
    # 7. false_positive_rate
    false_positive_events = sum(1 for e in events if e["kind"] == "false_positive")
    denominator = max(1, blocked_reproposals + warning_matches)
    false_positive_rate = false_positive_events / denominator
    
    return {
        "rejected_ideas_total": rejected_ideas_total,
        "blocked_reproposals": blocked_reproposals,
        "warning_matches": warning_matches,
        "reopened_ideas": reopened_ideas,
        "most_repeated_rejection": most_repeated_rejection,
        "agent_reproposal_rate": agent_reproposal_rate,
        "false_positive_rate": false_positive_rate
    }

def dashboard(ledger: Ledger) -> str:
    m = metrics(ledger)
    lines = []
    
    # Metric lines
    for key, value in m.items():
        # Handle None for most_repeated_rejection
        display_val = "None" if value is None else str(value)
        lines.append(f"{key:<26} {display_val}")
        
    lines.append("Top rejections by re-proposals:")
    
    # Get top 5 rejections by times_reproposed
    records = ledger.all(record_type=RecordType.REJECTION)
    sorted_records = sorted(records, key=lambda r: r.times_reproposed, reverse=True)
    
    for r in sorted_records[:5]:
        lines.append(f"  {r.times_reproposed:>3}  {r.canonical_idea}")
        
    return "\n".join(lines)

def print_dashboard(ledger: Ledger):
    print(dashboard(ledger))
