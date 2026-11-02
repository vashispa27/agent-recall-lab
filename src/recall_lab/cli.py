import argparse
import json
from pathlib import Path

from recall_lab.adapters import load_native_trace
from recall_lab.core import Store, load_trace


def main():
    parser = argparse.ArgumentParser(description="Inspectable agent memory baseline")
    parser.add_argument("--db", type=Path, default=Path(".recall/memory.db"))
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("paths", nargs="+", type=Path)
    ingest.add_argument("--format", choices=["canonical", "claude", "codex"], default="canonical")
    commands.add_parser("distill")
    listing = commands.add_parser("list")
    listing.add_argument(
        "--state", choices=["candidate", "approved", "rejected"], default="candidate"
    )
    show = commands.add_parser("show")
    show.add_argument("id")
    show.add_argument("--project", required=True)
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
            loader = (
                load_trace
                if args.format == "canonical"
                else (lambda path: load_native_trace(path, args.format))
            )
            result = {"inserted": store.ingest_batch(loader(path) for path in args.paths)}
        elif args.command == "distill":
            result = {"candidates_created": store.distill()}
        elif args.command == "list":
            result = store.list_memories(args.state)
        elif args.command == "show":
            result = store.inspect_memory(args.id, args.project)
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
