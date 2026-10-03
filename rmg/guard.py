import re
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable

from rmg.models import Record, Decision, Status
from rmg.ledger import Ledger
from rmg.similarity import similarity, concepts, Embedder

# Verbs that indicate a proposal
PROPOSAL_VERBS = {
    "use", "try", "poll", "build", "add", "switch", "copy", "mirror",
    "follow", "implement", "could", "should", "suggest", "propose",
    "let's", "how about", "consider", "maybe", "perhaps", "what about"
}

def extract_proposals(message: str) -> List[str]:
    """
    Split a candidate agent message into sentences/clauses and keep ones that look like proposals.
    """
    if not message:
        return []

    # Split on sentence terminators and newlines
    # We use a regex to split but keep the delimiters if we want, but here we just want the chunks
    # Split on . ! ? ; \n and bullet markers (-, *, •)
    # We'll split on any of these, treating them as boundaries
    # To handle "Let's" and "How about" which are phrases, we just check the start of the chunk
    
    # Simple split
    # Replace bullet markers with newlines to ensure they are treated as separators
    cleaned_message = re.sub(r'[-*•]\s*', '\n', message)
    
    # Split on sentence enders and newlines
    # We keep the delimiters in the split to potentially re-attach? No, usually proposals are self-contained.
    # But "Let's hit the REST endpoint once a second" is one sentence.
    # Let's split on [.!?;\n]
    parts = re.split(r'[\.\!\?;\n]+', cleaned_message)
    
    proposals = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Check if it looks like a proposal
        # Lowercase for checking
        lower_part = part.lower()
        
        # Check if it starts with or contains a proposal verb
        # The spec says: "contain verbs like ... or, if none match, all non-empty sentences"
        # It's safer to check if any of the verbs are present in the text, 
        # but usually proposals start with them. 
        # "Let's" is a phrase.
        
        is_proposal = False
        for verb in PROPOSAL_VERBS:
            # Check if the verb is in the text
            # Using word boundaries to avoid "use" matching "house"
            # But "let's" has an apostrophe.
            # Let's just do a simple substring check for phrases like "let's", "how about"
            # and word boundary for single words.
            if verb in ("let's", "how about"):
                if verb in lower_part:
                    is_proposal = True
                    break
            else:
                # Word boundary match
                if re.search(r'\b' + re.escape(verb) + r'\b', lower_part):
                    is_proposal = True
                    break
        
        if is_proposal:
            proposals.append(part)
            
    # If no proposals were found based on verbs, return all non-empty sentences
    if not proposals:
        for part in parts:
            part = part.strip()
            if part:
                proposals.append(part)
                
    return proposals


