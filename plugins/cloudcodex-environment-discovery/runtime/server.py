"""Optional MCP stdio server, implemented with the official MCP Python SDK.

Core skills/CLI remain Python 3.9+ and require no MCP process. This adapter needs
Python 3.10+ plus optional/requirements-mcp.txt. It is never auto-registered.
"""
import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from common.configuration import DiscoveryRuntime, load_configuration
from common.operation import Operation, OperationCancelled, OperationTimedOut, operation_scope

SERVER_NAME = "cloudcodex-environment-discovery"
VERSION = "0.3.0"
MAX_RESULT_BYTES = 1024 * 1024
TOOLS = {
    "list_legacy_environments": ("legacy", "list_environments"),
    "find_legacy_environments": ("legacy", "find_environments"),
    "get_legacy_environment": ("legacy", "get_environment"),
    "resolve_legacy_environment": ("legacy", "resolve_environment"),
    "list_current_environments": ("current", "list_environments"),
    "find_current_environments": ("current", "find_environments"),
    "get_current_environment": ("current", "get_environment"),
    "resolve_current_environment": ("current", "resolve_environment"),
}
ERROR_STATUSES = {"unavailable", "unauthorized", "forbidden", "approval_required", "invalid_response",
                  "invalid_request", "timeout", "cancelled", "not_verifiable", "response_too_large", "rate_limited"}


def tool_specs() -> list:
    """Explicit strict input/output contracts, independent of SDK import."""
    specs = []
    for name, (domain, operation) in TOOLS.items():
        properties = {"account": {"type": "string", "minLength": 1, "maxLength": 256}}
        required = []
        if operation != "get_environment":
            properties["include_drafts"] = {"type": "boolean", "default": False}
        if operation in {"find_environments", "resolve_environment"}:
            properties["repository"] = {"type": "string", "minLength": 1, "maxLength": 1024}
        if operation == "find_environments":
            required.append("repository")
        if operation == "get_environment":
            properties["environment_id"] = {"type": "string", "minLength": 1, "maxLength": 4096}
            required.append("environment_id")
        if operation == "resolve_environment":
            properties["name"] = {"type": "string", "minLength": 1, "maxLength": 4096}
        specs.append({
            "name": name,
            "description": (operation.replace("_", " ").capitalize() + " for " + domain
                            + " Codex Cloud only. Read-only; provenance and escalation trace included. "
                            "Unavailable is not an empty verified catalog."),
            "inputSchema": {"type": "object", "properties": properties,
                            "required": required, "additionalProperties": False},
            "outputSchema": {"type": "object", "required": ["cloud_type", "status", "catalog_complete"],
                             "properties": {"cloud_type": {"const": domain}, "status": {"type": "string"},
                                            "catalog_complete": {"type": "boolean"}},
                             "additionalProperties": True},
            "annotations": {"readOnlyHint": True, "destructiveHint": False,
                            "idempotentHint": True, "openWorldHint": True},
        })
    return specs


def build_server(runtime: Optional[DiscoveryRuntime] = None):
    """Use SDK lifecycle, version negotiation, notifications and cancellation."""
    import anyio
    from jsonschema import Draft202012Validator
    from mcp.server.lowlevel import Server
    from mcp.types import CallToolResult, TextContent, Tool

    runtime = runtime or DiscoveryRuntime()
    server = Server(SERVER_NAME, version=VERSION,
                    instructions="Read-only independent Legacy/Current discovery; no task creation or credential extraction.")
    definitions = {spec["name"]: Tool(**spec) for spec in tool_specs()}
    inputs = {name: Draft202012Validator(tool.inputSchema) for name, tool in definitions.items()}
    outputs = {name: Draft202012Validator(tool.outputSchema) for name, tool in definitions.items()}

    @server.list_tools()
    async def list_tools():
        return list(definitions.values())

    def result_for(data: dict, is_error: bool = False):
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
                              structuredContent=data, isError=is_error)

    # Use the SDK's JSON Schema dependency, but deliberately suppress raw input
    # values in its default validation errors: tool arguments can be sensitive.
    @server.call_tool(validate_input=False)
    async def call_tool(name: str, arguments: dict):
        if name not in TOOLS:
            return CallToolResult(content=[TextContent(type="text", text="Unknown discovery tool")], isError=True)
        domain, operation_name = TOOLS[name]
        if not inputs[name].is_valid(arguments):
            return result_for({"cloud_type": domain, "status": "invalid_request", "catalog_complete": False,
                               "warnings": ["Arguments do not match the read-only tool schema"]}, True)
        context = server.request_context
        progress_token = context.meta.progressToken if context.meta is not None else None
        count = 0

        async def progress(stage: str):
            nonlocal count
            count += 1
            if progress_token is not None:
                await context.session.send_progress_notification(progress_token, float(count), None, stage)

        def report(stage: str):
            anyio.from_thread.run(progress, stage)

        operation = Operation(timeout=runtime.timeout, progress=report)

        def execute():
            with operation_scope(operation):
                service = runtime.service(domain)
                return getattr(service, operation_name)(**arguments)

        try:
            data = await anyio.to_thread.run_sync(execute, abandon_on_cancel=True)
        except OperationTimedOut:
            data = {"cloud_type": domain, "status": "timeout", "catalog_complete": False}
        except OperationCancelled:
            data = {"cloud_type": domain, "status": "cancelled", "catalog_complete": False}
        except (ValueError, OSError, TypeError, RuntimeError):
            data = {"cloud_type": domain, "status": "invalid_response", "catalog_complete": False,
                    "warnings": ["Read-only adapter failed; raw host output was suppressed"]}
        except BaseException:
            operation.cancelled.set()
            raise  # SDK cancellation, not an authorization/retry signal.
        finally:
            operation.cancelled.set()
        if not outputs[name].is_valid(data):
            data = {"cloud_type": domain, "status": "invalid_response", "catalog_complete": False}
        if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > MAX_RESULT_BYTES:
            data = {"cloud_type": domain, "status": "response_too_large", "catalog_complete": False,
                    "warnings": ["Use an explicit narrower provider scope or CLI for this catalog"]}
        provider_status = data.get("provider", {}).get("status")
        return result_for(data, data.get("status") in ERROR_STATUSES or provider_status in ERROR_STATUSES)

    return server


async def run_stdio(runtime: DiscoveryRuntime) -> None:
    from mcp.server.stdio import stdio_server
    server = build_server(runtime)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Operator-controlled adapter configuration")
    args = parser.parse_args(argv)
    try:
        import anyio
        runtime = DiscoveryRuntime(load_configuration(args.config))
        logging.basicConfig(level=logging.ERROR)
        # SDK parser diagnostics may include invalid client input; keep them
        # out of logs. Public errors are structured and sanitized above.
        sdk_logger = logging.getLogger("mcp")
        sdk_logger.handlers = [logging.NullHandler()]
        sdk_logger.propagate = False
        anyio.run(run_stdio, runtime)
    except ImportError:
        import sys
        print("Optional MCP requires Python 3.10+ and optional/requirements-mcp.txt", file=sys.stderr)
        return 2
    except (ValueError, OSError, TypeError):
        import sys
        print("Invalid operator discovery configuration; no server started", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
