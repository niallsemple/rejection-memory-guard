import json
import os
import tempfile
from typing import Optional

from rmg import api
from rmg.inject import compaction_block
from rmg.ledger import Ledger


def run_demo(db_path: Optional[str] = None, verbose: bool = True) -> dict:
    if db_path is None:
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "demo.db")

    ledger = Ledger(db_path)

    if verbose:
        print("1. Ingesting session 1 conversation...")

    conv = [
        {
            "role": "assistant",
            "content": "I suggest we copy the trades of the most profitable wallets on-chain.",
        },
        {
            "role": "user",
            "content": "We already tried that, it didn't work — the edge decays before we can execute. Don't suggest that again. Only reconsider if our execution latency drops below 100ms.",
        },
    ]
    records = api.ingest(conv, ledger=ledger)
    assert records, "Ingest should return at least one record"

    if verbose:
        print("2. Generating compaction block...")

    summary = "Working on a Solana trading strategy; several ideas evaluated."
    injection = compaction_block(ledger, "improve the Solana trading strategy using top wallets")
    if verbose:
        print(f"Summary: {summary}")
        print(f"Injection:\n{injection}")

    if verbose:
        print("3. Checking reworded idea...")

    blocked = api.check("How about we mirror the positions of top-performing whale addresses?", ledger=ledger)[0]
    if verbose:
        print(json.dumps(blocked, indent=2))
        print(f"Reworded idea -> {blocked['decision']}")

    if verbose:
        print("4. False-positive check...")

    api.reject("poll the API every second", "rate limits", ledger=ledger)
    fallback = api.check("Use WebSockets with REST polling only as a fallback on disconnect", ledger=ledger)[0]
    if verbose:
        print(f"WebSocket with REST fallback -> {fallback['decision']}")

    if verbose:
        print("5. Reconsider case...")

    reconsider = api.check(
        "Let's copy the top wallets' trades again",
        context={"requirements": ["our execution latency now drops below 100ms"]},
        ledger=ledger,
    )[0]
    if verbose:
        print(f"Reconsider case -> {reconsider['decision']}: {reconsider['reason']}")

    return {
        "injection": injection,
        "summary": summary,
        "result": blocked,
        "fallback": fallback,
        "reconsider": reconsider,
        "record_id": records[0].id,
    }


if __name__ == "__main__":
    run_demo()
