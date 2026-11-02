"""Checks that every animation sprite sheet matches its entry in media/meta.json.

Run from the repo root:  python scripts/validate_media.py

Each animation is one PNG containing `frames` pictures laid out in a grid, so
the image must be exactly (cols * w) x (rows * h) pixels and the grid must be
big enough to hold all the frames.
"""
import json
import struct
import sys
from pathlib import Path

MEDIA = Path(__file__).resolve().parent.parent / "navigation_guide" / "media"
meta = json.loads((MEDIA / "meta.json").read_text(encoding="utf-8"))

errors = []
for name, m in meta.items():
    missing = [k for k in ("frames", "cols", "rows", "w", "h", "fps") if not m.get(k)]
    if missing:
        errors.append(f"{name}: missing {', '.join(missing)}")
        continue
    png = MEDIA / f"{name}.png"
    if not png.exists():
        errors.append(f"{name}: {png.name} does not exist")
        continue
    head = png.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        errors.append(f"{name}: {png.name} is not a PNG file")
        continue
    width, height = struct.unpack(">II", head[16:24])
    want = (m["cols"] * m["w"], m["rows"] * m["h"])
    if (width, height) != want:
        errors.append(f"{name}: image is {width}x{height}, meta.json says {want[0]}x{want[1]}")
    if m["cols"] * m["rows"] < m["frames"]:
        errors.append(f"{name}: {m['frames']} frames do not fit in a {m['cols']}x{m['rows']} grid")

extra = sorted(p.stem for p in MEDIA.glob("*.png") if p.stem not in meta)
if extra:
    print(f"warning: PNG files with no entry in meta.json: {', '.join(extra)}")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(meta)} animations")
