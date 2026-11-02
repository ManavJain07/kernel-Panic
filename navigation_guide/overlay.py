"""Draws the guidance inside the 3D viewport, including animations.

  * banner (bottom-left): current step text
  * animated keycaps: the shortcut keys light up one after another
  * animated mouse: shows which mouse button to use
  * pulsing ring around the active object (select / transform steps)
  * pulsing, moving line along the X / Y / Z axis (axis-constrained steps)

Every drawing function is wrapped so a drawing problem can never break Blender.
Owner: navigation team.
"""
import math
import textwrap
import time

import blf
import bpy
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from . import navigator, session

_handles = {"px": None, "view": None}

_COLORS = {
    "title": (0.55, 0.85, 1.0, 1.0),
    "step": (1.0, 1.0, 1.0, 1.0),
    "warn": (1.0, 0.7, 0.2, 1.0),
}
AXES = {
    "X": ((1.0, 0.0, 0.0), (1.0, 0.25, 0.25)),
    "Y": ((0.0, 1.0, 0.0), (0.45, 0.9, 0.2)),
    "Z": ((0.0, 0.0, 1.0), (0.3, 0.55, 1.0)),
}
KEY_H = 30
KEY_STEP_SECONDS = 0.9


# ---- tiny drawing helpers -------------------------------------------------
def _rect(x, y, w, h, color):
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(
        shader, "TRI_FAN", {"pos": ((x, y), (x + w, y), (x + w, y + h), (x, y + h))}
    )
    gpu.state.blend_set("ALPHA")
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.blend_set("NONE")


def _text(x, y, text, color, size=15):
    blf.size(0, size)
    blf.color(0, *color)
    blf.position(0, x, y, 0)
    blf.draw(0, text)


def _text_width(text, size=15):
    blf.size(0, size)
    return blf.dimensions(0, text)[0]


# ---- banner ---------------------------------------------------------------
def _draw_banner(context, x0, y0):
    """Draw the text banner; return its top edge (y)."""
    raw = session.lines()
    size = 16
    blf.size(0, size)
    line_h = int(size * 1.45)
    pad = 12
    width = max(200, min(context.region.width - 40, 620))
    max_chars = max(20, int((width - 2 * pad) / (size * 0.55)))

    flat = []
    for text, kind in raw:
        for part in textwrap.wrap(text, max_chars) or [""]:
            flat.append((part, kind))

    height = line_h * len(flat) + 2 * pad
    try:
        _rect(x0, y0, width, height, (0.0, 0.0, 0.0, 0.65))
    except Exception:
        pass  # text still draws without the background box

    y = y0 + height - pad - size
    for text, kind in flat:
        _text(x0 + pad, y, text, _COLORS.get(kind, _COLORS["step"]), size)
        y -= line_h
    return y0 + height


# ---- animated keycaps -----------------------------------------------------
def _key_label(key):
    return key.upper() if len(key) == 1 and key.isalpha() else key


def _draw_keys(groups, x, y, t):
    """Animated keycaps: each key group 'presses' in turn, then it loops."""
    n = len(groups)
    period = n * KEY_STEP_SECONDS + 0.8
    phase = t % period
    active = int(phase // KEY_STEP_SECONDS) if phase < n * KEY_STEP_SECONDS else -1

    cx = x
    for gi, group in enumerate(groups):
        lit = gi == active
        for ki, key in enumerate(group):
            label = _key_label(key)
            tw = _text_width(label)
            w = max(30, int(tw) + 20)
            dy = -3 if lit else 0
            _rect(cx, y - 3, w, KEY_H, (0.05, 0.05, 0.05, 0.9))  # key shadow
            body = (0.95, 0.95, 0.95, 1.0) if lit else (0.30, 0.30, 0.33, 0.95)
            _rect(cx, y + dy, w, KEY_H, body)
            text_color = (0.0, 0.0, 0.0, 1.0) if lit else (1.0, 1.0, 1.0, 1.0)
            _text(cx + (w - tw) / 2, y + dy + 9, label, text_color)
            cx += w + 4
            if ki < len(group) - 1:
                _text(cx, y + 9, "+", (1.0, 1.0, 1.0, 1.0))
                cx += 16
        cx += 8
        if gi < n - 1:
            _text(cx, y + 9, ">", (0.7, 0.7, 0.7, 1.0))
            cx += 20
    return cx - x


# ---- animated mouse -------------------------------------------------------
def _draw_mouse(label, x, y, t):
    low = label.lower()
    w, h = 30, 44
    _rect(x, y, w, h, (0.30, 0.30, 0.33, 0.95))
    pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.5)
    col = (1.0, 0.8, 0.2, 0.4 + 0.6 * pulse)
    if "middle" in low or "wheel" in low or "scroll" in low:
        _rect(x + w / 2 - 3, y + h * 0.55, 6, h * 0.35, col)
    elif "right" in low:
        _rect(x + w / 2 + 0.5, y + h * 0.5, w / 2 - 1.5, h * 0.5 - 1, col)
    else:
        _rect(x + 1, y + h * 0.5, w / 2 - 1.5, h * 0.5 - 1, col)

    used = w + 10
    if "drag" in low:
        p = (t * 0.8) % 1.0
        _rect(x + w + 10 + 40 * p, y + h * 0.5 - 4, 8, 8, (1.0, 0.8, 0.2, 1.0))
        used += 60
    elif "wheel" in low or "scroll" in low:
        up = int(t * 2) % 2 == 0
        _text(x + w + 10, y + h * 0.4, "^" if up else "v", (1.0, 0.8, 0.2, 1.0), 20)
        used += 24
    _text(x + used, y + h * 0.35, label, (1.0, 1.0, 1.0, 1.0))
    return used + _text_width(label)


