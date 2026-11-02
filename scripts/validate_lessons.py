"""Checks lessons/lessons.json against the rest of the add-on.

Run from the repo root:  python scripts/validate_lessons.py

What it checks
  * every lesson / task has the fields the add-on needs, ids are unique
  * "action"  must be a name in ACTIONS (actions.py)
  * "detect"  must be a name in DETECTORS (detect.py), if the add-on has one
  * "keys"    must be ids from KEY_ACTIONS (keys.py), if the add-on has one
  * "gif" / "gif_mac" must exist in media/meta.json and as media/<name>.png
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "navigation_guide"


def read(name):
    p = ROOT / name
    return p.read_text(encoding="utf-8") if p.exists() else None


lessons = json.loads((ROOT / "lessons" / "lessons.json").read_text(encoding="utf-8"))["lessons"]

actions_src = read("actions.py") or ""
actions = set(re.findall(r'^\s+"(\w+)":\s+_\w+,', actions_src, re.M))

detect_src = read("detect.py")
detectors = None
if detect_src and "DETECTORS = {" in detect_src:
    detectors = set(re.findall(r'^\s+"(\w+)":', detect_src[detect_src.index("DETECTORS = {"):], re.M))

keys_src = read("keys.py")
key_ids = None
if keys_src and "KEY_ACTIONS = (" in keys_src:
    block = keys_src[keys_src.index("KEY_ACTIONS = ("):keys_src.index("LABELS")]
    key_ids = set(re.findall(r'\(\s*"(\w+)",\s*"', block))

meta_path = ROOT / "media" / "meta.json"
meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

errors, warnings, seen = [], [], set()
used_media, n_tasks, n_detect = set(), 0, 0

for lesson in lessons:
    lid = lesson.get("id", "<missing id>")
    if lid in seen:
        errors.append(f"duplicate lesson id: {lid}")
    seen.add(lid)
    for key in ("id", "title", "steps"):
        if not lesson.get(key):
            errors.append(f"{lid}: missing '{key}'")
    if "needs_panels" in lesson and not isinstance(lesson["needs_panels"], bool):
        errors.append(f"{lid}: 'needs_panels' must be true or false")
    step_ids = set()
    for n, s in enumerate(lesson.get("steps", []), 1):
        where = f"{lid} task {n}"
        n_tasks += 1
        if not s.get("title"):
            errors.append(f"{where}: missing 'title'")
        if "id" in s:
            if s["id"] in step_ids:
                errors.append(f"{where}: duplicate task id '{s['id']}'")
            step_ids.add(s["id"])
        a = s.get("action")
        if a and a not in actions:
            errors.append(f"{where}: unknown action '{a}' (allowed: {sorted(actions)})")
        if a and not s.get("action_label"):
            warnings.append(f"{where}: has an action but no 'action_label' (button will say 'Do it for me')")
        d = s.get("detect")
        if d:
            n_detect += 1
        if detectors is not None:
            if not d:
                errors.append(f"{where}: missing 'detect'")
            elif d not in detectors:
                errors.append(f"{where}: unknown detector '{d}'")
        for k in s.get("keys", []):
            if key_ids is None:
                errors.append(f"{where}: has 'keys' but this add-on has no keys.py")
            elif k not in key_ids:
                errors.append(f"{where}: unknown key id '{k}' (allowed: {sorted(key_ids)})")
        for field in ("gif", "gif_mac"):
            g = s.get(field)
            if not g:
                continue
            used_media.add(g)
            if g not in meta:
                errors.append(f"{where}: {field} '{g}' is not in media/meta.json")
            if not (ROOT / "media" / f"{g}.png").exists():
                errors.append(f"{where}: media/{g}.png does not exist")

# media used directly by the Python code (e.g. the M key prompt) is not "unused"
code = "".join(p.read_text(encoding="utf-8") for p in ROOT.glob("*.py"))
unused = sorted(n for n in meta if n not in used_media and f'"{n}"' not in code)
if unused:
    warnings.append(f"media in meta.json not used by any task or by the code: {', '.join(unused)}")

for w in warnings:
    print("warning:", w)
if errors:
    print("\n".join(errors))
    sys.exit(1)
extra = "" if detectors is not None else "  (this version has no detect.py: tasks without 'detect' use a Done button)"
print(f"OK: {len(lessons)} lessons, {n_tasks} tasks, {n_detect} with auto-detection{extra}")
