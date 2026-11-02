"""Lesson mode.

How a session works
  1. The user clicks "Start tutorial" in the Nav Guide tab. The add-on is now
     "armed": the interface is dimmed and the viewport asks the user to press M.
  2. Pressing M (mouse over the 3D viewport) opens the bigger workspace and
     begins the lesson. (Lessons with "needs_panels": true keep the normal
     layout because they use the Properties editor.)
  3. The task checklist shows the tasks in order. Only the current task can be
     worked on; later tasks stay locked. Every task is checked automatically
     (see detect.py) and the current task shows a hint plus a live "not yet"
     message. A finished task is crossed out and the next one unlocks.
  4. Progress is saved to disk after every task. Lessons unlock one by one, so
     the user cannot jump ahead; the sidebar dropdown shows done / current /
     locked lessons.

Lessons live in lessons/lessons.json.
"""
import json
import os
import sys
import time

import bpy
import blf
import gpu
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader

from . import actions, detect

_DIR = os.path.dirname(__file__)
_LESSONS_PATH = os.path.join(_DIR, "lessons", "lessons.json")
_MEDIA = os.path.join(_DIR, "media")

NOISE = 0.002       # ignore camera changes smaller than this per tick

# Interface parts to dim: (Blender space class name, region types)
DIM_TARGETS = (
    ("SpaceView3D", ("HEADER", "TOOLS", "TOOL_HEADER")),
    ("SpaceOutliner", ("WINDOW", "HEADER")),
    ("SpaceProperties", ("WINDOW", "HEADER", "NAVIGATION_BAR")),
    ("SpaceDopeSheetEditor", ("WINDOW", "HEADER", "CHANNELS")),
)

_S = {
    "lesson": None,
    "phase": None,        # None | "armed" | "running"
    "idx": 0,             # index of the current task
    "finished": False,    # all tasks of the lesson are done
    "base": {},           # private notes for the current task's detector
    "flags": set(),       # key presses seen since the task became current
    "msg": None,          # live "not yet" message for the current task
    "last": {},
    "acc": {"orbit": 0.0, "pan": 0.0, "zoom": 0.0},
    "we_maxed": False,    # we opened the bigger workspace
    "nav_ui": None,       # the user's "navigation buttons" preference, to restore
    "handles": [],        # (space class, region type, handle)
    "view_handle": None,
    "hint": None,         # id of the task whose animation is open
    "hint_t0": 0.0,
    "hits": {},           # area pointer -> [(x, y, w, h, kind, arg)]
    "hover": None,        # (kind, arg) under the mouse
    "eat_release": False,
    "gen": 0,
    "tex": {},            # animation name -> (image, gpu texture) or False
}


# ---------------------------------------------------------------------------
# Saved progress
# ---------------------------------------------------------------------------
_progress = None


def _progress_path():
    try:
        base = bpy.utils.extension_path_user(__package__, path="", create=True)
    except Exception:
        base = os.path.join(bpy.utils.user_resource("CONFIG"), "navigation_guide")
        os.makedirs(base, exist_ok=True)
    return os.path.join(base, "progress.json")


