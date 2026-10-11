"""Offline/read-only CLI for Codex Cloud Environment Discovery."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from discovery.api import build_default_facade, build_snapshot_facade


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["list", "find", "get", "resolve"])
    parser.add_argument("--cloud-type", choices=["all", "legacy", "current"], default="all")
    parser.add_argument("--account")
    parser.add_argument("--repository")
    parser.add_argument("--name")
    parser.add_argument("--environment-id")
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument("--snapshot-legacy", type=Path)
    parser.add_argument("--snapshot-current", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.snapshot_legacy or args.snapshot_current:
            facade = build_snapshot_facade(
                legacy=args.snapshot_legacy,
                current=args.snapshot_current,
            )
        else:
            facade = build_default_facade()

        if args.operation == "list":
            result = facade.list_environments(
                account=args.account, cloud_type=args.cloud_type,
                include_drafts=args.include_drafts,
            )
        elif args.operation == "find":
            if not args.repository:
                parser.error("find requires --repository")
            result = facade.find_environments(
                repository=args.repository, account=args.account,
                cloud_type=args.cloud_type,
                include_drafts=args.include_drafts,
            )
        elif args.operation == "get":
            if not args.environment_id or args.cloud_type == "all":
                parser.error("get requires --environment-id and a specific --cloud-type")
            result = facade.get_environment(
                cloud_type=args.cloud_type, environment_id=args.environment_id,
                account=args.account,
            )
        else:
            result = facade.resolve_environment(
                repository=args.repository, name=args.name,
                cloud_type=args.cloud_type, account=args.account,
                include_drafts=args.include_drafts,
            )
    except (ValueError, OSError, json.JSONDecodeError):
        # Print a bounded generic diagnostic, not file contents or credentials.
        print(json.dumps({
            "status": "invalid_request",
            "catalog_complete": False,
            "warnings": ["Invalid input, snapshot or provider configuration"],
        }), file=sys.stdout)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
