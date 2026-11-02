"""Checks lessons.json so teammates can't merge a broken lesson.

Run from the repo root:  python scripts/validate_lessons.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "navigation_guide"
data = json.loads((ROOT / "lessons" / "lessons.json").read_text(encoding="utf-8"))
meta = json.loads((ROOT / "media" / "meta.json").read_text(encoding="utf-8"))

# Allowed action names are read straight from actions.py
src = (ROOT / "actions.py").read_text(encoding="utf-8")
allowed_actions = set(re.findall(r'^\s+"(\w+)":\s+_\w+[,(]', src, re.M))
det_src = (ROOT / "detect.py").read_text(encoding="utf-8")
allowed_detect = set(re.findall(r'^    "(\w+)":\s+[\(_]', det_src, re.M))

cmd_src = (ROOT / "commands.py").read_text(encoding="utf-8")
allowed_cmds = set(re.findall(r'^    "(\w+)": \(', cmd_src, re.M))

errors, lesson_ids = [], set()
for lesson in data["lessons"]:
    lid = lesson.get("id", "<missing id>")
    if lid in lesson_ids:
        errors.append(f"duplicate lesson id: {lid}")
    lesson_ids.add(lid)
    for key in ("id", "title", "steps"):
        if not lesson.get(key):
            errors.append(f"{lid}: missing '{key}'")
    step_ids = set()
    for n, s in enumerate(lesson.get("steps", []), 1):
        where = f"{lid} task {n}"
        if not s.get("title"):
            errors.append(f"{where}: missing 'title'")
        if s.get("id"):
            if s["id"] in step_ids:
                errors.append(f"{where}: duplicate id '{s['id']}'")
            step_ids.add(s["id"])
        if s.get("action") and s["action"] not in allowed_actions:
            errors.append(f"{where}: unknown action '{s['action']}' (allowed: {sorted(allowed_actions)})")
        if not s.get("detect"):
            errors.append(f"{where}: missing 'detect' (every task must be checked automatically)")
        elif s["detect"] not in allowed_detect:
            errors.append(f"{where}: unknown detect '{s['detect']}' (allowed: {sorted(allowed_detect)})")
        for cid in s.get("cmds", ()):
            if cid not in allowed_cmds:
                errors.append(f"{where}: unknown command '{cid}' (see commands.py)")
        if not s.get("cmds"):
            errors.append(f"{where}: missing 'cmds' (accessible mode needs a command for every task)")
        gif = s.get("gif")
        if gif and (gif not in meta or not (ROOT / "media" / f"{gif}.png").exists()):
            errors.append(f"{where}: gif '{gif}' not found - run scripts/make_hint_gifs.py")

if errors:
    print("\n".join(errors))
    sys.exit(1)
n_tasks = sum(len(l["steps"]) for l in data["lessons"])
print(f"OK: {len(data['lessons'])} lessons, {n_tasks} tasks")