def _load_progress():
    global _progress
    if _progress is None:
        data = {}
        try:
            with open(_progress_path(), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        _progress = {
            "completed": [x for x in data.get("completed", []) if isinstance(x, str)],
            "steps": {k: v for k, v in data.get("steps", {}).items() if isinstance(v, int)},
        }
    return _progress


def _save_progress():
    try:
        path = _progress_path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_load_progress(), f, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass        # progress is a convenience; never break a lesson over it


def reset_progress():
    global _progress
    _progress = {"completed": [], "steps": {}}
    _save_progress()


def is_completed(lesson_id):
    return lesson_id in _load_progress()["completed"]


def saved_step(lesson_id):
    return _load_progress()["steps"].get(lesson_id, 0)


def current_lesson():
    """The one lesson the user may start: the first that is not finished."""
    for item in load_lessons():
        if not is_completed(item["id"]):
            return item
    return None


def lesson_status(item):
    """'done', 'current' or 'locked' (lessons unlock one at a time)."""
    if is_completed(item["id"]):
        return "done"
    cur = current_lesson()
    return "current" if cur is not None and cur["id"] == item["id"] else "locked"


def _next_lesson_after(lesson):
    items = load_lessons()
    for i, item in enumerate(items):
        if item["id"] == lesson["id"] and i + 1 < len(items):
            return items[i + 1]
    return None


# ---------------------------------------------------------------------------
# Lesson data
# ---------------------------------------------------------------------------
_cache = None
_meta_cache = None


def load_lessons(force=False):
    global _cache
    if _cache is None or force:
        try:
            with open(_LESSONS_PATH, encoding="utf-8") as f:
                data = json.load(f)["lessons"]
        except (OSError, ValueError, KeyError):
            data = []
        for n, lesson in enumerate(data, 1):
            lesson["number"] = n
            for i, step in enumerate(lesson.get("steps", [])):
                step.setdefault("id", f"s{i}")
                step.setdefault("hint", "")
        _cache = data
    return _cache


def get_lesson(lesson_id):
    for lesson in load_lessons():
        if lesson["id"] == lesson_id:
            return lesson
    return None


def _meta():
    global _meta_cache
    if _meta_cache is None:
        try:
            with open(os.path.join(_MEDIA, "meta.json"), encoding="utf-8") as f:
                _meta_cache = json.load(f)
        except (OSError, ValueError):
            _meta_cache = {}
    return _meta_cache


def _gif_for(step):
    """Animation name for a task (Mac gets its own keys), or None."""
    name = step.get("gif")
    if name and sys.platform == "darwin" and step.get("gif_mac"):
        name = step["gif_mac"]
    return name if name and _meta().get(name) else None


def _find_step(lesson, step_id):
    for step in lesson["steps"]:
        if step["id"] == step_id:
            return step
    return None


# ---------------------------------------------------------------------------
# Small public helpers used by the panel
# ---------------------------------------------------------------------------

def is_active():
    return _S["lesson"] is not None


def phase():
    return _S["phase"]


def current():
    return _S["lesson"]


def progress():
    """(tasks done, tasks total) for the running lesson."""
    lesson = _S["lesson"]
    if lesson is None:
        return 0, 0
    total = len(lesson["steps"])
    if _S["finished"]:
        return total, total
    if _S["phase"] != "running":
        return min(saved_step(lesson["id"]), total), total
    return _S["idx"], total


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
_shader = None
_image_shader = None


def _get_shader():
    global _shader
    if _shader is None:
        try:
            _shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        except ValueError:  # older Blender name
            _shader = gpu.shader.from_builtin("2D_UNIFORM_COLOR")
    return _shader


def _get_image_shader():
    global _image_shader
    if _image_shader is None:
        try:
            _image_shader = gpu.shader.from_builtin("IMAGE")
        except ValueError:
            _image_shader = gpu.shader.from_builtin("2D_IMAGE")
    return _image_shader


def _rect(x, y, w, h, color):
    sh = _get_shader()
    batch = batch_for_shader(
        sh, "TRI_FAN", {"pos": ((x, y), (x + w, y), (x + w, y + h), (x, y + h))}
    )
    sh.uniform_float("color", color)
    batch.draw(sh)


def _text(x, y, text, size, color, strike=None):
    blf.size(0, size)
    blf.color(0, *color)
    blf.position(0, x, y, 0)
    blf.draw(0, text)
    if strike:
        w, _h = blf.dimensions(0, text)
        _rect(x, y + size * 0.32, w, max(1.5, size * 0.1), strike)


def _wrap(text, size, max_w):
    blf.size(0, size)
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and blf.dimensions(0, trial)[0] > max_w:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def _button(x, y, w, h, label, size, kind, arg, hits):
    hover = _S["hover"] == (kind, arg)
    _rect(x, y, w, h, (0.28, 0.52, 1.0, 1) if hover else (0.24, 0.24, 0.29, 1))
    blf.size(0, size)
    tw, th = blf.dimensions(0, label)
    _text(x + (w - tw) / 2, y + (h - th) / 2, label, size, (1, 1, 1, 1))
    hits.append((x, y, w, h, kind, arg))


def _draw_image(tex, x, y, w, h, u0, v0, u1, v1):
    sh = _get_image_shader()
    batch = batch_for_shader(
        sh, "TRI_FAN",
        {"pos": ((x, y), (x + w, y), (x + w, y + h), (x, y + h)),
         "texCoord": ((u0, v0), (u1, v0), (u1, v1), (u0, v1))},
    )
    sh.bind()
    sh.uniform_sampler("image", tex)
    batch.draw(sh)


def _draw_dim():
    region = bpy.context.region
    if region is None:
        return
    gpu.state.blend_set("ALPHA")
    _rect(0, 0, region.width, region.height, (0.0, 0.0, 0.0, 0.55))
    gpu.state.blend_set("NONE")


# ---------------------------------------------------------------------------
# The 3D viewport overlay: title, checklist, hint animation
# ---------------------------------------------------------------------------

def _draw_title(region, s, lesson):
    x0 = 80 * s
    title = f"Lesson {lesson['number']}: {lesson['title']}"
    tsize = 30 * s
    blf.size(0, tsize)
    tw, th = blf.dimensions(0, title)
    ty = region.height - 100 * s
    _rect(x0 - 14 * s, ty - 12 * s, tw + 28 * s, th + 24 * s, (0, 0, 0, 0.65))
    _text(x0, ty, title, tsize, (1, 1, 1, 1))


def _ui_width(area):
    return sum(r.width for r in area.regions if r.type == "UI" and r.width > 1)


def _draw_armed(region, area, s, lesson):
    """Small card at the bottom-left: an animated M key and one line of text."""
    total = len(lesson["steps"])
    saved = min(saved_step(lesson["id"]), total)
    meta = _meta().get("key_m")
    pad = 14 * s
    iw = meta["w"] * s * 0.7 if meta else 0
    ih = meta["h"] * s * 0.7 if meta else 0

    lines = [("Press M to start", 22, (1, 1, 1, 1)),
             ("with the mouse over the 3D viewport", 13, (0.75, 0.75, 0.75, 1))]
    if saved:
        lines.append((f"Continuing at task {saved + 1} of {total}", 13, (0.30, 0.80, 0.40, 1)))
    text_w = 0
    for text, size, _c in lines:
        blf.size(0, size * s)
        text_w = max(text_w, blf.dimensions(0, text)[0])
    text_h = sum(size * 1.6 * s for _t, size, _c in lines)
    cw = pad * 3 + iw + text_w
    ch = max(ih, text_h) + pad * 2
    x, y = 80 * s, 30 * s
    _rect(x, y, cw, ch, (0, 0, 0, 0.78))
    if meta:
        _draw_sprite("key_m", x + pad, y + (ch - ih) / 2, iw, ih)
    ty = y + ch / 2 + text_h / 2
    for text, size, col in lines:
        ty -= size * 1.6 * s
        _text(x + pad * 2 + iw, ty + size * 0.3 * s, text, size * s, col)


def _draw_viewport():
    lesson = _S["lesson"]
    region = bpy.context.region
    area = bpy.context.area
    if lesson is None or region is None or area is None:
        return
    s = bpy.context.preferences.system.ui_scale
    x0 = 80 * s
    steps = lesson["steps"]
    idx = _S["idx"]
    finished = _S["finished"]
    hits = []

    gpu.state.blend_set("ALPHA")
    _draw_title(region, s, lesson)

    if _S["phase"] != "running":
        _draw_armed(region, area, s, lesson)
        gpu.state.blend_set("NONE")
        _S["hits"][area.as_pointer()] = hits
        return

    # ---- task checklist, bottom-left ------------------------------------
    pad = 14 * s
    box = 18 * s
    width = min(720 * s, max(region.width - _ui_width(area) - x0 - 24 * s, 240 * s))
    text_x = x0 + pad + box + 12 * s
    avail_w = x0 + width - pad - text_x
    bsize = 13 * s

    rows = []
    total_h = pad * 2 + 26 * s
    for i, step in enumerate(steps):
        state = "done" if (finished or i < idx) else ("current" if i == idx else "locked")
        buttons = []
        if state == "current":
            if _gif_for(step):
                buttons.append(("Hint", "hint", step["id"]))
            if step.get("action"):
                buttons.append((step.get("action_label", "Do it for me"), "do", step["id"]))
        blf.size(0, bsize)
        btn_w = [blf.dimensions(0, b[0])[0] + 22 * s for b in buttons]
        gap = 8 * s
        btn_total = sum(btn_w) + gap * max(len(btn_w) - 1, 0)
        title_lines = _wrap(step["title"], 17 * s, avail_w - btn_total - 12 * s)
        hint_lines = []
        msg_lines = []
        if state != "locked" and step["hint"]:
            hint_lines = _wrap(step["hint"], 14 * s, avail_w)
        if state == "current" and _S["msg"]:
            msg_lines = _wrap(_S["msg"], 14 * s, avail_w)
        h = (10 * s + len(title_lines) * 24 * s + len(hint_lines) * 19 * s
             + len(msg_lines) * 19 * s + 8 * s)
        rows.append((step, state, buttons, btn_w, btn_total, gap, title_lines,
                     hint_lines, msg_lines, h))
        total_h += h
    if finished:
        total_h += 44 * s

    bottom = 30 * s
    _rect(x0, bottom, width, total_h, (0, 0, 0, 0.7))

    y = bottom + total_h - pad
    _text(x0 + pad, y - 16 * s, "Do these in order:", 15 * s, (0.75, 0.75, 0.75, 1))
    y -= 26 * s

    grey = (0.55, 0.55, 0.55, 1)
    locked = (0.40, 0.40, 0.40, 1)
    strike = (0.75, 0.75, 0.75, 1)
    green = (0.30, 0.80, 0.40, 1)
    amber = (1.0, 0.72, 0.30, 1)
    blue = (0.28, 0.52, 1.0, 1)
    for step, state, buttons, btn_w, btn_total, gap, t_lines, h_lines, m_lines, h in rows:
        if state == "current":
            _rect(x0, y - h, width, h, (0.17, 0.19, 0.27, 0.95))
            _rect(x0, y - h, 4 * s, h, blue)
        # checkbox
        bx, by = x0 + pad, y - 26 * s
        edge = max(1.5, 2 * s)
        col = green if state == "done" else (locked if state == "locked" else (0.95, 0.95, 0.95, 1))
        _rect(bx, by, box, edge, col)
        _rect(bx, by + box - edge, box, edge, col)
        _rect(bx, by, edge, box, col)
        _rect(bx + box - edge, by, edge, box, col)
        if state == "done":
            _rect(bx + 4 * s, by + 4 * s, box - 8 * s, box - 8 * s, green)
        # title + hint + live message
        ty0 = y - 10 * s - 17 * s
        tcol = {"done": grey, "locked": locked, "current": (1, 1, 1, 1)}[state]
        for i, line in enumerate(t_lines):
            _text(text_x, ty0 - i * 24 * s, line, 17 * s, tcol, strike if state == "done" else None)
        hy0 = ty0 - (len(t_lines) - 1) * 24 * s
        for i, line in enumerate(h_lines):
            _text(text_x, hy0 - (i + 1) * 19 * s - 2 * s, line, 14 * s,
                  grey if state == "done" else (0.82, 0.82, 0.82, 1),
                  strike if state == "done" else None)
        for i, line in enumerate(m_lines):
            _text(text_x, hy0 - (len(h_lines) + i + 1) * 19 * s - 2 * s, line, 14 * s, amber)
        # buttons, right-aligned on the first title line (current task only)
        bxr = x0 + width - pad - btn_total
        for (label, kind, arg), bw in zip(buttons, btn_w):
            _button(bxr, ty0 - 6 * s, bw, 24 * s, label, bsize, kind, arg, hits)
            bxr += bw + gap
        y -= h

    if finished:
        _text(x0 + pad, y - 22 * s, "Lesson complete!", 17 * s, green)
        labels = []
        if _next_lesson_after(lesson) is not None:
            labels.append(("Next lesson", "next"))
        labels.append(("Finish", "finish"))
        blf.size(0, bsize)
        widths = [blf.dimensions(0, t)[0] + 24 * s for t, _k in labels]
        bxr = x0 + width - pad - sum(widths) - 8 * s * (len(widths) - 1)
        for (label, kind), bw in zip(labels, widths):
            _button(bxr, y - 30 * s, bw, 26 * s, label, bsize, kind, "", hits)
            bxr += bw + 8 * s

    # ---- hint animation, right-hand side ---------------------------------
    if not finished:
        _draw_hint(region, area, s, hits)

    gpu.state.blend_set("NONE")
    _S["hits"][area.as_pointer()] = hits


def _draw_sprite(name, x, y, w, h):
    """Draw the current frame of a sprite-sheet animation. False if not loaded."""
    meta = _meta().get(name)
    ent = _S["tex"].get(name)
    if not meta or not ent:
        return False
    _img, tex = ent
    frames, cols, rows = meta["frames"], meta["cols"], meta["rows"]
    i = int((time.time() - _S["hint_t0"]) * meta["fps"]) % frames
    col, row = i % cols, i // cols
    u0, u1 = col / cols, (col + 1) / cols
    v1, v0 = 1 - row / rows, 1 - (row + 1) / rows
    gpu.state.blend_set("NONE")
    _draw_image(tex, x, y, w, h, u0, v0, u1, v1)
    gpu.state.blend_set("ALPHA")
    return True


def _draw_hint(region, area, s, hits):
    sid = _S["hint"]
    lesson = _S["lesson"]
    step = _find_step(lesson, sid) if sid else None
    name = _gif_for(step) if step else None
    if not name:
        return
    meta = _meta()[name]

    ui_w = sum(r.width for r in area.regions if r.type == "UI" and r.width > 1)
    pad = 12 * s
    head = 34 * s
    max_h = max(region.height - 260 * s, 120 * s)
    scale = min(1.0, (max_h - head - 2 * pad) / (meta["h"] * s))
    iw, ih = meta["w"] * s * scale, meta["h"] * s * scale
    cw, ch = iw + 2 * pad, ih + 2 * pad + head
    cx = max(region.width - ui_w - 24 * s - cw, 100 * s)
    cy = max((region.height - ch) / 2, 20 * s)

    _rect(cx, cy, cw, ch, (0.07, 0.07, 0.09, 0.96))
    _text(cx + pad, cy + ch - pad - 16 * s, "Hint", 16 * s, (1, 1, 1, 1))
    blf.size(0, 13 * s)
    close_w = blf.dimensions(0, "Close")[0] + 22 * s
    _button(cx + cw - pad - close_w, cy + ch - pad - 24 * s, close_w, 24 * s, "Close",
            13 * s, "close_hint", "", hits)

    if not _draw_sprite(name, cx + pad, cy + pad, iw, ih):
        _text(cx + pad, cy + ch / 2, "Animation not available", 14 * s, (0.8, 0.8, 0.8, 1))


def _load_texture(name):
    """Load a hint animation's sprite sheet (must run outside a draw callback)."""
    if name in _S["tex"]:
        return _S["tex"][name]
    ent = False
    try:
        img = bpy.data.images.load(os.path.join(_MEDIA, name + ".png"))
        img.colorspace_settings.name = "Non-Color"   # draw the pixels as they are
        ent = (img, gpu.texture.from_image(img))
    except Exception:
        ent = False
    _S["tex"][name] = ent
    return ent


def _free_textures():
    for ent in _S["tex"].values():
        if ent:
            try:
                bpy.data.images.remove(ent[0])
            except Exception:
                pass
    _S["tex"] = {}


# ---------------------------------------------------------------------------
# Redraw helpers
# ---------------------------------------------------------------------------

def _redraw_all():
    wm = bpy.context.window_manager
    for win in wm.windows:
        for area in win.screen.areas:
            area.tag_redraw()


def _redraw_view3d():
    wm = bpy.context.window_manager
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


# ---------------------------------------------------------------------------
# Detection (runs while a lesson is running)
# ---------------------------------------------------------------------------

def _env():
    wm = bpy.context.window_manager
    return detect.Env(list(wm.windows), _S["acc"], _S["flags"], _S["base"])


def _track_camera(windows):
    """Accumulate how far the viewport camera has been orbited / panned / zoomed."""
    acc = _S["acc"]
    for win in windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            r3d = area.spaces.active.region_3d
            if r3d is None or r3d.view_perspective == "CAMERA":
                continue
            key = area.as_pointer()
            cur = (r3d.view_rotation.copy(), r3d.view_location.copy(), r3d.view_distance)
            last = _S["last"].get(key)
            _S["last"][key] = cur
            if last is None:
                continue
            rot0, loc0, dist0 = last
            rot1, loc1, dist1 = cur
            base = max(dist0, 1e-4)
            d_zoom = abs(dist1 - dist0) / base
            d_orbit = rot0.rotation_difference(rot1).angle
            d_pan = (loc1 - loc0).length / base
            if d_zoom > NOISE:
                acc["zoom"] += d_zoom
            elif d_orbit > NOISE:
                acc["orbit"] += d_orbit
            elif d_pan > NOISE:
                acc["pan"] += d_pan


def _activate(idx):
    """Make task `idx` the current one and let its detector take a baseline."""
    lesson = _S["lesson"]
    _S.update(idx=idx, msg=None, flags=set(), base={}, last={}, hint=None,
              acc={"orbit": 0.0, "pan": 0.0, "zoom": 0.0}, finished=False)
    step = lesson["steps"][idx]
    entry = detect.DETECTORS.get(step.get("detect"))
    if entry and entry[0]:
        try:
            entry[0](_env())
        except Exception:
            pass


def _advance():
    """The current task is done: save, then unlock the next one."""
    lesson = _S["lesson"]
    idx = _S["idx"] + 1
    prog = _load_progress()
    prog["steps"][lesson["id"]] = idx
    if idx >= len(lesson["steps"]):
        _S.update(idx=idx, finished=True, msg=None, hint=None)
        if lesson["id"] not in prog["completed"]:
            prog["completed"].append(lesson["id"])
    else:
        _activate(idx)
    _save_progress()
    _redraw_all()


def _tick():
    lesson = _S["lesson"]
    if lesson is None:
        return None
    if _S["phase"] == "armed":
        _redraw_view3d()        # keep the M key animation playing
        return 0.05
    if _S["phase"] != "running" or _S["finished"]:
        return 0.2
    wm = bpy.context.window_manager
    windows = list(wm.windows)
    if not windows:
        return 0.2
    _track_camera(windows)

    step = lesson["steps"][_S["idx"]]
    entry = detect.DETECTORS.get(step.get("detect"))
    done, msg = False, None
    if entry:
        try:
            done, msg = entry[1](_env())
        except Exception:
            done, msg = False, None

    if done:
        _advance()
    elif msg != _S["msg"]:
        _S["msg"] = msg
        _redraw_all()
    elif _S["hint"]:
        _redraw_view3d()        # keep the hint animation playing
    return 0.05 if _S["hint"] else 0.1


@persistent
def _on_undo(*_args):
    if _S["lesson"] is not None and _S["phase"] == "running":
        _S["flags"].add("undo")


@persistent
def _on_load(*_args):
    stop()


# ---------------------------------------------------------------------------
# Layout: the "bigger workspace"
# ---------------------------------------------------------------------------

def _find_view3d(windows=None):
    best = None
    for win in (windows or bpy.context.window_manager.windows):
        for area in win.screen.areas:
            if area.type == "VIEW_3D" and (best is None or area.width * area.height > best[1].width * best[1].height):
                best = (win, area)
    return best


def _is_maximized(win):
    return len(win.screen.areas) == 1


def _toggle_full(win, area):
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.screen_full_area()


def _apply_layout(win=None, area=None):
    """Bigger workspace for most lessons, normal layout for needs_panels ones."""
    lesson = _S["lesson"]
    if win is None or area is None:
        found = _find_view3d()
        if found is None:
            return
        win, area = found
    want_big = not lesson.get("needs_panels")
    big = _is_maximized(win)
    try:
        if want_big and not big:
            _toggle_full(win, area)
            _S["we_maxed"] = True
        elif not want_big and big and _S["we_maxed"]:
            _toggle_full(win, area)
            _S["we_maxed"] = False
    except RuntimeError:
        pass


def _restore_layout():
    if not _S["we_maxed"]:
        return
    _S["we_maxed"] = False
    found = _find_view3d()
    if found and _is_maximized(found[0]):
        try:
            _toggle_full(*found)
        except RuntimeError:
            pass


# ---------------------------------------------------------------------------
# Start / begin / stop
# ---------------------------------------------------------------------------

def _set_nav_buttons(show):
    """Hide the zoom / pan / camera / ortho buttons next to the axis gizmo while a
    lesson runs (the axis gizmo itself stays, lesson 1 uses it). Restored on exit."""
    try:
        view = bpy.context.preferences.view
        if not show:
            if _S["nav_ui"] is None:
                _S["nav_ui"] = view.show_navigate_ui
            view.show_navigate_ui = False
        elif _S["nav_ui"] is not None:
            view.show_navigate_ui = _S["nav_ui"]
            _S["nav_ui"] = None
    except (AttributeError, RuntimeError):
        pass


def start():
    """Arm the tutorial for the current lesson. Returns False if none is left."""
    lesson = current_lesson()
    if lesson is None:
        return False
    stop()
    _S.update(lesson=lesson, phase="armed", idx=0, finished=False, base={}, flags=set(),
              msg=None, last={}, hint=None, hover=None, eat_release=False, hits={})
    _S["gen"] += 1
    _S["acc"] = {"orbit": 0.0, "pan": 0.0, "zoom": 0.0}

    for cls_name, regions in DIM_TARGETS:
        cls = getattr(bpy.types, cls_name, None)
        if cls is None:
            continue
        for region in regions:
            try:
                h = cls.draw_handler_add(_draw_dim, (), region, "POST_PIXEL")
            except (TypeError, ValueError):
                continue
            _S["handles"].append((cls, region, h))
    _S["view_handle"] = bpy.types.SpaceView3D.draw_handler_add(
        _draw_viewport, (), "WINDOW", "POST_PIXEL"
    )
    _set_nav_buttons(False)
    _S["hint_t0"] = time.time()
    _load_texture("key_m")
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=0.1)
    _redraw_all()
    return True