@dataclass
class GuardResult:
    candidate: str
    decision: Decision
    matched_rejection: Optional[Dict[str, str]]
    similarity: float
    reason: str
    conditions_changed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate": self.candidate,
            "decision": self.decision.value,
            "matched_rejection": self.matched_rejection,
            "similarity": self.similarity,
            "reason": self.reason,
            "conditions_changed": self.conditions_changed
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Guard:
    def __init__(self, ledger: Ledger, embedder: Optional[Embedder] = None, llm_judge: Optional[Callable] = None):
        self.ledger = ledger
        self.embedder = embedder
        self.llm_judge = llm_judge

    def check(self, message: str, context: Optional[str] = None) -> List[GuardResult]:
        proposals = extract_proposals(message)
        return [self.check_one(p, context) for p in proposals]

    def check_one(self, proposal: str, context: Optional[str] = None) -> GuardResult:
        # Get active rejections
        active_records = self.ledger.active()
        
        best_record: Optional[Record] = None
        best_sim = 0.0
        best_shared_concepts: set = set()
        best_alias_hit = False
        best_mech_sim = 0.0
        best_decision = Decision.ALLOW
        best_reason = "No matching rejection"
        best_conditions_changed = False

        for record in active_records:
            # 1. Similarity
            sim = similarity(proposal, record.match_text(), embedder=self.embedder)
            
            # 2. Rule signals
            shared_concepts = concepts(proposal) & concepts(record.match_text())
            
            # Alias hit
            alias_hit = False
            for alias in record.aliases:
                if alias and alias.lower() in proposal.lower():
                    alias_hit = True
                    break
            
            # Mechanism overlap
            mech_sim = 0.0
            if record.fingerprint.mechanism:
                mech_sim = similarity(proposal, record.fingerprint.mechanism, embedder=self.embedder)

            # Determine decision for this record
            # BLOCK requires (sim >= 0.45 AND (shared_concepts or alias_hit or mech_sim >= 0.4))
            # WARN when sim >= 0.3 or shared_concepts exist but BLOCK conditions are not met
            # Otherwise ALLOW
            
            decision = Decision.ALLOW
            reason = "No matching rejection"
            
            if sim >= 0.45 and (shared_concepts or alias_hit or mech_sim >= 0.4):
                decision = Decision.BLOCK
                reason = f"Previously rejected: {record.canonical_idea}. Reason: {record.rejection_reason}"
            elif sim >= 0.3 or shared_concepts:
                decision = Decision.WARN
                # Explain difference
                # "Similar to rejected '<idea>' but differs: ..."
                # Listing concepts present in only one side
                prop_concepts = concepts(proposal)
                rec_concepts = concepts(record.match_text())
                diff_concepts = prop_concepts.symmetric_difference(rec_concepts)
                diff_str = ", ".join(sorted(diff_concepts)) if diff_concepts else "minor details"
                reason = f"Similar to rejected '{record.canonical_idea}' but differs: {diff_str}"
            
            # Optional LLM Judge
            if self.llm_judge:
                judge_result = self.llm_judge(proposal, record)
                if judge_result:
                    if judge_result == "BLOCK":
                        decision = Decision.BLOCK
                        reason = f"LLM Judge: BLOCK. Previously rejected: {record.canonical_idea}."
                    elif judge_result == "WARN":
                        if decision == Decision.BLOCK:
                            decision = Decision.WARN
                            reason = f"LLM Judge: WARN. Similar to rejected '{record.canonical_idea}'."
                    elif judge_result == "ALLOW":
                        if decision == Decision.BLOCK:
                            decision = Decision.WARN # Downgrade BLOCK to WARN? Or ALLOW?
                            # Spec: "downgrade or confirm a BLOCK"
                            # Usually downgrade means BLOCK -> WARN.
                            # If it was WARN, keep WARN? Or ALLOW?
                            # Let's assume it can downgrade BLOCK to WARN, or confirm.
                            # If it says ALLOW, and we had BLOCK, we downgrade to WARN? 
                            # "downgrade or confirm a BLOCK" implies it can change BLOCK to something else.
                            # Let's stick to: if judge says ALLOW, and we had BLOCK, we make it WARN (safe side) or ALLOW?
                            # The spec says "downgrade or confirm". Downgrading BLOCK usually means to WARN.
                            # If it says ALLOW, maybe it means "Allow this".
                            # Let's assume ALLOW means ALLOW.
                            decision = Decision.ALLOW
                            reason = f"LLM Judge: ALLOW."
            
            # Track best match
            # We want the "best" matching record. 
            # Usually highest similarity.
            # If similarity is same, maybe prefer BLOCK over WARN?
            # Let's just use similarity as the primary metric for "best".
            if sim > best_sim:
                best_sim = sim
                best_record = record
                best_shared_concepts = shared_concepts
                best_alias_hit = alias_hit
                best_mech_sim = mech_sim
                best_decision = decision
                best_reason = reason
                best_conditions_changed = False # Default, could be updated by context logic later if implemented

        # Apply side effects for the best match
        if best_record:
            if best_decision == Decision.BLOCK:
                self.ledger.increment_reproposal(best_record.id)
                self.ledger.log_event("block", best_record.id)
            elif best_decision == Decision.WARN:
                self.ledger.log_event("warn", best_record.id)
            
            matched_rejection_dict = {
                "id": best_record.id,
                "canonical_idea": best_record.canonical_idea,
                "rejection_reason": best_record.rejection_reason
            }
        else:
            matched_rejection_dict = None

        return GuardResult(
            candidate=proposal,
            decision=best_decision,
            matched_rejection=matched_rejection_dict,
            similarity=best_sim,
            reason=best_reason,
            conditions_changed=best_conditions_changed
        )
