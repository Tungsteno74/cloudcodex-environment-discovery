# CloudCodeX Environment Discovery — approved icon

The plugin icon is the user-approved 3D blue cloud with a sideways-perspective
magnifying glass, subtle cast shadow, and an inset/cut-through rim. It belongs to
the same CloudCodeX icon family as Windows Bootstrap but is a distinct artwork.

## Reproducible source

- Approved image: `tools/artwork/approved-icon.rgb.png`
- SHA-256: `7dbeca275c54d877f9a2c69e4afd573a409f7d680845026ed69d273fa71f0cb2`
- Historical family reference: `Tungsteno74/cloudcodex-windows-bootstrap`,
  `plugins/cloudcodex-windows-bootstrap/assets/icon.png`
- Reference Git blob: `90f40edf8326fa3f6aab967af186badd17f86dff`
- Packaged output: `plugins/cloudcodex-environment-discovery/assets/icon.png`

The exact approved PNG was transferred from the office workstation and
integrity-checked. It has an opaque black background because it was exported as
RGB; the build step replaces that black matte with transparency without changing
any foreground RGB pixel values. The cloud and lens in the approved image are
**not** claimed to be pixel-identical to the historical Bootstrap artwork.

## Rebuild

From the repository root (only for artwork regeneration):

```console
python -m pip install -r requirements-artwork.txt
python tools/build_discovery_icon.py
python tools/validate.py
```

The build is deterministic with an input hash guard. The output is a square
1254×1254 RGBA PNG. `assets/icon-origin.json` records the output SHA-256,
approved source and image conversion details.

The portable and Codex compatibility manifests use the same
`./assets/icon.png` path for `logo` and `composerIcon`.
The plugin remains skills-first: no mandatory MCP server is introduced.

## Lifecycle

This branding change is committed independently of ongoing Current Cloud
discovery development. Source releases, installed Codex caches and the private
ChatGPT plugin are not updated by this local commit.
