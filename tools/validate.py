"""Validate package metadata and run all offline tests (no network required)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "cloudcodex-environment-discovery"


def validate_structure() -> None:
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    compatibility = json.loads(
        (PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
    )
    if manifest["name"] != PLUGIN.name:
        raise ValueError("Package directory does not match manifest name")
    if manifest["version"] != compatibility["version"]:
        raise ValueError("Compatibility manifest version drift")
    if manifest["name"] != compatibility["name"]:
        raise ValueError("Compatibility manifest identity drift")
    if "skills" in manifest or "mcpServers" in manifest:
        raise ValueError("Portable manifest has non-portable top-level keys")
    interface = manifest["extensions"]["com.openai"]["interface"]
    if len(interface["shortDescription"]) > 30:
        raise ValueError("Listing short description exceeds 30 characters")
    for relative in (
        ".app.json",
        "mcp.json",
        "runtime/server.py",
        "runtime/cli.py",
        "runtime/discovery/models.py",
        "runtime/discovery/providers.py",
        "runtime/discovery/service.py",
        "skills/cloudcodex-environment-discovery/SKILL.md",
        "skills/cloudcodex-environment-discovery/agents/openai.yaml",
        "skills/cloudcodex-environment-discovery/references/discovery-contract.md",
    ):
        if not (PLUGIN / relative).is_file():
            raise ValueError(f"Missing distributable file: {relative}")
    if (ROOT / ".agents").exists():
        raise ValueError("Marketplace catalog must remain in its own repository")
    for path in PLUGIN.rglob("*"):
        if path.name in {".env", "auth.json", "credentials.json"}:
            raise ValueError("Secret-like file found in plugin package")


def main() -> int:
    validate_structure()
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(f"package_structure=ok tests_run={result.testsRun} success={result.wasSuccessful()}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
