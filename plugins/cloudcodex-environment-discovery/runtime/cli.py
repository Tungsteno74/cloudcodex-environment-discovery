"""Read-only discovery CLI. No MCP dependency or implicit mixed Cloud catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from common.configuration import DiscoveryRuntime, load_configuration
from common.operation import Operation, OperationCancelled, OperationTimedOut, operation_scope
from common.service import EnvironmentDiscoveryService
from common.snapshot import SnapshotEnvironmentProvider


def make_service(
    cloud_type: str, snapshot: Optional[Path] = None, configuration: Optional[Path] = None
):
    if cloud_type not in {"legacy", "current"}:
        raise ValueError("Select exactly one Cloud generation")
    if snapshot is not None:
        return EnvironmentDiscoveryService(
            cloud_type,
            SnapshotEnvironmentProvider.from_file(cloud_type, snapshot),
        )
    return DiscoveryRuntime(load_configuration(configuration)).service(cloud_type)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cloud_type", choices=["legacy", "current"])
    parser.add_argument("operation", choices=["doctor", "list", "find", "get", "resolve"])
    parser.add_argument(
        "--config", type=Path, help="Operator-approved startup configuration, not credentials"
    )
    parser.add_argument("--account")
    parser.add_argument("--repository")
    parser.add_argument("--name")
    parser.add_argument("--environment-id")
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument(
        "--correlate-github",
        action="store_true",
        help="For list only: join the complete owned GitHub inventory without inventing Cloud IDs",
    )
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    if args.correlate_github and args.operation != "list":
        parser.error(
            "--correlate-github applies to list; find/resolve already verify the requested repository"
        )
    if args.operation == "find" and not args.repository:
        parser.error("find requires --repository")
    if args.operation == "get" and not args.environment_id:
        parser.error("get requires --environment-id")
    if args.snapshot is not None and args.config is not None:
        parser.error("--snapshot and --config describe separate sources; choose one")
    if args.operation == "doctor" and args.snapshot is not None:
        parser.error("doctor checks configured adapters, not an imported snapshot")
    code = 0
    try:
        runtime = DiscoveryRuntime(load_configuration(args.config))
        if args.operation == "doctor":
            result = runtime.doctor(args.cloud_type)
        else:
            service = (
                make_service(args.cloud_type, args.snapshot)
                if args.snapshot is not None
                else runtime.service(args.cloud_type)
            )
            with operation_scope(Operation(timeout=runtime.timeout)):
                if args.operation == "list":
                    result = service.list_environments(
                        args.account, args.include_drafts, args.correlate_github
                    )
                elif args.operation == "find":
                    result = service.find_environments(
                        args.repository, args.account, args.include_drafts
                    )
                elif args.operation == "get":
                    result = service.get_environment(args.environment_id, args.account)
                else:
                    result = service.resolve_environment(
                        args.repository, args.name, args.account, args.include_drafts
                    )
    except (OperationCancelled, KeyboardInterrupt):
        result = {"cloud_type": args.cloud_type, "status": "cancelled", "catalog_complete": False}
        code = 130
    except OperationTimedOut:
        result = {"cloud_type": args.cloud_type, "status": "timeout", "catalog_complete": False}
        code = 124
    except (ValueError, OSError, TypeError):
        result = {
            "cloud_type": args.cloud_type,
            "status": "invalid_request",
            "catalog_complete": False,
            "warnings": [
                "Invalid configuration, catalog input or provider response; no credentials were requested"
            ],
        }
        code = 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
