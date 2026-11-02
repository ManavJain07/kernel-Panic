"""Checks tools.json. Run from the repo root:  python scripts/validate_tools.py"""
import json
import sys
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "navigation_guide" / "tools" / "tools.json"
tools = json.loads(path.read_text(encoding="utf-8"))["tools"]
MODES = {"ANY", "OBJECT", "EDIT_MESH"}

errors, seen = [], set()
for t in tools:
    tid = t.get("id", "<missing id>")
    if tid in seen:
        errors.append(f"duplicate id: {tid}")
    seen.add(tid)
    for key in ("id", "name", "mode", "where", "what", "keywords"):
        if not t.get(key):
            errors.append(f"{tid}: missing '{key}'")
    if t.get("mode") not in MODES:
        errors.append(f"{tid}: mode must be one of {sorted(MODES)}")

if errors:
    print("\n".join(errors))
    sys.exit(1)

unverified = [t["id"] for t in tools if not t.get("verified")]
print(f"OK: {len(tools)} tools")
print(f"Still to verify in Blender ({len(unverified)}): {', '.join(unverified) or 'none'}")
