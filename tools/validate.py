"""Validate the independent domain skills, package structure and tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "cloudcodex-environment-discovery"
DOMAIN_SKILLS = {"legacy-discovery", "current-discovery"}


def validate_structure() -> None:
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    compat = json.loads(
        (PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
    )
    if manifest["name"] != PLUGIN.name:
        raise ValueError("Manifest identity does not match package directory")
    if manifest["version"] != compat["version"] or manifest["name"] != compat["name"]:
        raise ValueError("Portable and compatibility manifests do not match")
    if "skills" in manifest or "mcpServers" in manifest:
        raise ValueError("Portable manifest uses invalid top-level keys")
    interface = manifest["extensions"]["com.openai"]["interface"]
    if len(interface["shortDescription"]) > 30:
        raise ValueError("Plugin listing shortDescription exceeds 30 characters")
    prompt = interface["defaultPrompt"]
    if "$legacy-discovery" not in prompt or "$current-discovery" not in prompt:
        raise ValueError("Plugin entry point must describe both independent skills")

    skills = PLUGIN / "skills"
    installed_skills = {
        p.parent.name for p in skills.glob("*/SKILL.md")
    }
    if installed_skills != DOMAIN_SKILLS:
        raise ValueError(
            f"Expected exactly two independent skills: {installed_skills!r}"
        )
    for skill in DOMAIN_SKILLS:
        folder = skills / skill
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
        if f"name: {skill}" not in text:
            raise ValueError(f"Invalid YAML skill identity for {skill}")
        for relative in ("agents/openai.yaml", "references"):
            if not (folder / relative).exists():
                raise ValueError(f"Missing {skill}/{relative}")

    for rel in (
        ".app.json",
        ".codex-plugin/plugin.json",
        "optional/mcp.json",
        "runtime/server.py",
        "runtime/cli.py",
        "runtime/common/models.py",
        "runtime/common/matching.py",
        "runtime/common/protocols.py",
        "runtime/common/service.py",
        "runtime/common/snapshot.py",
        "runtime/legacy/provider.py",
        "runtime/legacy/api.py",
        "runtime/current/provider.py",
        "runtime/current/api.py",
    ):
        if not (PLUGIN / rel).is_file():
            raise ValueError(f"Required plugin source missing: {rel}")

    # Old mixed catalog modules and mandatory Root skill are forbidden.
    for obsolete in (
        "runtime/discovery",
        "skills/cloudcodex-environment-discovery",
    ):
        if (PLUGIN / obsolete).exists():
            raise ValueError(f"Obsolete mixed component remains: {obsolete}")

    if (PLUGIN / "mcp.json").exists():
        raise ValueError("Default installation must not auto-register MCP")
    mcp_config = json.loads((PLUGIN / "optional/mcp.json").read_text(encoding="utf-8"))
    mcp_entry = next(iter(mcp_config["mcpServers"].values()))
    if (mcp_entry.get("type") != "stdio"
            or "runtime/server.py" not in " ".join(mcp_entry.get("args", []))):
        raise ValueError("Invalid optional MCP template")
    for path in PLUGIN.rglob("*"):
        if path.name.casefold() in {".env", "auth.json", "credentials.json"}:
            raise ValueError("Credential-like file must not be included")
    if (ROOT / ".agents").exists():
        raise ValueError("GSM marketplace catalog must remain independent")

    # Provider-specific modules must not import each other.
    for domain, other in (("legacy", "current"), ("current", "legacy")):
        for name in ("provider.py", "api.py"):
            source = (PLUGIN / "runtime" / domain / name).read_text(encoding="utf-8")
            if f"from {other} " in source or f"import {other}" in source:
                raise ValueError(f"{domain} must not import {other}")


def main() -> int:
    validate_structure()
    total = 0
    success = True
    loader = unittest.TestLoader()
    for domain in ("common", "legacy", "current", "mcp"):
        suite = loader.discover(
            str(ROOT / "tests"), pattern=f"test_{domain}.py"
        )
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        total += result.testsRun
        success &= result.wasSuccessful()
        print(
            f"suite={domain} tests={result.testsRun} passed={result.wasSuccessful()}"
        )
    print(f"package_structure=ok tests_run={total} success={success}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
