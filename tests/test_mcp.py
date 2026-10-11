"""MCP transport and standalone package regression tests."""
from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "cloudcodex-environment-discovery"
sys.path.insert(0, str(PLUGIN / "runtime"))

import server  # noqa: E402
from discovery.api import build_default_facade  # noqa: E402


def request(name, arguments=None, request_id=1):
    return {
        "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


class McpTests(unittest.TestCase):
    def test_initialize(self):
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        }, None)
        self.assertEqual(result["result"]["protocolVersion"], "2025-03-26")

    def test_methods_are_read_only(self):
        tools = {item["name"] for item in server.tool_specs()}
        self.assertEqual(tools, {
            "list_environments", "find_environments",
            "get_environment", "resolve_environment",
        })

    def test_notifications_ignore_idless_call(self):
        self.assertIsNone(server.handle_request({
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }, None))

    def test_unknown_method(self):
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 7, "method": "environments/create"
        }, None)
        self.assertEqual(result["error"]["code"], -32601)

    def test_cannot_call_unlisted_write_tool(self):
        result = server.handle_request(
            request("create_environment"), build_default_facade()
        )
        self.assertIn("error", result)

    def test_mcp_catalog_unavailable_is_explicit(self):
        result = server.handle_request(
            request("list_environments"), build_default_facade()
        )
        body = result["result"]["structuredContent"]
        self.assertFalse(body["catalog_complete"])
        self.assertEqual(len(body["providers"]), 2)

    def test_valid_mcp_tool_errors_are_bounded(self):
        result = server.handle_request(
            request("find_environments", {"repository": "bad"}),
            build_default_facade()
        )
        self.assertEqual(result["error"]["code"], -32602)

    def test_frame_roundtrip(self):
        stream = io.BytesIO()
        server.write_frame(stream, {"method": "ping", "id": 1})
        stream.seek(0)
        self.assertEqual(server.read_frame(stream)["id"], 1)

    def test_multiple_requests(self):
        stream = io.BytesIO()
        server.write_frame(stream, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        })
        server.write_frame(stream, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        })
        stream.seek(0)
        output = io.BytesIO()
        server.serve(stream, output)
        output.seek(0)
        self.assertEqual(server.read_frame(output)["id"], 1)
        self.assertEqual(server.read_frame(output)["id"], 2)

    def test_mcp_stdio_uses_newline_delimited_json(self):
        stream = io.BytesIO()
        server.write_frame(stream, {"jsonrpc": "2.0", "id": 1, "result": {}})
        encoded = stream.getvalue()
        self.assertTrue(encoded.startswith(b"{"))
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertNotIn(b"Content-Length", encoded)

    def test_reject_oversize_frame(self):
        with self.assertRaises(ValueError):
            server.read_frame(io.BytesIO(b"x" * (server.MAX_FRAME_BYTES + 2)))

    def test_reject_invalid_json(self):
        with self.assertRaises(json.JSONDecodeError):
            server.read_frame(io.BytesIO(b"nope\n"))


class PackageTests(unittest.TestCase):
    def test_portable_manifest(self):
        obj = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(obj["name"], "cloudcodex-environment-discovery")
        self.assertNotIn("mcpServers", obj)
        self.assertNotIn("skills", obj)

    def test_legacy_manifest_matches(self):
        a = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        b = json.loads(
            (PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual((a["name"], a["version"]), (b["name"], b["version"]))

    def test_local_stdio_server_present(self):
        obj = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
        server_def = next(iter(obj["mcpServers"].values()))
        self.assertEqual(server_def["type"], "stdio")
        self.assertIn("PLUGIN_ROOT", " ".join(server_def["args"]))
        self.assertTrue((PLUGIN / "runtime/server.py").is_file())

    def test_skill_present(self):
        body = (
            PLUGIN / "skills/cloudcodex-environment-discovery/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("name: cloudcodex-environment-discovery", body)
        self.assertIn("Root", body)

    def test_short_description_limit(self):
        obj = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        short = obj["extensions"]["com.openai"]["interface"]["shortDescription"]
        self.assertLessEqual(len(short), 30)

    def test_no_embedded_marketplace(self):
        self.assertFalse((PLUGIN / ".agents/plugins/marketplace.json").exists())

    def test_no_credential_files_packaged(self):
        filenames = {p.name.lower() for p in PLUGIN.rglob("*") if p.is_file()}
        self.assertNotIn("auth.json", filenames)
        self.assertNotIn(".env", filenames)


if __name__ == "__main__":
    unittest.main()