def begin(win, area):
    """The user pressed M: open the bigger workspace and start the tasks."""
    lesson = _S["lesson"]
    if lesson is None or _S["phase"] != "armed":
        return
    _apply_layout(win, area)
    _S["phase"] = "running"
    _activate(min(saved_step(lesson["id"]), len(lesson["steps"]) - 1))
    _redraw_all()


def next_lesson():
    """From the 'Lesson complete' card: go straight on to the next lesson."""
    nxt = current_lesson()
    if nxt is None:
        stop()
        return
    _S.update(lesson=nxt, hits={}, hint=None)
    _apply_layout()
    _activate(min(saved_step(nxt["id"]), len(nxt["steps"]) - 1))
    _redraw_all()


def stop():
    _restore_layout()
    _set_nav_buttons(True)
    for cls, region, h in _S["handles"]:
        try:
            cls.draw_handler_remove(h, region)
        except (ValueError, RuntimeError):
            pass
    _S["handles"] = []
    if _S["view_handle"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_S["view_handle"], "WINDOW")
        except (ValueError, RuntimeError):
            pass
        _S["view_handle"] = None
    _S.update(lesson=None, phase=None, hint=None, hits={}, finished=False, msg=None)
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
    _free_textures()
    try:
        _redraw_all()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

def _viewport_under_mouse(context, event):
    """(area, window region) if the mouse is over the 3D viewport itself, else None."""
    mx, my = event.mouse_x, event.mouse_y
    for area in context.window.screen.areas:
        if area.type != "VIEW_3D":
            continue
        if not (area.x <= mx < area.x + area.width and area.y <= my < area.y + area.height):
            continue
        region = None
        for r in area.regions:
            if r.type == "WINDOW":
                region = r
            elif (r.type in {"UI", "TOOLS", "HEADER", "TOOL_HEADER"} and r.width > 1
                  and r.x <= mx < r.x + r.width and r.y <= my < r.y + r.height):
                return None     # mouse is over the sidebar / toolbar / header
        return (area, region) if region else None
    return None


