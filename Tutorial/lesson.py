"""Lesson mode.

How a session works
  1. The user clicks "Start tutorial" in the Nav Guide tab. The add-on is now
     "armed": the interface is dimmed and the viewport asks the user to press M.
  2. Pressing M (mouse over the 3D viewport) opens the bigger workspace and
     begins the lesson. (Lessons with "needs_panels": true keep the normal
     layout because they use the Properties editor.)
  3. A small card shows ONE task at a time with a counter (2/6), a progress
     bar, the hint text and an animation that plays automatically. Every task
     is checked automatically (see detect.py) and the card shows a live
     "not yet" message. When a task is finished the card briefly shows
     "1/6 - Task completed", then moves on to the next task.
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

from . import actions, detect, keys

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
    "gizmo_prev": {},     # fallback: viewport -> its navigate-gizmo setting, to restore
    "handles": [],        # (space class, region type, handle)
    "view_handle": None,
    "gif_on": True,       # show the hint animation inside the task card
    "flash": None,        # (tasks done, until time) while "Task completed" shows
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


def note_key(flag):
    """A learner's own key was pressed: remember it like the default key."""
    if flag and _S["lesson"] is not None and _S["phase"] == "running":
        _S["flags"].add(flag)


def begin_from_key(context):
    """The learner's own 'Start' key. Returns None or a message."""
    if _S["lesson"] is None or _S["phase"] != "armed":
        return "Click Start tutorial in the Nav Guide tab first."
    begin(context.window, context.area)
    return None


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
    tsize = 22 * s
    blf.size(0, tsize)
    tw, th = blf.dimensions(0, title)
    ty = region.height - 80 * s
    _rect(x0 - 12 * s, ty - 10 * s, tw + 24 * s, th + 20 * s, (0, 0, 0, 0.65))
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

    mine = keys.start_label()
    lines = [("Press M to start", 22, (1, 1, 1, 1)),
             ("with the mouse over the 3D viewport", 13, (0.75, 0.75, 0.75, 1))]
    if mine:
        lines.append((f"Your start key: {mine}", 13, (0.30, 0.80, 0.40, 1)))
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


GREEN = (0.30, 0.80, 0.40, 1)
AMBER = (1.0, 0.72, 0.30, 1)
BLUE = (0.28, 0.52, 1.0, 1)
WHITE = (1, 1, 1, 1)
LIGHT = (0.82, 0.82, 0.82, 1)
GREY = (0.62, 0.62, 0.62, 1)
GIF_SCALE = 0.6        # hint animation size relative to its original size


def _draw_progress(x, y, w, s, total, done, current):
    """Row of small bars, one per task: green = done, blue = current."""
    gap = 4 * s
    seg = (w - gap * (total - 1)) / max(total, 1)
    for i in range(total):
        col = GREEN if i < done else (BLUE if i == current else (0.30, 0.30, 0.34, 1))
        _rect(x + i * (seg + gap), y, seg, 6 * s, col)


def _draw_check(x, y, size, col):
    edge = max(1.5, size * 0.11)
    _rect(x, y, size, edge, col)
    _rect(x, y + size - edge, size, edge, col)
    _rect(x, y, edge, size, col)
    _rect(x + size - edge, y, edge, size, col)
    _rect(x + size * 0.22, y + size * 0.22, size * 0.56, size * 0.56, col)


def _card_geometry(region, area, s):
    x0 = 80 * s
    width = min(600 * s, max(region.width - _ui_width(area) - x0 - 24 * s, 300 * s))
    return x0, width, 30 * s, 14 * s       # x, width, bottom, pad


def _draw_card_header(x0, top, width, pad, s, counter, color, total, done, current):
    _text(x0 + pad, top - pad - 18 * s, counter, 22 * s, color)
    _draw_progress(x0 + pad, top - pad - 24 * s - 10 * s, width - 2 * pad, s,
                   total, done, current)
    return pad + 24 * s + 18 * s          # height used by the header


