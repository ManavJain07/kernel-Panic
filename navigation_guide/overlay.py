"""Draws the guidance inside the 3D viewport, with animations.

  * banner: slides in on every new step, shows a live progress bar that eases
  * keycaps: press down one after another with a glow, then loop
  * mouse: button pulses with click ripples, drag shows a moving dot with a trail
  * ripple rings and a bobbing arrow around the active object
  * axis line with several travelling dashes and a bouncing axis letter
  * success burst when a step completes, confetti when a goal is finished
  * after 15 seconds on one step: a gentle nudge ("Stuck? Open the Help tab")

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
_A = [1.0]  # global alpha multiplier used for fade-ins
_bar = {"for": None, "shown": 0.0}  # eased progress bar value

CYAN = (0.45, 0.85, 1.0, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
AMBER = (1.0, 0.72, 0.2, 1.0)
GREEN = (0.35, 0.9, 0.45, 1.0)
PANEL = (0.06, 0.06, 0.08, 0.82)
AXES = {
    "X": ((1.0, 0.0, 0.0), (1.0, 0.25, 0.25)),
    "Y": ((0.0, 1.0, 0.0), (0.45, 0.9, 0.2)),
    "Z": ((0.0, 0.0, 1.0), (0.3, 0.55, 1.0)),
}
CONFETTI = [(1.0, 0.4, 0.4), (1.0, 0.85, 0.2), (0.4, 0.9, 0.5), (0.4, 0.7, 1.0), (0.85, 0.5, 1.0)]
KEY_H = 30
KEY_SLOT = 0.9          # seconds each key group is "pressed"
STUCK_SECONDS = 15.0


# ---- math helpers ---------------------------------------------------------
def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _ease_out(t):
    t = _clamp(t)
    return 1 - (1 - t) ** 3


def _hash(i, k):
    """Deterministic pseudo-random number in 0..1."""
    return abs(math.sin(i * 12.9898 + k * 78.233) * 43758.5453) % 1.0


def _col(c):
    return (c[0], c[1], c[2], (c[3] if len(c) > 3 else 1.0) * _A[0])


# ---- drawing helpers ------------------------------------------------------
def _fill(pts, color, mode="TRI_FAN"):
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, mode, {"pos": pts})
    gpu.state.blend_set("ALPHA")
    shader.uniform_float("color", _col(color))
    batch.draw(shader)
    gpu.state.blend_set("NONE")


def _line(pts, color, width=2.0, mode="LINE_LOOP"):
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, mode, {"pos": pts})
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(width)
    shader.uniform_float("color", _col(color))
    batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set("NONE")


def _rect(x, y, w, h, color):
    _fill(((x, y), (x + w, y), (x + w, y + h), (x, y + h)), color)


def _circle(cx, cy, r, color, width=2.0, n=40):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    _line(pts, color, width, "LINE_LOOP")


def _text(x, y, text, color, size=15):
    blf.size(0, size)
    blf.color(0, *_col(color))
    blf.position(0, x, y, 0)
    blf.draw(0, text)


def _text_width(text, size=15):
    blf.size(0, size)
    return blf.dimensions(0, text)[0]


def _obj_screen(context, offset=(0.0, 0.0, 0.0)):
    """Screen position of the active object's origin (plus an offset), or None."""
    obj = context.active_object
    if obj is None or context.region is None or context.region_data is None:
        return None
    loc = obj.matrix_world.translation + Vector(offset)
    p = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, loc)
    return None if p is None else (p.x, p.y)


