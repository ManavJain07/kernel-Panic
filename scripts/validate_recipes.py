"""Checks recipes.json. Run from the repo root:  python scripts/validate_recipes.py"""
import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "navigation_guide"
sys.path.insert(0, str(PKG))
import navigator  # noqa: E402

recipes = json.loads((PKG / "recipes" / "recipes.json").read_text(encoding="utf-8"))["recipes"]
ops_src = (PKG / "operators.py").read_text(encoding="utf-8")
actions = set(re.findall(r'^\s+"(\w+)":\s+_\w+,', ops_src, re.M))
MODES = {"OBJECT", "EDIT_MESH", "ANY"}
AXES = {"X", "Y", "Z"}

errors, seen = [], set()
for r in recipes:
    rid = r.get("id", "<missing id>")
    if rid in seen:
        errors.append(f"duplicate recipe id: {rid}")
    seen.add(rid)
    for key in ("id", "title", "summary", "keywords", "steps"):
        if not r.get(key):
            errors.append(f"{rid}: missing '{key}'")
    for n, s in enumerate(r.get("steps", []), 1):
        where = f"{rid} step {n}"
        for key in ("short", "text"):
            if not s.get(key):
                errors.append(f"{where}: missing '{key}'")
        if s.get("mode") and s["mode"] not in MODES:
            errors.append(f"{where}: bad mode '{s['mode']}'")
        if s.get("action") and s["action"] not in actions:
            errors.append(f"{where}: unknown action '{s['action']}'")
        if s.get("axis") and s["axis"] not in AXES:
            errors.append(f"{where}: axis must be X, Y or Z")
        for k in s.get("done", {}):
            if k not in navigator.KNOWN_KEYS:
                errors.append(f"{where}: unknown condition '{k}'")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(recipes)} recipes, {sum(len(r['steps']) for r in recipes)} steps")
