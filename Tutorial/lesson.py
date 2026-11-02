"""Lesson mode.

A lesson is a list of tasks (steps). While a lesson runs this module
  * dims the rest of Blender's interface
  * shows "Lesson N: Title" at the top of the 3D viewport
  * shows the task checklist at the bottom-left of the viewport and crosses
    a task out when it is done
  * gives each task a Hint button that plays a short how-to animation on the
    right-hand side of the viewport
  * for tasks that cannot be detected, gives a Done button (and, where it
    makes sense, a "Do it for me" button)

Lessons live in lessons/lessons.json. Task detection for the mouse lesson
works by watching the viewport camera (rotation / position / distance) so it
works with a mouse, a trackpad and the on-screen gizmo alike.
"""
import json
import os
import time

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader

from . import actions

_DIR = os.path.dirname(__file__)
_LESSONS_PATH = os.path.join(_DIR, "lessons", "lessons.json")
_MEDIA = os.path.join(_DIR, "media")

# How much movement counts as "did it" for detect: orbit / pan / zoom.
THRESH = {
    "orbit": 0.7,   # radians of total rotation (~40 degrees)
    "pan": 0.35,    # total slide, as a fraction of the view distance
    "zoom": 0.30,   # total zoom, as a fraction of the view distance
}
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
    "done": set(),
    "last": {},
    "acc": {"orbit": 0.0, "pan": 0.0, "zoom": 0.0},
    "had_empty": False,
    "handles": [],        # (space class, region type, handle)
    "view_handle": None,
    "hint": None,         # id of the step whose animation is open
    "hint_t0": 0.0,
    "hits": {},           # area pointer -> [(x, y, w, h, kind, arg)]
    "hover": None,        # (kind, arg) under the mouse
    "eat_release": False,
    "gen": 0,
    "tex": {},            # animation name -> (image, gpu texture) or False
}


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


def current():
    return _S["lesson"]


def progress():
    lesson = _S["lesson"]
    if lesson is None:
        return 0, 0
    return len(_S["done"]), len(lesson["steps"])


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