# ---- banner ---------------------------------------------------------------
def _draw_banner(context, x0, y0, now, skip_shortcut):
    """Draw the step banner. Returns (top_y, width)."""
    c = session.info()
    raw = [ln for ln in c["lines"] if not (skip_shortcut and ln[1] == "shortcut")]
    if c["step"] is not None and now - c["since"] > STUCK_SECONDS:
        raw.append(("Stuck? Open the Help tab in the sidebar.", "tip"))

    pad = 12
    width = max(220, min(context.region.width - 40, 540))
    body_chars = max(20, int((width - 2 * pad - 6) / 8.8))
    flat = []  # (text, kind, size)
    for text, kind in raw:
        size = 14 if kind == "title" else 16
        for part in textwrap.wrap(text, body_chars) or [""]:
            flat.append((part, kind, size))

    prog = c["progress"]
    prog_h = 34 if prog else 0
    text_h = sum(int(s * 1.45) for _, _, s in flat)
    height = text_h + prog_h + 2 * pad
    warn = any(k == "warn" for _, k, _ in flat)

    _rect(x0, y0, width, height, PANEL)
    _rect(x0, y0, 5, height, AMBER if warn else CYAN)  # accent strip

    y = y0 + height - pad
    colors = {"title": CYAN, "step": WHITE, "shortcut": (0.8, 0.9, 1.0, 1.0), "warn": AMBER, "tip": GREEN}
    for text, kind, size in flat:
        y -= int(size * 1.45)
        _text(x0 + pad + 6, y, text, colors.get(kind, WHITE), size)

    if prog:
        target, label = prog
        if _bar["for"] != c["changed_at"]:
            _bar["for"], _bar["shown"] = c["changed_at"], 0.0
        _bar["shown"] += (target - _bar["shown"]) * 0.18  # ease toward the real value
        bx, bw = x0 + pad + 6, width - 2 * pad - 6
        _text(bx, y0 + pad + 14, label, (0.85, 0.85, 0.9, 1.0), 13)
        _rect(bx, y0 + pad, bw, 8, (0.22, 0.22, 0.26, 1.0))
        f = _clamp(_bar["shown"])
        fill = (AMBER[0] + (GREEN[0] - AMBER[0]) * f, AMBER[1] + (GREEN[1] - AMBER[1]) * f,
                AMBER[2] + (GREEN[2] - AMBER[2]) * f, 1.0)
        _rect(bx, y0 + pad, max(2.0, bw * f), 8, fill)
        if target >= 0.999:  # shimmer when complete
            sx = bx + (bw - 30) * ((time.time() * 0.8) % 1.0)
            _rect(sx, y0 + pad, 30, 8, (1.0, 1.0, 1.0, 0.35))
    return y0 + height, width


# ---- keycaps --------------------------------------------------------------
def _key_label(key):
    return key.upper() if len(key) == 1 and key.isalpha() else key


