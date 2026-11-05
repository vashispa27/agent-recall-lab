import argparse
import json
from pathlib import Path

from recall_lab.adapters import load_native_trace
from recall_lab.capture import load_codex_export
from recall_lab.core import Store, load_trace


def main():
    parser = argparse.ArgumentParser(description="Inspectable agent memory baseline")
    parser.add_argument("--db", type=Path, default=Path(".recall/memory.db"))
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("paths", nargs="+", type=Path)
    ingest.add_argument("--format", choices=["canonical", "claude", "codex"], default="canonical")
    capture = commands.add_parser("capture", help="Import one saved Codex exec JSONL export")
    capture.add_argument("path", type=Path)
    capture.add_argument("--project", required=True)
    capture.add_argument("--correction", action="append", default=[], metavar="ITEM_ID")
    capture.add_argument("--synthetic", action="store_true", help="Label invented fixture input")
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
    revise = commands.add_parser("revise")
    revise.add_argument("id")
    revise.add_argument("--project", required=True)
    revise.add_argument("--body", required=True)
    revise.add_argument("--applicability", required=True)
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
        elif args.command == "capture":
            try:
                trace = load_codex_export(args.path, args.project, args.correction, args.synthetic)
                result = {"inserted": int(store.ingest(trace))}
            except (OSError, ValueError, RecursionError) as error:
                capture.error(f"Capture rejected ({type(error).__name__}). See docs/capture.md.")
        elif args.command == "distill":
            result = {"candidates_created": store.distill()}
        elif args.command == "list":
            result = store.list_memories(args.state)
        elif args.command == "show":
            result = store.inspect_memory(args.id, args.project)
        elif args.command == "revise":
            result = {"id": store.revise(args.id, args.project, args.body, args.applicability)}
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
