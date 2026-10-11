"""Parse only the rendered native Legacy environment selector, never log files."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional, Sequence, Tuple

from common.models import EnvironmentDescriptor, normalize_repository

_ID = re.compile(r"(?<![A-Za-z0-9_])[0-9a-f]{32}(?![A-Za-z0-9_])")


@dataclass(frozen=True)
class SelectorPage:
    environments: Tuple[EnvironmentDescriptor, ...]
    selected: Optional[str]
    global_visible: bool


def parse_selector(lines: Sequence[str]) -> Optional[SelectorPage]:
    """Return None until a complete unfiltered modal is rendered.

    The ID format and border are verified for CLI 0.162.0. Unknown layout,
    filtering or truncated data is an error rather than an empty inventory.
    """
    title = next((i for i, line in enumerate(lines) if "Select Environment" in line), None)
    if title is None:
        return None
    line = lines[title]
    label_pos = line.index("Select Environment")
    left = max(line.rfind("╭", 0, label_pos), line.rfind("┌", 0, label_pos))
    endings = [line.find(char, label_pos) for char in ("╮", "┐")]
    right = min((p for p in endings if p >= 0), default=-1)
    if left < 0 or right <= left:
        raise ValueError("Unknown native selector boundary")
    bottom = next(
        (
            i
            for i in range(title + 1, len(lines))
            if len(lines[i]) > right and lines[i][left] in "╰└" and lines[i][right] in "╯┘"
        ),
        None,
    )
    if bottom is None:
        return None
    contents = [row[left + 1 : right].strip() for row in lines[title + 1 : bottom]]
    if any("Loading environments" in row for row in contents):
        return None
    searches = [row for row in contents if row.startswith("Search:")]
    if not searches:
        return None
    if searches != ["Search:"]:
        raise ValueError("Filtered selector is not a full visible inventory")
    entries, selected, global_visible = [], None, False
    after_search = False
    for row in contents:
        if row == "Search:":
            after_search = True
            continue
        if not after_search or not row:
            continue
        marked = row.startswith(("> ", "› "))
        text = row[2:].strip() if marked else row
        if text == "All Environments (Global)":
            global_visible = True
            if marked:
                if selected is not None:
                    raise ValueError("Ambiguous native selector cursor")
                selected = "__global__"
            continue
        identifiers = list(_ID.finditer(text))
        if len(identifiers) != 1:
            raise ValueError("Ambiguous, truncated or missing native environment ID")
        match = identifiers[0]
        name = text[: match.start()].rstrip()
        if name.endswith("  PINNED"):
            name = name[:-8].rstrip()
        elif name == "PINNED":
            raise ValueError("Native environment label missing")
        suffix = text[match.end() :].strip()
        association = normalize_repository(suffix) if suffix else None
        if suffix and association is None:
            raise ValueError("Unknown native repository hint format")
        entry = EnvironmentDescriptor(
            cloud_type="legacy",
            environment_id=match.group(),
            name=name,
            repository=association,
            scope="native_selector",
            discovery_source="codex_tui_screen",
            evidence="live",
        )
        entries.append(entry)
        if marked:
            if selected is not None:
                raise ValueError("Ambiguous native selector cursor")
            selected = entry.environment_id
    if len({item.environment_id for item in entries}) != len(entries):
        raise ValueError("Duplicate native identities on one selector page")
    return SelectorPage(tuple(entries), selected, global_visible)
