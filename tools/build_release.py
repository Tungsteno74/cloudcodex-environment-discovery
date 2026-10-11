"""Build a deterministic standalone agent plugin ZIP, no external dependencies."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-cloud-environment-discovery"
VERSION = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
DIST = ROOT / "dist"


def build(output_dir: Path = DIST) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"codex-cloud-environment-discovery-{VERSION}.zip"
    entries = sorted(
        [path for path in PLUGIN.rglob("*") if path.is_file()
         and "__pycache__" not in path.parts
         and not path.name.endswith((".pyc", ".pyo"))
         and not path.name.startswith(".env")],
        key=lambda path: path.relative_to(PLUGIN).as_posix(),
    )
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as handle:
        for path in entries:
            relative = path.relative_to(PLUGIN).as_posix()
            info = zipfile.ZipInfo(f"{PLUGIN.name}/{relative}")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            handle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                            compresslevel=9)
    return archive


def main() -> int:
    archive = build()
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"archive={archive} files={len(zipfile.ZipFile(archive).namelist())} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