def _draw_keys(groups, x, y, now, age, nudge):
    """Keycaps press down in sequence with a glow, then the sequence loops."""
    n = len(groups)
    period = n * KEY_SLOT + 0.9
    phase = now % period
    slot = int(phase // KEY_SLOT) if phase < n * KEY_SLOT else -1
    local = (phase - slot * KEY_SLOT) / KEY_SLOT if slot >= 0 else 0.0
    bounce = abs(math.sin(now * 6)) * 5 if nudge else 0.0

    cx = x
    saved = _A[0]
    for gi, group in enumerate(groups):
        _A[0] = saved * _ease_out((age - 0.07 * gi) / 0.3)  # staggered fade-in
        press = 0.0
        if gi == slot:
            press = _clamp(local * 5) * (1 - _clamp((local - 0.7) / 0.3))
        for ki, key in enumerate(group):
            label = _key_label(key)
            tw = _text_width(label)
            w = max(30, int(tw) + 20)
            ky = y + bounce - 4 * press
            if press > 0:  # glow behind a pressed key
                _rect(cx - 4, ky - 4, w + 8, KEY_H + 8, (1.0, 0.85, 0.3, 0.30 * press))
            _rect(cx, y + bounce - 4, w, KEY_H, (0.04, 0.04, 0.05, 0.9))  # shadow
            base, lit = (0.30, 0.30, 0.33), (0.97, 0.97, 0.97)
            body = tuple(base[i] + (lit[i] - base[i]) * press for i in range(3)) + (0.97,)
            _rect(cx, ky, w, KEY_H, body)
            tcol = (1 - press, 1 - press, 1 - press, 1.0)
            _text(cx + (w - tw) / 2, ky + 9, label, tcol)
            cx += w + 4
            if ki < len(group) - 1:
                _text(cx, y + 9 + bounce, "+", WHITE)
                cx += 16
        cx += 8
        if gi < n - 1:
            _text(cx, y + 9 + bounce, ">", (0.7, 0.7, 0.7, 1.0))
            cx += 20
    _A[0] = saved
    return cx - x


# ---- mouse ----------------------------------------------------------------
def _draw_mouse(label, x, y, now):
    low = label.lower()
    w, h = 30, 44
    _rect(x, y, w, h, (0.30, 0.30, 0.33, 0.97))
    cycle = (now * 1.1) % 1.0
    pulse = 0.5 + 0.5 * math.sin(now * 2 * math.pi * 1.5)
    col = (1.0, 0.8, 0.2, 0.45 + 0.55 * pulse)

    if "middle" in low or "wheel" in low or "scroll" in low:
        bx, by, bw, bh = x + w / 2 - 3, y + h * 0.55, 6, h * 0.35
    elif "right" in low:
        bx, by, bw, bh = x + w / 2 + 0.5, y + h * 0.5, w / 2 - 1.5, h * 0.5 - 1
    else:
        bx, by, bw, bh = x + 1, y + h * 0.5, w / 2 - 1.5, h * 0.5 - 1
    _rect(bx, by, bw, bh, col)
    _circle(bx + bw / 2, by + bh / 2, 4 + 16 * cycle, (1.0, 0.8, 0.2, 0.8 * (1 - cycle)), 2.0, 24)  # click ripple

    used = w + 10
    if "drag" in low:
        p = _ease_out((now * 0.7) % 1.0)
        for k in range(4):  # dot with a fading trail
            pk = max(0.0, p - 0.06 * k)
            _rect(x + w + 10 + 46 * pk, y + h * 0.5 - 4, 8, 8, (1.0, 0.8, 0.2, 1.0 - 0.25 * k))
        used += 62
    elif "wheel" in low or "scroll" in low:
        up = int(now * 2.5) % 2 == 0
        _text(x + w + 10, y + h * 0.4, "^" if up else "v", AMBER, 22)
        used += 26
    _text(x + used, y + h * 0.35, label, WHITE)
    return used + _text_width(label)


# ---- rings and arrow around the active object -------------------------------
def _draw_ring(context, now):
    p = _obj_screen(context)
    if p is None:
        return
    for k in range(2):  # two ripples, half a cycle apart
        ph = (now * 0.9 + 0.5 * k) % 1.0
        _circle(p[0], p[1], 14 + 46 * _ease_out(ph), (1.0, 0.85, 0.15, 0.9 * (1 - ph)), 3.0)
    _circle(p[0], p[1], 10, (1.0, 0.85, 0.15, 0.9), 2.0, 24)
    bob = 6 * math.sin(now * 2 * math.pi * 1.4)  # arrow bobbing above the object
    ay = p[1] + 66 + bob
    _fill(((p[0], ay - 14), (p[0] - 9, ay + 2), (p[0] + 9, ay + 2)), (1.0, 0.85, 0.15, 1.0), "TRI_FAN")


def _draw_axis_letter(context, axis, now):
    _, color = AXES[axis]
    d = AXES[axis][0]
    p = _obj_screen(context, tuple(c * 5.0 for c in d))
    if p is None:
        return
    bounce = 5 * math.sin(now * 2 * math.pi * 1.2)
    _circle(p[0], p[1] + bounce, 15, (*color, 0.9), 2.0, 24)
    _text(p[0] - 5, p[1] + bounce - 7, axis, (*color, 1.0), 20)


# ---- celebration ----------------------------------------------------------
def _draw_flash(context, kind, age, x0, top, width):
    saved = _A[0]
    _A[0] = 1.0
    if kind == "step" and age < 1.3:
        p = _obj_screen(context)
        if p is not None and age < 0.8:
            r = 12 + 90 * _ease_out(age / 0.8)
            _circle(p[0], p[1], r, (*GREEN[:3], 0.9 * (1 - age / 0.8)), 4.0, 48)
        rise = 26 * _ease_out(age / 0.9)
        fade = 1 - _clamp((age - 0.7) / 0.6)
        _text(x0 + 4, top + 16 + rise, "Step done!", (*GREEN[:3], fade), 20)
    elif kind == "done" and age < 2.4:
        for i in range(40):  # confetti
            px = x0 + _hash(i, 1) * width
            vy = 160 + 220 * _hash(i, 2)
            sway = 18 * math.sin(age * 5 + i)
            py = top + 60 + 90 * _hash(i, 3) + vy * age * 0.5 - 330 * age * age * 0.5
            c = CONFETTI[i % len(CONFETTI)]
            _rect(px + sway, py, 7, 7, (*c, 1.0 - _clamp((age - 1.6) / 0.8)))
        pop = 1 + 0.25 * math.sin(_clamp(age / 0.5) * math.pi)
        _text(x0 + 4, top + 22, "Goal complete!", (*GREEN[:3], 1.0 - _clamp((age - 1.8) / 0.6)), int(24 * pop))
    _A[0] = saved


# ---- 2D handler -----------------------------------------------------------
def _draw_pixel_impl(context):
    wm = context.window_manager
    if not wm.navguide_overlay:
        return
    c = session.info()
    if not c["lines"] or context.region is None:
        return

    now = time.time()
    age = now - c["changed_at"]
    step = c["step"]
    animate = wm.navguide_animate
    parsed = navigator.parse_shortcut(step.get("shortcut")) if step else None

    intro = _ease_out(age / 0.35) if animate else 1.0
    slide = (1 - intro) * 34
    _A[0] = intro
    try:
        top, width = _draw_banner(context, 20, 30 - slide, now, skip_shortcut=bool(animate and parsed))
        if not animate or step is None:
            return

        nudge = now - c["since"] > STUCK_SECONDS
        if parsed:
            y = top + 12
            x = 20
            if parsed["mouse"]:
                x += _draw_mouse(parsed["mouse"], x, y, now) + 16
            if parsed["keys"]:
                x += _draw_keys(parsed["keys"], x, y + 6, now, age, nudge) + 12
            if parsed["path"]:
                _text(x, y + 15, parsed["path"].replace(">", " > "), (0.8, 0.9, 1.0, 1.0))

        if step.get("highlight") or step.get("axis"):
            _draw_ring(context, now)
        if step.get("axis") in AXES:
            _draw_axis_letter(context, step["axis"], now)
        if c["kind"] in ("step", "done"):
            _draw_flash(context, c["kind"], age, 20, top, width)
    finally:
        _A[0] = 1.0


def _draw_pixel():
    try:
        _draw_pixel_impl(bpy.context)
    except Exception:
        pass


# ---- 3D handler: axis line --------------------------------------------------
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
    shader.uniform_float("color", (*color, 0.28 + 0.4 * pulse))
    batch.draw(shader)

    gpu.state.line_width_set(6.0)  # three dashes travelling along the axis
    for k in range(3):
        s = ((t * 0.5 + k / 3) % 1.0) * 2 - 1
        s2 = min(s + 0.1, 1.0)
        fade = 1 - abs(s) ** 3
        batch = batch_for_shader(
            shader, "LINES", {"pos": [tuple(origin + d * (s * length)), tuple(origin + d * (s2 * length))]}
        )
        shader.uniform_float("color", (*color, fade))
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
    return 0.04  # about 25 frames per second while guiding


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
