"""Checks problems.json. Run from the repo root:  python scripts/validate_problems.py"""
import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "navigation_guide"
sys.path.insert(0, str(PKG))
import navigator  # noqa: E402

problems = json.loads((PKG / "problems" / "problems.json").read_text(encoding="utf-8"))["problems"]
fixes = set()
for name in ("operators.py", "goal_ops.py"):
    fixes |= set(re.findall(r'^\s+"(\w+)":\s+_\w+,', (PKG / name).read_text(encoding="utf-8"), re.M))

errors, seen = [], set()
for p in problems:
    pid = p.get("id", "<missing id>")
    if pid in seen:
        errors.append(f"duplicate problem id: {pid}")
    seen.add(pid)
    for key in ("id", "title", "summary", "keywords", "causes"):
        if not p.get(key):
            errors.append(f"{pid}: missing '{key}'")
    for n, c in enumerate(p.get("causes", []), 1):
        where = f"{pid} cause {n}"
        if not c.get("text"):
            errors.append(f"{where}: missing 'text'")
        if c.get("fix") and c["fix"] not in fixes:
            errors.append(f"{where}: unknown fix '{c['fix']}'")
        if c.get("quick") and not c.get("when"):
            errors.append(f"{where}: 'quick' needs a 'when' condition")
        for k in c.get("when", {}):
            if k not in navigator.KNOWN_KEYS:
                errors.append(f"{where}: unknown condition '{k}'")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(problems)} problems, {sum(len(p['causes']) for p in problems)} causes")