def _draw_task_card(region, area, s, lesson, hits):
    """One card, one task: counter (2/6), progress bar, task, hint, buttons and
    the hint animation. Replaces the old long checklist."""
    steps = lesson["steps"]
    total, idx = len(steps), _S["idx"]
    step = steps[idx]
    x0, width, bottom, pad = _card_geometry(region, area, s)
    tx = x0 + pad

    # hint animation (shown automatically; the user can hide it)
    name = _gif_for(step) if _S["gif_on"] else None
    meta = _meta().get(name) if name else None
    if not (name and _S["tex"].get(name)):
        meta = None
    gw = gh = 0.0
    side = False
    if meta:
        gw, gh = meta["w"] * s * GIF_SCALE, meta["h"] * s * GIF_SCALE
        side = width >= 480 * s
        if not side and gw > width - 2 * pad:
            gw = width - 2 * pad
            gh = gw * meta["h"] / meta["w"]
    text_w = width - 2 * pad - ((gw + pad) if (meta and side) else 0)

    buttons = []
    if step.get("action"):
        buttons.append((step.get("action_label", "Do it for me"), "do"))
    if _gif_for(step):
        buttons.append(("Hide animation" if _S["gif_on"] else "Show animation", "toggle_gif"))
    bsize = 13 * s
    blf.size(0, bsize)
    btn_w = [blf.dimensions(0, b[0])[0] + 22 * s for b in buttons]

    title_lines = _wrap(step["title"], 17 * s, text_w)
    hint_lines = _wrap(step["hint"], 13 * s, text_w) if step["hint"] else []
    msg_lines = _wrap(_S["msg"], 13 * s, text_w) if _S["msg"] else []
    mine_text = keys.step_line(step)
    key_lines = _wrap(mine_text, 13 * s, text_w) if mine_text else []
    left_h = (len(title_lines) * 24 * s + (4 * s + len(hint_lines) * 18 * s if hint_lines else 0)
              + len(key_lines) * 18 * s
              + len(msg_lines) * 18 * s + (8 * s + 26 * s if buttons else 0))
    if meta and side:
        body_h = max(left_h, gh)
    elif meta:
        body_h = left_h + pad + gh
    else:
        body_h = left_h
    head_h = pad + 24 * s + 18 * s
    H = head_h + body_h + pad
    top = bottom + H

    _rect(x0, bottom, width, H, (0, 0, 0, 0.78))
    _draw_card_header(x0, top, width, pad, s, f"{idx + 1}/{total}", WHITE, total, idx, idx)

    cur = top - head_h
    gif_top = cur
    for i, line in enumerate(title_lines):
        _text(tx, cur - 17 * s - i * 24 * s, line, 17 * s, WHITE)
    cur -= len(title_lines) * 24 * s
    if hint_lines:
        cur -= 4 * s
        for i, line in enumerate(hint_lines):
            _text(tx, cur - 13 * s - i * 18 * s, line, 13 * s, LIGHT)
        cur -= len(hint_lines) * 18 * s
    for i, line in enumerate(key_lines):
        _text(tx, cur - 13 * s - i * 18 * s, line, 13 * s, GREEN)
    cur -= len(key_lines) * 18 * s
    for i, line in enumerate(msg_lines):
        _text(tx, cur - 13 * s - i * 18 * s, line, 13 * s, AMBER)
    cur -= len(msg_lines) * 18 * s
    if buttons:
        cur -= 8 * s
        bx = tx
        for (label, kind), bw in zip(buttons, btn_w):
            _button(bx, cur - 26 * s, bw, 26 * s, label, bsize, kind, step["id"], hits)
            bx += bw + 8 * s
        cur -= 26 * s

    if meta:
        if side:
            gx, gy = x0 + width - pad - gw, gif_top - gh
        else:
            gx, gy = tx, cur - pad - gh
        _rect(gx - 2 * s, gy - 2 * s, gw + 4 * s, gh + 4 * s, (0.35, 0.35, 0.42, 1))
        _draw_sprite(name, gx, gy, gw, gh)


def _draw_flash_card(region, area, s, lesson):
    """Shown for a moment after a task is finished: '1/6  Task completed'."""
    total = len(lesson["steps"])
    done = _S["flash"][0]
    x0, width, bottom, pad = _card_geometry(region, area, s)
    head_h = pad + 24 * s + 18 * s
    H = head_h + 28 * s + pad
    top = bottom + H
    _rect(x0, bottom, width, H, (0, 0, 0, 0.78))
    _draw_card_header(x0, top, width, pad, s, f"{done}/{total}", GREEN, total, done, -1)
    _draw_check(x0 + pad, top - head_h - 22 * s, 18 * s, GREEN)
    _text(x0 + pad + 30 * s, top - head_h - 18 * s,
          f"Task {done} completed! Next task coming up...", 17 * s, GREEN)


def _draw_done_card(region, area, s, lesson, hits):
    total = len(lesson["steps"])
    x0, width, bottom, pad = _card_geometry(region, area, s)
    head_h = pad + 24 * s + 18 * s
    H = head_h + 40 * s + pad
    top = bottom + H
    _rect(x0, bottom, width, H, (0, 0, 0, 0.78))
    _draw_card_header(x0, top, width, pad, s, f"{total}/{total}", GREEN, total, total, -1)
    _draw_check(x0 + pad, top - head_h - 26 * s, 18 * s, GREEN)
    _text(x0 + pad + 30 * s, top - head_h - 22 * s, "Lesson complete!", 17 * s, GREEN)
    labels = []
    if _next_lesson_after(lesson) is not None:
        labels.append(("Next lesson", "next"))
    labels.append(("Finish", "finish"))
    bsize = 13 * s
    blf.size(0, bsize)
    widths = [blf.dimensions(0, text)[0] + 24 * s for text, _k in labels]
    bx = x0 + width - pad - sum(widths) - 8 * s * (len(widths) - 1)
    for (label, kind), bw in zip(labels, widths):
        _button(bx, bottom + pad, bw, 26 * s, label, bsize, kind, "", hits)
        bx += bw + 8 * s


