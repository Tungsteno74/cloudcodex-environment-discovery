"""Minimal read-only MCP stdio transport for discovery tools.

Run from the plugin's local runtime. No credentials, network calls or stdout
logging. This process is not automatically available to ChatGPT web/mobile.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, IO, Mapping, Optional

from discovery.api import build_default_facade

MAX_FRAME_BYTES = 1024 * 1024
SERVER_NAME = "codex-cloud-environment-discovery"
VERSION = "0.1.0"


def read_frame(input_stream: IO[bytes]) -> Optional[Dict[str, Any]]:
    length = None
    headers = 0
    while True:
        line = input_stream.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        headers += 1
        if headers > 24:
            raise ValueError("too many MCP headers")
        if line.lower().startswith(b"content-length:"):
            try:
                length = int(line.split(b":", 1)[1].strip())
            except ValueError as error:
                raise ValueError("invalid MCP length") from error

    if length is None or length <= 0 or length > MAX_FRAME_BYTES:
        raise ValueError("missing or excessive MCP length")
    raw = input_stream.read(length)
    if len(raw) != length:
        raise ValueError("truncated MCP frame")
    body = json.loads(raw.decode("utf-8"))
    if not isinstance(body, dict):
        raise ValueError("MCP request must be an object")
    return body


def write_frame(output_stream: IO[bytes], payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    output_stream.write(
        b"Content-Length: " + str(len(encoded)).encode("ascii")
        + b"\r\n\r\n" + encoded
    )
    output_stream.flush()


def tool_specs() -> list:
    return [
        {
            "name": "list_environments",
            "description": "Read-only inventory with provider availability and catalog completeness.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account": {"type": "string"},
                    "cloud_type": {"type": "string", "enum": ["all", "legacy", "current"]},
                    "include_drafts": {"type": "boolean"},
                },
            },
        },
        {
            "name": "find_environments",
            "description": "Find all environments for a verified GitHub repository association.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repository": {"type": "string"},
                    "account": {"type": "string"},
                    "cloud_type": {"type": "string", "enum": ["all", "legacy", "current"]},
                    "include_drafts": {"type": "boolean"},
                },
                "required": ["repository"],
            },
        },
        {
            "name": "get_environment",
            "description": "Get an environment by exact type and immutable ID, without creating tasks.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cloud_type": {"type": "string", "enum": ["legacy", "current"]},
                    "environment_id": {"type": "string"},
                    "account": {"type": "string"},
                },
                "required": ["cloud_type", "environment_id"],
            },
        },
        {
            "name": "resolve_environment",
            "description": "Select only a unique live, verified environment from a complete catalog.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repository": {"type": "string"},
                    "name": {"type": "string"},
                    "account": {"type": "string"},
                    "cloud_type": {"type": "string", "enum": ["all", "legacy", "current"]},
                    "include_drafts": {"type": "boolean"},
                },
            },
        },
    ]


def handle_request(
    message: Mapping[str, Any],
    facade: Any,
) -> Optional[Dict[str, Any]]:
    method = message.get("method")
    if not isinstance(method, str):
        return None
    if "id" not in message:  # JSON-RPC notification
        return None
    request_id = message["id"]
    try:
        if method == "initialize":
            params = message.get("params") or {}
            version = params.get("protocolVersion", "2024-11-05")
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
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            funcs = {
                "list_environments": facade.list_environments,
                "find_environments": facade.find_environments,
                "get_environment": facade.get_environment,
                "resolve_environment": facade.resolve_environment,
            }
            if tool_name not in funcs:
                raise KeyError("unknown discovery tool")
            data = funcs[tool_name](**arguments)
            result = {
                "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
                "structuredContent": data,
                "isError": False,
            }
        else:
            return {
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": "Method not found"},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except (ValueError, TypeError, KeyError) as error:
        # Do not report raw HTTP error bodies or secret-bearing call values.
        return {
            "jsonrpc": "2.0", "id": request_id,
            "error": {"code": -32602, "message": str(error)},
        }
    except Exception:
        return {
            "jsonrpc": "2.0", "id": request_id,
            "error": {"code": -32603, "message": "Internal read-only provider error"},
        }


def serve(input_stream: IO[bytes], output_stream: IO[bytes]) -> None:
    facade = build_default_facade()
    while True:
        try:
            message = read_frame(input_stream)
        except (ValueError, UnicodeError, json.JSONDecodeError):
            # Invalid frames have no reliable request ID. Stop safely.
            return
        if message is None:
            return
        reply = handle_request(message, facade)
        if reply is not None:
            write_frame(output_stream, reply)


if __name__ == "__main__":
    serve(sys.stdin.buffer, sys.stdout.buffer)
