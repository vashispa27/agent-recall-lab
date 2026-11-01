import argparse
import json
from pathlib import Path

from recall_lab.core import Store, load_trace


def main():
    parser = argparse.ArgumentParser(description="Inspectable agent memory baseline")
    parser.add_argument("--db", type=Path, default=Path(".recall/memory.db"))
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("paths", nargs="+", type=Path)
    commands.add_parser("distill")
    listing = commands.add_parser("list")
    listing.add_argument(
        "--state", choices=["candidate", "approved", "rejected"], default="candidate"
    )
    review = commands.add_parser("review")
    review.add_argument("id")
    review.add_argument("decision", choices=["approved", "rejected"])
    search = commands.add_parser("search")
    search.add_argument("--project", required=True)
    search.add_argument("query")
    args = parser.parse_args()
    store = Store(args.db)
    try:
        if args.command == "ingest":
            result = {"inserted": sum(store.ingest(load_trace(path)) for path in args.paths)}
        elif args.command == "distill":
            result = {"candidates_created": store.distill()}
        elif args.command == "list":
            result = store.list_memories(args.state)
        elif args.command == "review":
            store.review(args.id, args.decision)
            result = {"id": args.id, "state": args.decision}
        else:
            result = store.search(args.project, args.query)
        print(json.dumps(result, indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
