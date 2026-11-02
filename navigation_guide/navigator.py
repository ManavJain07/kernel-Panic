"""The brain of the navigation interface. Pure Python (no bpy): testable anywhere.

A *recipe* is a goal ("build a wall") made of steps. Each step can have a
`done` condition that is checked against the live Blender state, so the guide
can (a) start at the first step the user has NOT done yet, (b) advance by
itself when the user does the step, and (c) warn when the user is in the
wrong mode for the step. Owner: navigation team.
"""
import json
import os
import re

try:
    from . import finder
except ImportError:  # running outside the package (tests / validator)
    import finder

_PATH = os.path.join(os.path.dirname(__file__), "recipes", "recipes.json")
_cache = None

# Every key allowed inside a "done" / "when" condition (validators use this).
KNOWN_KEYS = {
    "mode", "mode_not", "active_type", "min_selected", "max_selected",
    "min_mesh_objects", "min_objects", "max_objects", "new_object", "fewer_objects",
    "dim_min", "dim_max", "bottom_z_min", "rot_min", "has_modifier", "modifier_ready",
    "has_material", "shading", "active_hidden", "saved",
}


def load_recipes(force=False):
    global _cache
    if _cache is None or force:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _cache = json.load(f)["recipes"]
        except (OSError, ValueError, KeyError):
            _cache = []
    return _cache


def get_recipe(recipe_id):
    for r in load_recipes():
        if r["id"] == recipe_id:
            return r
    return None


def match(query, limit=3):
    """Find the recipes that best fit what the user typed."""
    tokens = finder._words(query)
    useful = [t for t in tokens if t not in finder._STOPWORDS] or tokens
    scored = []
    for index, r in enumerate(load_recipes()):
        title_words = finder._words(r["title"])
        keywords = [w for k in r.get("keywords", []) for w in finder._words(k)]
        summary_words = finder._words(r.get("summary", ""))
        score = 0
        for t in useful:
            if any(finder._match(t, w) for w in title_words):
                score += 3
            if any(finder._match(t, w) for w in keywords):
                score += 2
            if any(finder._match(t, w) for w in summary_words):
                score += 1
        if score > 0:
            scored.append((-score, index, r))
    scored.sort(key=lambda s: (s[0], s[1]))
    return [r for _, _, r in scored[:limit]]


def check_condition(cond, state, baseline):
    """True if every part of the condition holds in the current state."""
    for key, want in cond.items():
        if key == "mode":
            ok = state["mode_id"] == want
        elif key == "mode_not":
            ok = state["mode_id"] != want
        elif key == "active_type":
            ok = state["active_type"] == want
        elif key == "min_selected":
            ok = state["selected_count"] >= want
        elif key == "max_selected":
            ok = state["selected_count"] <= want
        elif key == "min_mesh_objects":
            ok = state["mesh_object_count"] >= want
        elif key == "min_objects":
            ok = state["object_count"] >= want
        elif key == "max_objects":
            ok = state["object_count"] <= want
        elif key == "new_object":
            ok = state["object_count"] > baseline.get("object_count", 0)
        elif key == "fewer_objects":
            ok = state["object_count"] < baseline.get("object_count", 0)
        elif key in ("dim_min", "dim_max"):
            dims = state["dims"]
            if dims is None:
                return False
            if key == "dim_min":
                ok = all(dims[axis] >= v for axis, v in want.items())
            else:
                ok = all(dims[axis] <= v for axis, v in want.items())
        elif key == "bottom_z_min":
            ok = state["bottom_z"] is not None and state["bottom_z"] >= want
        elif key == "rot_min":
            rot = state.get("rot_deg")
            if rot is None:
                return False
            ok = all(abs(rot[axis]) >= v for axis, v in want.items())
        elif key == "has_modifier":
            ok = want in state["modifier_types"]
        elif key == "modifier_ready":
            ok = want in state["ready_modifiers"]
        elif key == "has_material":
            ok = state["has_material"] == want
        elif key == "shading":
            ok = state["shading"] == want
        elif key == "active_hidden":
            ok = state.get("active_hidden", False) == want
        elif key == "saved":
            ok = state.get("saved", False) == want
        else:
            return False  # unknown condition: never auto-complete
        if not ok:
            return False
    return True


def is_done(step, state, baseline):
    """True/False for auto-checked steps, None for manual steps."""
    cond = step.get("done")
    if cond is None:
        return None
    return check_condition(cond, state, baseline)


def first_unfinished(recipe, state, baseline):
    """Index of the first step the user has not completed yet.

    This is how the guide starts 'from the point where the user is stuck'.
    """
    steps = recipe["steps"]
    for i, step in enumerate(steps):
        if is_done(step, state, baseline) is not True:
            return i
    return len(steps)


def advance(recipe, index, state, baseline):
    """Move forward while the current step's condition is already met."""
    steps = recipe["steps"]
    while index < len(steps) and is_done(steps[index], state, baseline) is True:
        index += 1
    return index


def problem(step, state):
    """(message, action) if the user is in the wrong mode for this step."""
    return finder.mode_advice({"mode": step.get("mode", "ANY")}, state)


def overlay_lines(recipe, index, state):
    """Short lines for the viewport banner: [(text, kind)], kind: title/step/warn."""
    steps = recipe["steps"]
    if index >= len(steps):
        return [(f"{recipe['title']}: complete!", "title")]
    step = steps[index]
    lines = [(f"{recipe['title']}  -  step {index + 1} of {len(steps)}", "title")]
    message, _ = problem(step, state)
    if message:
        lines.append((message, "warn"))
    lines.append((step["text"], "step"))
    if step.get("shortcut"):
        lines.append((f"Shortcut: {step['shortcut']}", "step"))
    return lines


# ---- shortcut parsing for the animated key display ------------------------
_KEY_NAMES = {
    "shift", "ctrl", "alt", "tab", "enter", "esc", "delete", "home", "space",
    "backspace", "numpad .", "numpad 0",
}


def _is_key(part):
    p = part.strip().lower()
    return (
        p in _KEY_NAMES
        or bool(re.fullmatch(r"[a-z0-9.]", p))
        or bool(re.fullmatch(r"f\d{1,2}", p))
        or bool(re.fullmatch(r"\d+(\.\d+)?", p))
    )


def parse_shortcut(text):
    """Turn a shortcut string into something the overlay can animate.

    Returns None if there is nothing to animate, else a dict:
      {"keys": [[key, ...], ...], "path": str|None, "mouse": str|None}
    keys is a sequence; each item is keys pressed together.
    """
    if not text:
        return None
    keys_part, _, path = text.partition(">")
    low = keys_part.lower()
    if any(w in low for w in ("mouse", "click", "wheel", "drag")):
        return {"keys": [], "path": path.strip() or None, "mouse": keys_part.strip()}
    groups = []
    for item in keys_part.split(","):
        parts = [p.strip() for p in item.split("+") if p.strip()]
        if not parts or not all(_is_key(p) for p in parts):
            return None
        groups.append(parts)
    if not groups:
        return None
    return {"keys": groups, "path": path.strip() or None, "mouse": None}
