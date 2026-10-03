import argparse
import json
import sys
from typing import List, Optional

from rmg.ledger import Ledger
from rmg import api
from rmg.models import Scope, RejectionType


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="RMG CLI")
    parser.add_argument("--db", type=str, default=None, help="Path to the ledger database")
    
    subparsers = parser.add_subparsers(dest="command")

    # reject
    p_reject = subparsers.add_parser("reject", help="Reject an idea")
    p_reject.add_argument("idea", type=str)
    p_reject.add_argument("--reason", type=str, required=True)
    p_reject.add_argument("--reconsider-if", type=str, default="")
    p_reject.add_argument("--alias", action="append", default=[])
    p_reject.add_argument("--category", type=str, default="")
    p_reject.add_argument("--scope", type=str, default="entire_concept")
    p_reject.add_argument("--rejection-type", type=str, default="hard")
    p_reject.add_argument("--evidence", type=str, default="")
    p_reject.add_argument("--original-discussion", type=str, default="")
    p_reject.add_argument("--replacement", type=str, default="")

    # reopen
    p_reopen = subparsers.add_parser("reopen", help="Reopen a rejection")
    p_reopen.add_argument("id", type=str)
    p_reopen.add_argument("--reason", type=str, required=True)

    # supersede
    p_supersede = subparsers.add_parser("supersede", help="Supersede a rejection")
    p_supersede.add_argument("id", type=str)
    p_supersede.add_argument("new_idea", type=str)

    # archive
    p_archive = subparsers.add_parser("archive", help="Archive a rejection")
    p_archive.add_argument("id", type=str)

    # conditions
    p_conditions = subparsers.add_parser("conditions", help="Update reconsider conditions")
    p_conditions.add_argument("id", type=str)
    p_conditions.add_argument("text", type=str)

    # check
    p_check = subparsers.add_parser("check", help="Check a candidate against rejections")
    p_check.add_argument("text", type=str)
    p_check.add_argument("--require", action="append", default=[], help="Requirement strings")

    # search
    p_search = subparsers.add_parser("search", help="Search rejections")
    p_search.add_argument("query", type=str)
    p_search.add_argument("--limit", type=int, default=10)

    # list
    subparsers.add_parser("list", help="List all rejections")

    # inject
    p_inject = subparsers.add_parser("inject", help="Generate injection block")
    p_inject.add_argument("task", type=str)
    p_inject.add_argument("--handoff", action="store_true")
    p_inject.add_argument("--approach", type=str, default="")

    # stats
    subparsers.add_parser("stats", help="Show statistics")

    # serve
    p_serve = subparsers.add_parser("serve", help="Start web server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    ledger = Ledger(args.db) if args.db else None

    try:
        if args.command == "reject":
            scope_map = {
                "entire_concept": Scope.ENTIRE_CONCEPT,
            }
            type_map = {
                "hard": RejectionType.HARD,
                "conditional": RejectionType.CONDITIONAL,
            }
            
            record = api.reject(
                idea=args.idea,
                reason=args.reason,
                aliases=args.alias or None,
                category=args.category,
                scope=scope_map.get(args.scope, Scope.ENTIRE_CONCEPT),
                rejection_type=type_map.get(args.rejection_type, RejectionType.HARD),
                reconsider_if=args.reconsider_if,
                evidence=args.evidence,
                original_discussion=args.original_discussion,
                replacement=args.replacement,
                ledger=ledger
            )
            print(record.id)
            
        elif args.command == "reopen":
            api.reopen(args.id, args.reason, ledger=ledger)
            
        elif args.command == "supersede":
            api.supersede(args.id, args.new_idea, ledger=ledger)
            
        elif args.command == "archive":
            api.archive(args.id, ledger=ledger)
            
        elif args.command == "conditions":
            api.update_conditions(args.id, args.text, ledger=ledger)
            
        elif args.command == "check":
            context = None
            if args.require:
                context = {"requirements": args.require}
            results = api.check(args.text, context=context, ledger=ledger)
            print(json.dumps(results, indent=2))
            
        elif args.command == "search":
            records = api.search_rejections(args.query, limit=args.limit, ledger=ledger)
            for r in records:
                print(f"{r.id} {r.canonical_idea}")
                
        elif args.command == "list":
            l = ledger or api.get_ledger()
            records = l.all()
            for r in records:
                date_str = r.rejected_at[:10] if r.rejected_at else "unknown"
                print(f"{r.id} {r.status.value} {date_str} {r.canonical_idea}")
                
        elif args.command == "inject":
            from rmg.inject import compaction_block, handoff_block
            l = ledger or api.get_ledger()
            if args.handoff:
                print(handoff_block(l, args.task, current_approach=args.approach))
            else:
                print(compaction_block(l, args.task))
                
        elif args.command == "stats":
            try:
                from rmg.analytics import print_dashboard
                print_dashboard(ledger or api.get_ledger())
            except ImportError:
                print("not available yet")
                
        elif args.command == "serve":
            try:
                from rmg.web import serve
                print(f"Serving on http://{args.host}:{args.port}")
                serve(ledger or api.get_ledger(), host=args.host, port=args.port)
            except ImportError:
                print("not available yet")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if ledger:
            ledger.close()

    return 0