def _hit_test(context, event):
    """Which overlay button (if any) is under the mouse? Returns
    (area, window region, kind, arg) or None."""
    over = _viewport_under_mouse(context, event)
    if over is None:
        return None
    area, region = over
    lx, ly = event.mouse_x - region.x, event.mouse_y - region.y
    for x, y, w, h, kind, arg in _S["hits"].get(area.as_pointer(), ()):
        if x <= lx <= x + w and y <= ly <= y + h:
            return area, region, kind, arg
    return None


class NAVGUIDE_OT_start_tutorial(bpy.types.Operator):
    """Start the current lesson. Press M over the viewport to begin. Stays
    running in the background so the overlay buttons can be clicked and the
    lesson keys (Shift + A, 1 / 2 / 3) can be noticed."""
    bl_idname = "navguide.start_tutorial"
    bl_label = "Start tutorial"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        if not start():
            self.report({"INFO"}, "You have finished every lesson.")
            return {"CANCELLED"}
        self._gen = _S["gen"]
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if _S["lesson"] is None or self._gen != _S["gen"]:
            return {"CANCELLED", "PASS_THROUGH"}

        if event.type == "MOUSEMOVE":
            found = _hit_test(context, event)
            key = (found[2], found[3]) if found else None
            if key != _S["hover"]:
                _S["hover"] = key
                _redraw_view3d()
            return {"PASS_THROUGH"}

        # --- armed: wait for M ------------------------------------------
        if _S["phase"] == "armed":
            if event.type == "M" and event.value == "PRESS":
                over = _viewport_under_mouse(context, event)
                if over:
                    begin(context.window, over[0])
                    return {"RUNNING_MODAL"}
            return {"PASS_THROUGH"}

        # --- running: note the keys detectors care about ------------------
        if event.value == "PRESS" and event.type in {"A", "ONE", "TWO", "THREE"}:
            if _viewport_under_mouse(context, event):
                if event.type == "A" and event.shift:
                    _S["flags"].add("shift_a")
                elif event.type in {"ONE", "TWO", "THREE"} and not (event.shift or event.ctrl or event.alt):
                    _S["flags"].add({"ONE": "key_1", "TWO": "key_2", "THREE": "key_3"}[event.type])

        if event.type == "LEFTMOUSE":
            if event.value in {"PRESS", "DOUBLE_CLICK"}:
                found = _hit_test(context, event)
                if found:
                    area, region, kind, arg = found
                    self._click(context, area, region, kind, arg)
                    _S["eat_release"] = True
                    return {"RUNNING_MODAL"}
            elif event.value == "RELEASE" and _S["eat_release"]:
                _S["eat_release"] = False
                return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    def _click(self, context, area, region, kind, arg):
        lesson = _S["lesson"]
        step = _find_step(lesson, arg) if arg else None
        current_id = None if _S["finished"] else lesson["steps"][_S["idx"]]["id"]
        if kind == "hint" and step and arg == current_id:
            if _S["hint"] == arg:
                _S["hint"] = None
            else:
                _load_texture(_gif_for(step))
                _S["hint"] = arg
                _S["hint_t0"] = time.time()
        elif kind == "close_hint":
            _S["hint"] = None
        elif kind == "do" and step and arg == current_id:
            # The button only performs the action. The task is ticked off by
            # the detector, exactly as if the user had done it by hand.
            fn = actions.ACTIONS.get(step.get("action"))
            if fn is None:
                self.report({"ERROR"}, f"Unknown action: {step.get('action')}")
            else:
                try:
                    with bpy.context.temp_override(window=context.window, area=area,
                                                   region=region):
                        problem = fn(bpy.context)
                except RuntimeError as e:
                    problem = str(e).strip() or "That could not run here."
                if problem:
                    self.report({"WARNING"}, problem)
        elif kind == "next" and _S["finished"]:
            next_lesson()
        elif kind == "finish" and _S["finished"]:
            stop()
        _redraw_all()


class NAVGUIDE_OT_exit_lesson(bpy.types.Operator):
    bl_idname = "navguide.exit_lesson"
    bl_label = "Exit lesson"
    bl_description = "Stop the lesson (your progress is saved) and bring the interface back to normal"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        stop()
        return {"FINISHED"}


class NAVGUIDE_OT_reset_progress(bpy.types.Operator):
    bl_idname = "navguide.reset_progress"
    bl_label = "Reset progress"
    bl_description = "Forget all saved progress and start again from Lesson 1"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        stop()
        reset_progress()
        return {"FINISHED"}


classes = (NAVGUIDE_OT_start_tutorial, NAVGUIDE_OT_exit_lesson, NAVGUIDE_OT_reset_progress)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.app.handlers.undo_post.append(_on_undo)
    bpy.app.handlers.load_post.append(_on_load)


def unregister():
    stop()
    for handlers, fn in ((bpy.app.handlers.undo_post, _on_undo),
                         (bpy.app.handlers.load_post, _on_load)):
        if fn in handlers:
            handlers.remove(fn)
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
