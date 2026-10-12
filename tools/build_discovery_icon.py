"""Build the approved CloudCodeX Environment Discovery icon without redesigning it.

This pipeline converts the user's approved black-matte image into a transparent
plugin PNG. RGB pixels throughout the visible artwork are unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "cloudcodex-environment-discovery"
SOURCE = ROOT / "tools" / "artwork" / "approved-icon.rgb.png"
OUTPUT = PLUGIN / "assets" / "icon.png"
PROVENANCE = PLUGIN / "assets" / "icon-origin.json"
SOURCE_SHA256 = "7dbeca275c54d877f9a2c69e4afd573a409f7d680845026ed69d273fa71f0cb2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_icon() -> None:
    if not SOURCE.is_file() or sha256(SOURCE) != SOURCE_SHA256:
        raise ValueError("The approved image source is missing or has changed")

    with Image.open(SOURCE) as original:
        if original.mode != "RGB" or original.size != (1254, 1254):
            raise ValueError("Unexpected approved PNG geometry or color mode")
        rgb = np.asarray(original, dtype=np.uint8).copy()

    # The approved generator returned an opaque RGB PNG with a black matte.
    # Remove only that matte. The visible cloud and magnifier retain their
    # exact RGB values, including the perspective and recessed rim.
    brightness = rgb.max(axis=2).astype(np.float32)
    alpha = np.clip((brightness - 5.0) * (255.0 / 55.0), 0.0, 255.0)
    alpha = np.rint(alpha).astype(np.uint8)

    rgba = np.dstack((rgb, alpha))
    if alpha[0, 0] != 0 or alpha[625, 630] != 255:
        raise ValueError("Transparency sanity check failed")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(OUTPUT, format="PNG",
                                           optimize=True)

    provenance = {
        "source_repository": "Tungsteno74/cloudcodex-windows-bootstrap",
        "source_path": "plugins/cloudcodex-windows-bootstrap/assets/icon.png",
        "source_git_blob": "90f40edf8326fa3f6aab967af186badd17f86dff",
        "approved_source_path": "tools/artwork/approved-icon.rgb.png",
        "approved_source_sha256": SOURCE_SHA256,
        "output_sha256": sha256(OUTPUT),
        "dimensions": [1254, 1254],
        "color_mode": "RGBA",
        "background_transparent": True,
        "foreground_rgb_preserved": True,
        "alpha_unchanged": False,
        "outside_region_unchanged": False,
        "change": "Approved perspective magnifier, recessed into cloud; black matte removed",
    }
    PROVENANCE.write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    build_icon()