# ---- pulsing ring around the active object --------------------------------
def _draw_ring(context, t):
    obj = context.active_object
    if obj is None or context.region is None or context.region_data is None:
        return
    p = view3d_utils.location_3d_to_region_2d(
        context.region, context.region_data, obj.matrix_world.translation
    )
    if p is None:
        return
    r = 34 + 8 * math.sin(t * 2 * math.pi * 1.2)
    pts = [
        (p.x + r * math.cos(2 * math.pi * i / 48), p.y + r * math.sin(2 * math.pi * i / 48))
        for i in range(48)
    ]
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINE_LOOP", {"pos": pts})
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(3.0)
    shader.uniform_float("color", (1.0, 0.85, 0.1, 0.9))
    batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set("NONE")


# ---- 2D handler -----------------------------------------------------------
def _draw_pixel_impl(context):
    wm = context.window_manager
    if not wm.navguide_overlay:
        return
    raw = session.lines()
    if not raw or context.region is None:
        return

    x0, y0 = 20, 30
    top = _draw_banner(context, x0, y0)
    if not wm.navguide_animate:
        return

    t = time.time()
    step = session.step()
    if step is None:
        return

    parsed = navigator.parse_shortcut(step.get("shortcut"))
    if parsed:
        y = top + 12
        x = x0
        if parsed["mouse"]:
            x += _draw_mouse(parsed["mouse"], x, y, t) + 16
        if parsed["keys"]:
            x += _draw_keys(parsed["keys"], x, y + 6, t) + 12
        if parsed["path"]:
            _text(x, y + 15, parsed["path"].replace(">", " > "), (0.8, 0.9, 1.0, 1.0))

    if step.get("highlight") or step.get("axis"):
        _draw_ring(context, t)


def _draw_pixel():
    try:
        _draw_pixel_impl(bpy.context)
    except Exception:
        pass


# ---- 3D handler: axis line ------------------------------------------------
def _draw_view_impl(context):
    wm = context.window_manager
    if not (wm.navguide_overlay and wm.navguide_animate):
        return
    step = session.step()
    if not step or step.get("axis") not in AXES:
        return
    obj = context.active_object
    if obj is None:
        return

    direction, color = AXES[step["axis"]]
    d = Vector(direction)
    origin = obj.matrix_world.translation
    length = 8.0
    t = time.time()
    pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi)

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("ALPHA")

    a, b = origin - d * length, origin + d * length
    gpu.state.line_width_set(2.0)
    batch = batch_for_shader(shader, "LINES", {"pos": [tuple(a), tuple(b)]})
    shader.uniform_float("color", (*color, 0.3 + 0.4 * pulse))
    batch.draw(shader)

    # a bright dash that travels along the axis
    s = ((t * 0.6) % 1.0) * 2 - 1  # -1 .. 1
    s2 = min(s + 0.12, 1.0)
    gpu.state.line_width_set(6.0)
    batch = batch_for_shader(
        shader, "LINES", {"pos": [tuple(origin + d * (s * length)), tuple(origin + d * (s2 * length))]}
    )
    shader.uniform_float("color", (*color, 1.0))
    batch.draw(shader)

    gpu.state.line_width_set(1.0)
    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set("LESS_EQUAL")


def _draw_view():
    try:
        _draw_view_impl(bpy.context)
    except Exception:
        pass


# ---- fast redraw timer (drives the animation) ------------------------------
def _anim_tick():
    try:
        wm = bpy.context.window_manager
        if wm.navguide_goal_id and wm.navguide_overlay and wm.navguide_animate:
            session.redraw_all()
    except Exception:
        pass
    return 0.05  # about 20 frames per second while guiding


def register():
    if _handles["px"] is None:
        _handles["px"] = bpy.types.SpaceView3D.draw_handler_add(_draw_pixel, (), "WINDOW", "POST_PIXEL")
    if _handles["view"] is None:
        _handles["view"] = bpy.types.SpaceView3D.draw_handler_add(_draw_view, (), "WINDOW", "POST_VIEW")
    if not bpy.app.timers.is_registered(_anim_tick):
        bpy.app.timers.register(_anim_tick, first_interval=0.5, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_anim_tick):
        bpy.app.timers.unregister(_anim_tick)
    for key in ("px", "view"):
        if _handles[key] is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_handles[key], "WINDOW")
            _handles[key] = None
