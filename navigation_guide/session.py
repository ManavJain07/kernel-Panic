"""Keeps the guide live: a timer watches Blender, advances steps and feeds
the overlay (text, live progress, timing for animations).

Owner: navigation team.
"""
import time

import bpy

from . import context as ctx
from . import navigator

_cache = {
    "lines": [],
    "step": None,
    "progress": None,   # (fraction, label) or None
    "changed_at": 0.0,  # when the step last changed (drives entrance / success animations)
    "since": 0.0,       # when the user arrived at this step (drives the "stuck?" nudge)
    "kind": "",         # "start", "step" or "done": what the overlay should celebrate
}


def info():
    return _cache


def lines():
    return _cache["lines"]


def step():
    """The step the overlay should animate (dict) or None."""
    return _cache["step"]


def mark_change(kind):
    now = time.time()
    _cache["changed_at"] = now
    _cache["since"] = now
    _cache["kind"] = kind


def redraw_all():
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
    except Exception:
        pass


def _current_step(recipe, index):
    steps = recipe["steps"]
    return steps[index] if index < len(steps) else None


def _update(recipe, index, state):
    _cache["lines"] = navigator.overlay_lines(recipe, index, state)
    _cache["step"] = _current_step(recipe, index)
    _cache["progress"] = navigator.progress(_cache["step"], state) if _cache["step"] else None


def _clear():
    _cache.update(lines=[], step=None, progress=None, kind="")


def refresh(context=None):
    """Rebuild the overlay data from the current goal and state."""
    context = context or bpy.context
    wm = context.window_manager
    recipe = navigator.get_recipe(wm.navguide_goal_id) if wm.navguide_goal_id else None
    if recipe is None:
        _clear()
        return
    _update(recipe, wm.navguide_goal_step, ctx.get_state(context))


def _tick():
    context = bpy.context
    wm = context.window_manager
    if not wm.navguide_goal_id:
        if _cache["lines"]:
            _clear()
            redraw_all()
        return
    recipe = navigator.get_recipe(wm.navguide_goal_id)
    if recipe is None:
        return
    state = ctx.get_state(context)
    baseline = {"object_count": wm.navguide_goal_baseline}
    old = wm.navguide_goal_step
    new = navigator.advance(recipe, old, state, baseline)
    if new != old:
        wm.navguide_goal_step = new
        mark_change("done" if new >= len(recipe["steps"]) else "step")
    before = (list(_cache["lines"]), _cache["progress"])
    _update(recipe, wm.navguide_goal_step, state)
    if new != old or before != (_cache["lines"], _cache["progress"]):
        redraw_all()


def tick():
    try:
        _tick()
    except Exception:
        pass  # never let the timer crash Blender's UI
    return 0.5


def register():
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=1.0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    _clear()
