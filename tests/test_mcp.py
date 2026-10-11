"""Read-only MCP protocol, lazy provider selection and plugin structure."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/cloudcodex-environment-discovery"
RUNTIME = PLUGIN / "runtime"
sys.path.insert(0, str(RUNTIME))

import server  # noqa: E402


def request(name, arguments=None):
    return {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


class FakeService:
    def __init__(self, cloud_type):
        self.cloud_type = cloud_type
    def list_environments(self, account=None, include_drafts=False):
        return {"cloud_type": self.cloud_type, "account": account,
                "status": "unavailable", "catalog_complete": False}
    def find_environments(self, repository, account=None, include_drafts=False):
        return {"cloud_type": self.cloud_type, "repository": repository,
                "status": "partial"}
    def get_environment(self, environment_id, account=None):
        return {"cloud_type": self.cloud_type, "environment_id": environment_id,
                "status": "not_verifiable"}
    def resolve_environment(self, repository=None, name=None,
                            account=None, include_drafts=False):
        return {"cloud_type": self.cloud_type, "status": "not_verifiable"}


class McpTests(unittest.TestCase):
    def test_initialize(self):
        out = server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        })
        self.assertEqual(out["result"]["protocolVersion"], "2025-03-26")

    def test_specs_are_exactly_eight_independent_tools(self):
        names = {entry["name"] for entry in server.tool_specs()}
        self.assertEqual(names, {
            "list_legacy_environments", "find_legacy_environments",
            "get_legacy_environment", "resolve_legacy_environment",
            "list_current_environments", "find_current_environments",
            "get_current_environment", "resolve_current_environment",
        })

    def test_no_generic_mixed_catalog_tool(self):
        names = {item["name"] for item in server.tool_specs()}
        self.assertNotIn("list_environments", names)
        self.assertNotIn("resolve_environment", names)

    def test_no_cloud_type_argument_exposed(self):
        for item in server.tool_specs():
            self.assertNotIn("cloud_type", item["inputSchema"]["properties"])
            self.assertFalse(item["inputSchema"]["additionalProperties"])

    def test_each_domain_is_dispatched_only_to_own_service(self):
        called = []
        def factory(domain):
            called.append(domain)
            return FakeService(domain)
        one = server.handle_request(
            request("list_current_environments"), factory
        )
        self.assertEqual(one["result"]["structuredContent"]["cloud_type"], "current")
        self.assertEqual(called, ["current"])

    def test_legacy_tool_dispatches_legacy_only(self):
        called = []
        def factory(domain):
            called.append(domain)
            return FakeService(domain)
        out = server.handle_request(
            request("find_legacy_environments", {"repository": "owner/repo"}),
            factory
        )
        self.assertEqual(out["result"]["structuredContent"]["cloud_type"], "legacy")
        self.assertEqual(called, ["legacy"])

    def test_get_current_is_specific(self):
        out = server.handle_request(
            request("get_current_environment", {"environment_id": "cfg-1"}),
            FakeService,
        )
        self.assertEqual(
            out["result"]["structuredContent"]["environment_id"], "cfg-1"
        )

    def test_resolve_legacy_is_specific(self):
        out = server.handle_request(
            request("resolve_legacy_environment", {"name": "Legacy"}),
            FakeService,
        )
        self.assertEqual(
            out["result"]["structuredContent"]["cloud_type"], "legacy"
        )

    def test_default_runtime_current_fails_closed(self):
        out = server.handle_request(request("list_current_environments"))
        self.assertFalse(out["result"]["structuredContent"]["catalog_complete"])

    def test_default_runtime_legacy_fails_closed(self):
        out = server.handle_request(request("list_legacy_environments"))
        self.assertFalse(out["result"]["structuredContent"]["catalog_complete"])

    def test_explicit_mixed_arg_rejected(self):
        out = server.handle_request(request(
            "list_current_environments", {"cloud_type": "all"}
        ), FakeService)
        self.assertEqual(out["error"]["code"], -32602)

    def test_unknown_arguments_rejected(self):
        out = server.handle_request(request(
            "list_legacy_environments", {"token": "dont-expose-this"}
        ), FakeService)
        self.assertEqual(out["error"]["code"], -32602)
        self.assertNotIn("dont-expose-this", str(out))

    def test_creating_environment_is_not_a_tool(self):
        out = server.handle_request(request("create_environment"), FakeService)
        self.assertEqual(out["error"]["code"], -32602)

    def test_notification_has_no_response(self):
        self.assertIsNone(server.handle_request({
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }))

    def test_unknown_method(self):
        out = server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "environments/create"
        })
        self.assertEqual(out["error"]["code"], -32601)

    def test_frame_roundtrip(self):
        stream = io.BytesIO()
        server.write_frame(stream, {"jsonrpc": "2.0", "id": 1})
        stream.seek(0)
        self.assertEqual(server.read_frame(stream)["id"], 1)

    def test_stdio_is_json_lines_not_content_length(self):
        stream = io.BytesIO()
        server.write_frame(stream, {"jsonrpc": "2.0", "id": 1})
        raw = stream.getvalue()
        self.assertTrue(raw.startswith(b"{"))
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(b"Content-Length", raw)

    def test_multiple_messages_from_same_stream(self):
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

    def test_oversize_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            server.read_frame(io.BytesIO(b"x" * (server.MAX_FRAME_BYTES + 2)))

    def test_invalid_json_rejected(self):
        with self.assertRaises(json.JSONDecodeError):
            server.read_frame(io.BytesIO(b"nope\n"))

    def test_selected_provider_is_loaded_lazily(self):
        source = (RUNTIME / "server.py").read_text(encoding="utf-8")
        self.assertIn("from current.api import build_current_service", source)
        self.assertIn("from legacy.api import build_legacy_service", source)
        self.assertIn('if cloud_type == "current":', source)

    def test_cli_requires_explicit_type(self):
        result = subprocess.run(
            [sys.executable, str(RUNTIME / "cli.py"), "list"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_current_cli_uses_only_current_type(self):
        result = subprocess.run(
            [sys.executable, str(RUNTIME / "cli.py"), "current", "list"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["cloud_type"], "current")

    def test_legacy_cli_uses_only_legacy_type(self):
        result = subprocess.run(
            [sys.executable, str(RUNTIME / "cli.py"), "legacy", "list"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["cloud_type"], "legacy")


class PluginTests(unittest.TestCase):
    def test_manifest_identity_and_version_consistent(self):
        portable = json.loads(
            (PLUGIN / "plugin.json").read_text(encoding="utf-8")
        )
        compat = json.loads(
            (PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual((portable["name"], portable["version"]),
                         (compat["name"], compat["version"]))
        self.assertEqual(portable["version"], server.VERSION)

    def test_exactly_two_domain_skills(self):
        folder = PLUGIN / "skills"
        skills = sorted(p.parent.name for p in folder.glob("*/SKILL.md"))
        self.assertEqual(skills, ["current-discovery", "legacy-discovery"])

    def test_no_obligatory_root_skill(self):
        self.assertFalse((PLUGIN / "skills/cloudcodex-environment-discovery").exists())

    def test_each_skill_has_matching_frontmatter(self):
        for name in ("current-discovery", "legacy-discovery"):
            path = PLUGIN / "skills" / name / "SKILL.md"
            body = path.read_text(encoding="utf-8")
            self.assertIn("name: " + name, body)
            self.assertTrue((path.parent / "agents/openai.yaml").exists())

    def test_manifest_directs_root_without_extra_skill(self):
        manifest = json.loads(
            (PLUGIN / "plugin.json").read_text(encoding="utf-8")
        )
        prompt = manifest["extensions"]["com.openai"]["interface"]["defaultPrompt"]
        self.assertIn("$legacy-discovery", prompt)
        self.assertIn("$current-discovery", prompt)

    def test_standard_package_does_not_register_mcp(self):
        self.assertFalse((PLUGIN / "mcp.json").exists())

    def test_optional_mcp_template_is_available(self):
        config = json.loads(
            (PLUGIN / "optional/mcp.json").read_text(encoding="utf-8")
        )
        entry = next(iter(config["mcpServers"].values()))
        self.assertEqual(entry["type"], "stdio")
        self.assertIn("PLUGIN_ROOT", " ".join(entry["args"]))
        self.assertTrue((RUNTIME / "server.py").is_file())

    def test_runtime_has_separate_provider_modules(self):
        self.assertTrue((RUNTIME / "legacy/provider.py").is_file())
        self.assertTrue((RUNTIME / "current/provider.py").is_file())
        self.assertFalse((RUNTIME / "discovery/providers.py").exists())

    def test_no_secret_files_packaged(self):
        filenames = {p.name.casefold() for p in PLUGIN.rglob("*") if p.is_file()}
        self.assertFalse(
            filenames.intersection({".env", "auth.json", "credentials.json"})
        )


if __name__ == "__main__":
    unittest.main()
