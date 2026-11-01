"""Checks tasks.json so teammates can't merge a broken task.

Run from the repo root:  python scripts/validate_tasks.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "navigation_guide"
data = json.loads((ROOT / "tasks" / "tasks.json").read_text(encoding="utf-8"))

# Read the allowed action names straight from operators.py
ops_src = (ROOT / "operators.py").read_text(encoding="utf-8")
allowed = set(re.findall(r'^\s+"(\w+)":\s+_\w+,', ops_src, re.M))

errors, seen = [], set()
for t in data["tasks"]:
    tid = t.get("id", "<missing id>")
    if tid in seen:
        errors.append(f"duplicate task id: {tid}")
    seen.add(tid)
    for key in ("id", "title", "summary", "steps"):
        if not t.get(key):
            errors.append(f"{tid}: missing '{key}'")
    for n, s in enumerate(t.get("steps", []), 1):
        if not s.get("text"):
            errors.append(f"{tid} step {n}: missing 'text'")
        a = s.get("action")
        if a and a not in allowed:
            errors.append(f"{tid} step {n}: unknown action '{a}' (allowed: {sorted(allowed)})")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(data['tasks'])} tasks, actions allowed: {sorted(allowed)}")
