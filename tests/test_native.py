"""Native-selector parsing/navigation tests; no real account or CLI is invoked."""

from __future__ import annotations

from collections import deque
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "plugins/cloudcodex-environment-discovery/runtime"
sys.path.insert(0, str(RUNTIME))
from legacy.native_cli import NativeCliEnvironmentProvider, NativeCliSettings
from legacy.selector import parse_selector
from legacy.terminal import KEYS
from common.configuration import validate_configuration
from common.operation import Operation, OperationCancelled, operation_scope

A, B, C = "a" * 32, "b" * 32, "c" * 32


def frame(rows, selected="__global__", query="", include_global=True):
    width = 180
    result = [
        "╭" + "Select Environment".ljust(width, "─") + "╮",
        "│" + "Type to search, Enter select, Esc cancel".ljust(width) + "│",
        "│" + ("Search: " + query).ljust(width) + "│",
    ]
    if include_global:
        marker = "> " if selected == "__global__" else "  "
        result.append("│" + (marker + "All Environments (Global)").ljust(width) + "│")
    for identifier, label, repo in rows:
        text = ("> " if identifier == selected else "  ") + label + "  " + identifier
        if repo:
            text += "  " + repo
        result.append("│" + text.ljust(width) + "│")
    result += ["│" + " " * width + "│", "╰" + "─" * width + "╯"]
    return result


class ParserTests(unittest.TestCase):
    def test_extracts_immutable_ids_not_task_ids(self):
        page = parse_selector(frame([(A, "One", None), (B, "Two", None)]))
        self.assertEqual([row.environment_id for row in page.environments], [A, B])
        self.assertEqual(page.selected, "__global__")

    def test_repository_display_name_is_only_a_label(self):
        row = parse_selector(frame([(A, "owner/repo", None)])).environments[0]
        self.assertIsNone(row.repository)
        self.assertEqual(row.name, "owner/repo")

    def test_explicit_native_repo_hint_is_an_association(self):
        row = parse_selector(frame([(A, "Different label", "Owner/Repo")])).environments[0]
        self.assertEqual(row.repository, "owner/repo")

    def test_pin_label_removed_not_part_of_name(self):
        row = parse_selector(frame([(A, "Example  PINNED", None)])).environments[0]
        self.assertEqual(row.name, "Example")

    def test_selected_environment_does_not_need_enter(self):
        page = parse_selector(frame([(A, "One", None), (B, "Two", None)], selected=B))
        self.assertEqual(page.selected, B)

    def test_unrelated_task_screen_not_a_catalog(self):
        self.assertIsNone(parse_selector(["Cloud Tasks", "READY example", "o : Set Env"]))

    def test_loading_modal_is_not_empty(self):
        rows = frame([])
        rows[2] = rows[2].replace("Search:", "Loading environments")
        self.assertIsNone(parse_selector(rows))

    def test_filtered_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_selector(frame([(A, "One", None)], query="one"))

    def test_truncated_id_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_selector(frame([(A[:-1], "One", None)]))

    def test_ambiguous_id_in_label_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_selector(frame([(B, "Label " + A, None)]))

    def test_incomplete_border_waits(self):
        self.assertIsNone(parse_selector(frame([(A, "One", None)])[:-1]))

    def test_empty_selector_is_a_visual_observation_only(self):
        page = parse_selector(frame([]))
        self.assertEqual(page.environments, ())
        self.assertTrue(page.global_visible)

    def test_no_creation_or_apply_keys_exposed(self):
        self.assertEqual(set(KEYS), {"selector", "home", "end", "next_page", "escape", "quit"})
        self.assertNotIn("n", KEYS.values())
        self.assertNotIn("\r", KEYS.values())
        self.assertNotIn("\n", KEYS.values())
        self.assertNotIn("a", KEYS.values())


class FakeTerminal:
    def __init__(self, pages):
        self.pages = deque([["Cloud Tasks  o : Set Env"]] + pages)
        self.sent, self.closed = [], False

    def send(self, key):
        self.sent.append(key)

    def wait(self, predicate):
        while self.pages:
            result = predicate(self.pages.popleft())
            if result is not None:
                return result
        raise RuntimeError("fixture_output_exhausted")

    def close(self):
        self.closed = True


class NativeProviderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.executable = Path(self.directory.name) / (
            "codex.exe" if sys.platform == "win32" else "codex"
        )
        self.executable.write_bytes(b"fake binary never executed")
        self.settings = NativeCliSettings(
            str(self.executable), hashlib.sha256(self.executable.read_bytes()).hexdigest()
        )

    def tearDown(self):
        self.directory.cleanup()

    def provider(self, terminal, version="codex-cli 0.162.0", settings=None):
        return NativeCliEnvironmentProvider(
            settings or self.settings,
            terminal_factory=lambda *args: terminal,
            version_reader=lambda: version,
        )

    def test_small_catalog_returns_actual_rows_conservative_coverage(self):
        rows = [(A, "One", None), (B, "Two", None)]
        terminal = FakeTerminal([frame(rows), frame(rows, selected=B)])
        result = self.provider(terminal).list_environments()
        self.assertEqual(len(result.environments), 2)
        self.assertEqual(result.evidence, "live")
        self.assertTrue(result.coverage["visible_rows_complete"])
        self.assertFalse(result.catalog_complete)
        self.assertTrue(terminal.closed)
        self.assertEqual(terminal.sent, ["selector", "end"])

    def test_modal_initially_at_last_row_reanchors_before_enumeration(self):
        rows = [(A, "One", None), (B, "Two", None)]
        terminal = FakeTerminal([
            frame(rows, selected=B),
            frame(rows, selected="__global__"),
            frame(rows, selected=B),
        ])
        result = self.provider(terminal).list_environments()
        self.assertEqual({row.environment_id for row in result.environments}, {A, B})
        self.assertTrue(result.coverage["visible_rows_complete"])
        self.assertFalse(result.catalog_complete)
        self.assertEqual(terminal.sent, ["selector", "home", "end"])
        self.assertTrue(terminal.closed)

    def test_initially_scrolled_selector_does_not_omit_earlier_rows(self):
        terminal = FakeTerminal([
            frame([(C, "Three", None)], selected=C, include_global=False),
            frame([(A, "One", None)]),
            frame([(C, "Three", None)], selected=C, include_global=False),
            frame([(A, "One", None)]),
            frame([(A, "One", None), (B, "Two", None)], selected=B, include_global=False),
            frame([(B, "Two", None), (C, "Three", None)], selected=C, include_global=False),
        ])
        result = self.provider(terminal).list_environments()
        self.assertEqual({row.environment_id for row in result.environments}, {A, B, C})
        self.assertTrue(result.coverage["visible_rows_complete"])
        self.assertEqual(terminal.sent[:3], ["selector", "home", "end"])
        self.assertTrue(terminal.closed)

    def test_large_catalog_is_traversed_without_selecting_an_environment(self):
        terminal = FakeTerminal(
            [
                frame([(A, "One", None)]),
                frame([(C, "Three", None)], selected=C, include_global=False),
                frame([(A, "One", None)]),
                frame([(A, "One", None), (B, "Two", None)], selected=B, include_global=False),
                frame([(B, "Two", None), (C, "Three", None)], selected=C, include_global=False),
            ]
        )
        result = self.provider(terminal).list_environments()
        self.assertEqual({row.environment_id for row in result.environments}, {A, B, C})
        self.assertTrue(result.coverage["visible_rows_complete"])
        self.assertTrue(terminal.closed)
        self.assertNotIn("enter", terminal.sent)

    def test_page_limit_preserves_partial_rows(self):
        terminal = FakeTerminal(
            [
                frame([(A, "One", None)]),
                frame([(C, "Three", None)], selected=C),
                frame([(A, "One", None)]),
                frame([(B, "Two", None)], selected=B),
            ]
        )
        settings = NativeCliSettings(self.settings.executable, self.settings.sha256, max_pages=1)
        result = self.provider(terminal, settings=settings).list_environments()
        self.assertFalse(result.coverage["visible_rows_complete"])
        self.assertEqual(result.reason, "native_selector_page_limit")
        self.assertTrue(terminal.closed)

    def test_empty_visual_selector_cannot_prove_absence(self):
        terminal = FakeTerminal([frame([])])
        result = self.provider(terminal).list_environments()
        self.assertFalse(result.catalog_complete)
        self.assertEqual(result.status, "partial")
        self.assertTrue(terminal.closed)

    def test_version_probe_timeout_uses_structured_operation_timeout(self):
        from unittest.mock import patch
        from subprocess import TimeoutExpired
        from common.operation import OperationTimedOut

        terminal = FakeTerminal([])
        provider = NativeCliEnvironmentProvider(
            self.settings, terminal_factory=lambda *args: terminal
        )
        with patch(
            "legacy.native_cli.subprocess.run", side_effect=TimeoutExpired("codex --version", 5)
        ):
            with self.assertRaises(OperationTimedOut):
                provider.list_environments()
        self.assertEqual(terminal.sent, [])

    def test_unknown_client_version_not_silently_supported(self):
        terminal = FakeTerminal([])
        result = self.provider(terminal, version="codex-cli 9.9.9").list_environments()
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(terminal.sent, [])

    def test_cancellation_prevents_start(self):
        operation = Operation(5)
        operation.cancelled.set()
        with self.assertRaises(OperationCancelled), operation_scope(operation):
            self.provider(FakeTerminal([])).list_environments()

    def test_terminal_failure_does_not_leak_output(self):
        terminal = FakeTerminal([["unexpected screen"]])
        result = self.provider(terminal).list_environments()
        self.assertEqual(result.status, "invalid_response")
        self.assertTrue(terminal.closed)
        self.assertNotIn("unexpected screen", str(result))

    def test_native_stage_requires_explicit_approval_and_valid_pin(self):
        config = {
            "schema_version": 1,
            "domains": {
                "legacy": {
                    "stages": [
                        {
                            "kind": "native_cli",
                            "approved": False,
                            "native": {
                                "executable": self.settings.executable,
                                "sha256": self.settings.sha256,
                            },
                        }
                    ]
                }
            },
        }
        validate_configuration(config)
        config["domains"]["current"] = config["domains"].pop("legacy")
        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_native_settings_reject_shell_commands(self):
        with self.assertRaises(ValueError):
            NativeCliSettings.from_mapping({"executable": "codex --unsafe", "sha256": "a" * 64})


if __name__ == "__main__":
    unittest.main()