def _draw_viewport():
    lesson = _S["lesson"]
    region = bpy.context.region
    area = bpy.context.area
    if lesson is None or region is None or area is None:
        return
    s = bpy.context.preferences.system.ui_scale
    x0 = 80 * s
    done = _S["done"]
    steps = lesson["steps"]
    hits = []

    gpu.state.blend_set("ALPHA")

    # ---- title, top of the viewport ------------------------------------
    title = f"Lesson {lesson['number']}: {lesson['title']}"
    tsize = 30 * s
    blf.size(0, tsize)
    tw, th = blf.dimensions(0, title)
    ty = region.height - 100 * s
    _rect(x0 - 14 * s, ty - 12 * s, tw + 28 * s, th + 24 * s, (0, 0, 0, 0.65))
    _text(x0, ty, title, tsize, (1, 1, 1, 1))

    # ---- task checklist, bottom-left ------------------------------------
    pad = 14 * s
    box = 18 * s
    ui_w = sum(r.width for r in area.regions if r.type == "UI" and r.width > 1)
    width = min(720 * s, max(region.width - ui_w - x0 - 24 * s, 240 * s))
    text_x = x0 + pad + box + 12 * s
    avail_w = x0 + width - pad - text_x
    bsize = 13 * s

    rows = []
    total_h = pad * 2 + 26 * s
    for step in steps:
        sid = step["id"]
        is_done = sid in done
        buttons = []
        if step.get("gif") and _meta().get(step["gif"]):
            buttons.append(("Hint", "hint", sid))
        if not is_done:
            if step.get("action"):
                buttons.append((step.get("action_label", "Do it for me"), "do", sid))
            if not step.get("detect"):
                buttons.append(("Done", "done", sid))
        blf.size(0, bsize)
        btn_w = [blf.dimensions(0, b[0])[0] + 22 * s for b in buttons]
        gap = 8 * s
        btn_total = sum(btn_w) + gap * max(len(btn_w) - 1, 0)
        title_lines = _wrap(step["title"], 17 * s, avail_w - btn_total - 12 * s)
        hint_lines = _wrap(step["hint"], 14 * s, avail_w) if step["hint"] else []
        h = 10 * s + len(title_lines) * 24 * s + len(hint_lines) * 19 * s + 8 * s
        rows.append((step, is_done, buttons, btn_w, btn_total, gap, title_lines, hint_lines, h))
        total_h += h
    all_done = len(done) == len(steps)
    if all_done:
        total_h += 30 * s

    bottom = 30 * s
    _rect(x0, bottom, width, total_h, (0, 0, 0, 0.7))

    y = bottom + total_h - pad
    _text(x0 + pad, y - 16 * s, "Try each of these:", 15 * s, (0.75, 0.75, 0.75, 1))
    y -= 26 * s

    grey = (0.55, 0.55, 0.55, 1)
    strike = (0.75, 0.75, 0.75, 1)
    green = (0.30, 0.80, 0.40, 1)
    for step, is_done, buttons, btn_w, btn_total, gap, t_lines, h_lines, h in rows:
        # checkbox
        bx, by = x0 + pad, y - 26 * s
        edge = max(1.5, 2 * s)
        col = green if is_done else (0.9, 0.9, 0.9, 1)
        _rect(bx, by, box, edge, col)
        _rect(bx, by + box - edge, box, edge, col)
        _rect(bx, by, edge, box, col)
        _rect(bx + box - edge, by, edge, box, col)
        if is_done:
            _rect(bx + 4 * s, by + 4 * s, box - 8 * s, box - 8 * s, green)
        # title + hint text
        ty0 = y - 10 * s - 17 * s
        for i, line in enumerate(t_lines):
            _text(text_x, ty0 - i * 24 * s, line, 17 * s,
                  grey if is_done else (1, 1, 1, 1), strike if is_done else None)
        hy0 = ty0 - (len(t_lines) - 1) * 24 * s
        for i, line in enumerate(h_lines):
            _text(text_x, hy0 - (i + 1) * 19 * s - 2 * s, line, 14 * s,
                  grey if is_done else (0.82, 0.82, 0.82, 1), strike if is_done else None)
        # buttons, right-aligned on the first title line
        bxr = x0 + width - pad - btn_total
        for (label, kind, arg), bw in zip(buttons, btn_w):
            _button(bxr, ty0 - 6 * s, bw, 24 * s, label, bsize, kind, arg, hits)
            bxr += bw + gap
        y -= h

    if all_done:
        _text(x0 + pad, y - 18 * s,
              "Lesson complete! Press Exit lesson in the Nav Guide tab.", 15 * s, green)

    # ---- hint animation, right-hand side ---------------------------------
    _draw_hint(region, area, s, hits)

    gpu.state.blend_set("NONE")
    _S["hits"][area.as_pointer()] = hits


def _draw_hint(region, area, s, hits):
    sid = _S["hint"]
    lesson = _S["lesson"]
    step = _find_step(lesson, sid) if sid else None
    if step is None or not step.get("gif"):
        return
    meta = _meta().get(step["gif"])
    ent = _S["tex"].get(step["gif"])
    if not meta:
        return

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
    _text(cx + pad, cy + ch - pad - 16 * s, "How to: " + step["title"].split(" (")[0],
          16 * s, (1, 1, 1, 1))
    blf.size(0, 13 * s)
    close_w = blf.dimensions(0, "Close")[0] + 22 * s
    _button(cx + cw - pad - close_w, cy + ch - pad - 24 * s, close_w, 24 * s, "Close",
            13 * s, "close_hint", "", hits)

    if ent:
        _img, tex = ent
        frames, cols, rows = meta["frames"], meta["cols"], meta["rows"]
        i = int((time.time() - _S["hint_t0"]) * meta["fps"]) % frames
        col, row = i % cols, i // cols
        u0, u1 = col / cols, (col + 1) / cols
        v1, v0 = 1 - row / rows, 1 - (row + 1) / rows
        gpu.state.blend_set("NONE")
        _draw_image(tex, cx + pad, cy + pad, iw, ih, u0, v0, u1, v1)
        gpu.state.blend_set("ALPHA")
    else:
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
# Detection (runs while a lesson is active)
# ---------------------------------------------------------------------------

