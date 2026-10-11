"""Independent Legacy/Current read-only MCP stdio server.

The MCP tool name determines the provider; there is no implicit mixed list.
Each provider is imported lazily so Legacy can be retired without modifying
Current's implementation. This process never extracts credentials.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, IO, Mapping, Optional, Tuple

MAX_FRAME_BYTES = 1024 * 1024
SERVER_NAME = "cloudcodex-environment-discovery"
VERSION = "0.2.1"

# Every externally callable method targets exactly one Cloud generation.
# No generic "all" or cross-provider catalog operation is exposed.
TOOLS: Dict[str, Tuple[str, str]] = {
    "list_legacy_environments": ("legacy", "list_environments"),
    "find_legacy_environments": ("legacy", "find_environments"),
    "get_legacy_environment": ("legacy", "get_environment"),
    "resolve_legacy_environment": ("legacy", "resolve_environment"),
    "list_current_environments": ("current", "list_environments"),
    "find_current_environments": ("current", "find_environments"),
    "get_current_environment": ("current", "get_environment"),
    "resolve_current_environment": ("current", "resolve_environment"),
}


def make_default_service(cloud_type: str) -> Any:
    """Load only the selected provider implementation."""
    if cloud_type == "legacy":
        from legacy.api import build_legacy_service
        return build_legacy_service()
    if cloud_type == "current":
        from current.api import build_current_service
        return build_current_service()
    raise ValueError("unsupported cloud type")


def read_frame(input_stream: IO[bytes]) -> Optional[Dict[str, Any]]:
    """Read one newline-delimited JSON-RPC object; bounded for safety."""
    raw = input_stream.readline(MAX_FRAME_BYTES + 2)
    if not raw:
        return None
    if len(raw) > MAX_FRAME_BYTES + 1 or not raw.endswith(b"\n"):
        raise ValueError("invalid or oversized MCP message")
    message = json.loads(raw.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("MCP message must be a JSON object")
    return message


def write_frame(output_stream: IO[bytes], payload: Mapping[str, Any]) -> None:
    raw = json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if len(raw) > MAX_FRAME_BYTES:
        raise ValueError("MCP response exceeds maximum size")
    output_stream.write(raw + b"\n")
    output_stream.flush()


def tool_specs() -> list:
    """Advertise exactly eight domain-specific tools."""
    operations = {
        "list": (
            "List existing {domain} Cloud environments with completeness and provenance.",
            {},
            [],
        ),
        "find": (
            "Find existing {domain} Cloud environments by explicit repository identity.",
            {"repository": {"type": "string"}},
            ["repository"],
        ),
        "get": (
            "Read an existing {domain} Cloud environment by immutable ID.",
            {"environment_id": {"type": "string"}},
            ["environment_id"],
        ),
        "resolve": (
            "Resolve only one live, verified {domain} Cloud environment.",
            {"repository": {"type": "string"}, "name": {"type": "string"}},
            [],
        ),
    }
    names = {
        "list": "list_{domain}_environments",
        "find": "find_{domain}_environments",
        "get": "get_{domain}_environment",
        "resolve": "resolve_{domain}_environment",
    }
    specs = []
    for domain in ("legacy", "current"):
        for operation in ("list", "find", "get", "resolve"):
            description, properties, required = operations[operation]
            schema_properties = dict(properties)
            schema_properties["account"] = {"type": "string"}
            if operation != "get":
                schema_properties["include_drafts"] = {"type": "boolean"}
            specs.append({
                "name": names[operation].format(domain=domain),
                "description": description.format(domain=domain),
                "inputSchema": {
                    "type": "object",
                    "properties": schema_properties,
                    "required": required,
                    "additionalProperties": False,
                },
            })
    assert {spec["name"] for spec in specs} == set(TOOLS)
    return specs


def handle_request(
    message: Mapping[str, Any],
    service_factory: Optional[Callable[[str], Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Handle one JSON-RPC request with a lazily loaded target service."""
    method = message.get("method")
    if not isinstance(method, str) or "id" not in message:
        return None  # Notification, not a command requiring response.
    request_id = message["id"]
    try:
        if method == "initialize":
            params = message.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError("invalid initialize arguments")
            version = params.get("protocolVersion") or "2024-11-05"
            result: Dict[str, Any] = {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": VERSION},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": tool_specs()}
        elif method == "tools/call":
            params = message.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError("invalid tool call arguments")
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            if tool_name not in TOOLS:
                raise KeyError("unknown discovery tool")
            if "cloud_type" in arguments:
                raise ValueError("cloud_type is fixed by the selected tool")
            allowed = next(
                spec["inputSchema"]["properties"]
                for spec in tool_specs() if spec["name"] == tool_name
            )
            if any(key not in allowed for key in arguments):
                raise ValueError("unexpected discovery tool argument")
            domain, method_name = TOOLS[tool_name]
            factory = service_factory or make_default_service
            service = factory(domain)
            if service.cloud_type != domain:
                raise ValueError("provider identity mismatch")
            data = getattr(service, method_name)(**arguments)
            result = {
                "content": [{
                    "type": "text",
                    "text": json.dumps(data, ensure_ascii=False),
                }],
                "structuredContent": data,
                "isError": False,
            }
        else:
            return {
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": "Method not found"},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except (ValueError, TypeError, KeyError):
        # No request args, paths or raw HTTP error bodies in exceptions.
        return {
            "jsonrpc": "2.0", "id": request_id,
            "error": {"code": -32602, "message": "Invalid discovery request"},
        }
    except Exception:
        return {
            "jsonrpc": "2.0", "id": request_id,
            "error": {"code": -32603, "message": "Read-only provider error"},
        }


def serve(input_stream: IO[bytes], output_stream: IO[bytes]) -> None:
    while True:
        try:
            message = read_frame(input_stream)
        except (ValueError, UnicodeError, json.JSONDecodeError):
            return  # Invalid framing has no safe request ID.
        if message is None:
            return
        response = handle_request(message)
        if response is not None:
            write_frame(output_stream, response)


if __name__ == "__main__":
    serve(sys.stdin.buffer, sys.stdout.buffer)