def _draw_viewport():
    lesson = _S["lesson"]
    region = bpy.context.region
    area = bpy.context.area
    if lesson is None or region is None or area is None:
        return
    s = bpy.context.preferences.system.ui_scale
    hits = []

    gpu.state.blend_set("ALPHA")
    _draw_title(region, s, lesson)

    if _S["phase"] != "running":
        _draw_armed(region, area, s, lesson)
    elif _S["finished"]:
        _draw_done_card(region, area, s, lesson, hits)
    elif _S["flash"]:
        _draw_flash_card(region, area, s, lesson)
    else:
        _draw_task_card(region, area, s, lesson, hits)

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


def _free_textures(keep=()):
    """Free sprite sheets that are no longer needed (each is ~10 MB in memory)."""
    for name, ent in list(_S["tex"].items()):
        if name in keep:
            continue
        if ent:
            try:
                bpy.data.images.remove(ent[0])
            except Exception:
                pass
        del _S["tex"][name]


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
    _S.update(idx=idx, msg=None, flags=set(), base={}, last={},
              acc={"orbit": 0.0, "pan": 0.0, "zoom": 0.0}, finished=False)
    step = lesson["steps"][idx]
    name = _gif_for(step)
    _free_textures(keep=(name,) if name else ())
    if name:
        _load_texture(name)
    _S["hint_t0"] = time.time()
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
        _S.update(idx=idx, finished=True, msg=None, flash=None)
        _free_textures()
        if lesson["id"] not in prog["completed"]:
            prog["completed"].append(lesson["id"])
    else:
        _activate(idx)
        _S["flash"] = (idx, time.time() + 1.3)
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

    fl = _S["flash"]
    if fl and time.time() >= fl[1]:
        _S["flash"] = None
        _redraw_all()

    step = lesson["steps"][_S["idx"]]
    entry = detect.DETECTORS.get(step.get("detect"))
    done, msg = False, None
    if entry:
        try:
            done, msg = entry[1](_env())
        except Exception:
            done, msg = False, None

    animating = bool(_S["gif_on"] and _gif_for(step) and not _S["flash"])
    if done:
        _advance()
    elif msg != _S["msg"]:
        _S["msg"] = msg
        _redraw_all()
    elif animating:
        _redraw_view3d()        # keep the hint animation playing
    return 0.05 if animating else 0.1


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
    """Hide the zoom / pan / camera / grid buttons next to the axis gizmo while a
    lesson runs (the axis gizmo itself stays, lesson 1 uses it). Restored on exit.

    The preference is the normal way. If this Blender has no such preference, or
    refuses it, the whole navigate gizmo is hidden per viewport instead."""
    view = bpy.context.preferences.view
    pref_ok = hasattr(view, "show_navigate_ui")
    try:
        if not show:
            if pref_ok:
                if _S["nav_ui"] is None:
                    _S["nav_ui"] = view.show_navigate_ui
                view.show_navigate_ui = False
                pref_ok = view.show_navigate_ui is False
            if not pref_ok:
                for win in bpy.context.window_manager.windows:
                    for area in win.screen.areas:
                        if area.type == "VIEW_3D":
                            sp = area.spaces.active
                            if hasattr(sp, "show_gizmo_navigate"):
                                _S["gizmo_prev"].setdefault(area.as_pointer(), sp.show_gizmo_navigate)
                                sp.show_gizmo_navigate = False
        else:
            if pref_ok and _S["nav_ui"] is not None:
                view.show_navigate_ui = _S["nav_ui"]
            _S["nav_ui"] = None
            for win in bpy.context.window_manager.windows:
                for area in win.screen.areas:
                    if area.type == "VIEW_3D":
                        prev = _S["gizmo_prev"].get(area.as_pointer())
                        if prev is not None:
                            area.spaces.active.show_gizmo_navigate = prev
            _S["gizmo_prev"] = {}
    except (AttributeError, RuntimeError):
        pass
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            for region in area.regions:
                region.tag_redraw()


def start():
    """Arm the tutorial for the current lesson. Returns False if none is left."""
    lesson = current_lesson()
    if lesson is None:
        return False
    stop()
    _S.update(lesson=lesson, phase="armed", idx=0, finished=False, base={}, flags=set(),
              msg=None, last={}, hover=None, eat_release=False, hits={}, flash=None)
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
    _set_nav_buttons(False)         # the maximised view is a new screen: hide again
    _S["phase"] = "running"
    _activate(min(saved_step(lesson["id"]), len(lesson["steps"]) - 1))
    _redraw_all()


def next_lesson():
    """From the 'Lesson complete' card: go straight on to the next lesson."""
    nxt = current_lesson()
    if nxt is None:
        stop()
        return
    _S.update(lesson=nxt, hits={}, flash=None)
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
    _S.update(lesson=None, phase=None, hits={}, finished=False, msg=None, flash=None)
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
        if kind == "toggle_gif" and step and arg == current_id:
            _S["gif_on"] = not _S["gif_on"]
            name = _gif_for(step)
            if _S["gif_on"] and name:
                _load_texture(name)
                _S["hint_t0"] = time.time()
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
