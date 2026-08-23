"""Command-line interface for File Task Bus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bus import LANES, TaskBus


def json_object(value: str) -> dict:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return parsed


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="file-task-bus")
    root.add_argument("--root", default=".task-bus", help="bus directory (default: .task-bus)")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="create lifecycle folders")

    submit = commands.add_parser("submit", help="submit a task")
    submit.add_argument("title")
    submit.add_argument("--payload", type=json_object, default={})
    submit.add_argument("--id")
    submit.add_argument("--created-by", default="human")
    submit.add_argument("--requires-approval", action="store_true")

    claim = commands.add_parser("claim", help="atomically claim the next task")
    claim.add_argument("--worker", required=True)

    complete = commands.add_parser("complete", help="finish a claimed task")
    complete.add_argument("task_id")
    complete.add_argument("--result", type=json_object, required=True)
    complete.add_argument("--actor", required=True)

    fail = commands.add_parser("fail", help="fail a claimed task")
    fail.add_argument("task_id")
    fail.add_argument("--error", required=True)
    fail.add_argument("--actor", required=True)

    approve = commands.add_parser("approve", help="approve a completed task")
    approve.add_argument("task_id")
    approve.add_argument("--reviewer", required=True)

    reject = commands.add_parser("reject", help="reject a completed task")
    reject.add_argument("task_id")
    reject.add_argument("--reviewer", required=True)
    reject.add_argument("--reason", required=True)

    listing = commands.add_parser("list", help="list tasks")
    listing.add_argument("--lane", choices=LANES)
    commands.add_parser("digest", help="show lane counts")

    watch = commands.add_parser("watch", help="print counts when they change")
    watch.add_argument("--interval", type=float, default=1.0)
    return root


def main(argv: list[str] | None = None) -> int:
    root = parser()
    args = root.parse_args(argv)
    bus = TaskBus(Path(args.root))
    try:
        if args.command == "init":
            bus.init()
            output = {"root": str(bus.root), "lanes": list(LANES)}
        elif args.command == "submit":
            output = bus.submit(args.title, args.payload, task_id=args.id, created_by=args.created_by,
                                requires_approval=args.requires_approval)
        elif args.command == "claim":
            output = bus.claim_next(args.worker) or {"status": "empty"}
        elif args.command == "complete":
            output = bus.complete(args.task_id, args.result, args.actor)
        elif args.command == "fail":
            output = bus.fail(args.task_id, args.error, args.actor)
        elif args.command == "approve":
            output = bus.approve(args.task_id, args.reviewer)
        elif args.command == "reject":
            output = bus.reject(args.task_id, args.reviewer, args.reason)
        elif args.command == "list":
            output = bus.list(args.lane)
        elif args.command == "digest":
            output = bus.digest()
        else:
            try:
                for output in bus.watch(args.interval):
                    print(json.dumps(output, sort_keys=True), flush=True)
            except KeyboardInterrupt:
                return 0
            return 0
    except (ValueError, FileExistsError, json.JSONDecodeError) as error:
        root.error(str(error))
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0
