"""Read-only CLI with explicit Legacy or Current selection.

Examples:
    python cli.py legacy list --pretty
    python cli.py current find --repository owner/repo --pretty
    python cli.py legacy find --repository owner/repo --snapshot path.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence


def make_service(cloud_type: str, snapshot: Optional[Path] = None):
    """Import only the requested provider; never query an implicit mixed catalog."""
    if cloud_type == "legacy":
        from legacy.api import build_legacy_service, build_legacy_snapshot_service
        return (
            build_legacy_snapshot_service(snapshot)
            if snapshot is not None else build_legacy_service()
        )
    if cloud_type == "current":
        from current.api import build_current_service, build_current_snapshot_service
        return (
            build_current_snapshot_service(snapshot)
            if snapshot is not None else build_current_service()
        )
    raise ValueError("cloud type must be legacy or current")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cloud_type", choices=["legacy", "current"])
    parser.add_argument("operation", choices=["list", "find", "get", "resolve"])
    parser.add_argument("--account")
    parser.add_argument("--repository")
    parser.add_argument("--name")
    parser.add_argument("--environment-id")
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        service = make_service(args.cloud_type, snapshot=args.snapshot)
        if args.operation == "list":
            output = service.list_environments(
                account=args.account, include_drafts=args.include_drafts
            )
        elif args.operation == "find":
            if not args.repository:
                parser.error("find requires --repository")
            output = service.find_environments(
                repository=args.repository, account=args.account,
                include_drafts=args.include_drafts,
            )
        elif args.operation == "get":
            if not args.environment_id:
                parser.error("get requires --environment-id")
            output = service.get_environment(
                environment_id=args.environment_id, account=args.account
            )
        else:
            output = service.resolve_environment(
                repository=args.repository, name=args.name,
                account=args.account, include_drafts=args.include_drafts,
            )
    except (ValueError, OSError, json.JSONDecodeError):
        print(json.dumps({
            "cloud_type": args.cloud_type,
            "status": "invalid_request",
            "catalog_complete": False,
            "warnings": ["Invalid catalog input or provider configuration"],
        }))
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