def _tick():
    lesson = _S["lesson"]
    if lesson is None:
        return None
    wm = bpy.context.window_manager
    changed = False
    done = _S["done"]
    acc = _S["acc"]

    first_view_layer = None
    for win in wm.windows:
        if first_view_layer is None:
            first_view_layer = win.view_layer
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

    selected_now = None
    if first_view_layer is not None:
        vl = first_view_layer
        selected_now = sum(1 for o in vl.objects if o.select_get(view_layer=vl))
        if selected_now == 0:
            _S["had_empty"] = True

    for step in lesson["steps"]:
        sid, how = step["id"], step.get("detect")
        if not how or sid in done:
            continue
        if how in THRESH and acc[how] >= THRESH[how]:
            done.add(sid)
            changed = True
        elif how == "select" and selected_now and _S["had_empty"]:
            done.add(sid)
            changed = True

    if changed:
        _redraw_all()
    elif _S["hint"]:
        _redraw_view3d()        # keep the hint animation playing
    return 0.05 if _S["hint"] else 0.1


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------

def start(lesson_id):
    lesson = get_lesson(lesson_id)
    if lesson is None:
        return False
    stop()
    _S.update(lesson=lesson, done=set(), last={}, had_empty=False, hint=None,
              hover=None, eat_release=False, hits={})
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
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=0.1)
    _redraw_all()
    return True


def stop():
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
    _S["lesson"] = None
    _S["hint"] = None
    _S["hits"] = {}
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

def _hit_test(context, event):
    """Which overlay button (if any) is under the mouse? Returns
    (area, window region, kind, arg) or None."""
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
        if region is None:
            return None
        lx, ly = mx - region.x, my - region.y
        for x, y, w, h, kind, arg in _S["hits"].get(area.as_pointer(), ()):
            if x <= lx <= x + w and y <= ly <= y + h:
                return area, region, kind, arg
        return None
    return None


class NAVGUIDE_OT_start_lesson(bpy.types.Operator):
    """Dim the interface and show this lesson's tasks. Stays running in the
    background so the overlay buttons (Hint, Done...) can be clicked."""
    bl_idname = "navguide.start_lesson"
    bl_label = "Start lesson"
    bl_options = {"INTERNAL"}

    lesson_id: bpy.props.StringProperty()

    def invoke(self, context, event):
        if not start(self.lesson_id):
            self.report({"ERROR"}, f"Unknown lesson: {self.lesson_id}")
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
        if kind == "hint" and step:
            if _S["hint"] == arg:
                _S["hint"] = None
            else:
                _load_texture(step["gif"])
                _S["hint"] = arg
                _S["hint_t0"] = time.time()
        elif kind == "close_hint":
            _S["hint"] = None
        elif kind == "done" and step:
            _S["done"].add(arg)
        elif kind == "do" and step:
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
                else:
                    _S["done"].add(arg)
        _redraw_all()


class NAVGUIDE_OT_exit_lesson(bpy.types.Operator):
    bl_idname = "navguide.exit_lesson"
    bl_label = "Exit lesson"
    bl_description = "Stop the lesson and bring the interface back to normal"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        stop()
        return {"FINISHED"}


class NAVGUIDE_OT_toggle_maximize(bpy.types.Operator):
    bl_idname = "navguide.toggle_maximize"
    bl_label = "Bigger workspace"
    bl_description = "Make the 3D viewport fill the whole window (press again to go back)"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        try:
            bpy.ops.screen.screen_full_area()
        except RuntimeError as e:
            self.report({"WARNING"}, str(e).strip() or "Could not resize here.")
            return {"CANCELLED"}
        return {"FINISHED"}


classes = (NAVGUIDE_OT_start_lesson, NAVGUIDE_OT_exit_lesson, NAVGUIDE_OT_toggle_maximize)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    stop()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
