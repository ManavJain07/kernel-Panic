"""Keeps the guide live: a timer watches Blender and advances the steps.

Owner: navigation team.
"""
import bpy

from . import context as ctx
from . import navigator

_cache = {"lines": [], "step": None}


def lines():
    return _cache["lines"]


def step():
    """The step the overlay should animate (dict) or None."""
    return _cache["step"]


def _current_step(recipe, index):
    steps = recipe["steps"]
    return steps[index] if index < len(steps) else None


def redraw_all():
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
    except Exception:
        pass


def refresh(context=None):
    """Rebuild the viewport banner text from the current goal and state."""
    context = context or bpy.context
    wm = context.window_manager
    recipe = navigator.get_recipe(wm.navguide_goal_id) if wm.navguide_goal_id else None
    if recipe is None:
        _cache["lines"] = []
        _cache["step"] = None
        return
    state = ctx.get_state(context)
    _cache["lines"] = navigator.overlay_lines(recipe, wm.navguide_goal_step, state)
    _cache["step"] = _current_step(recipe, wm.navguide_goal_step)


def _tick():
    context = bpy.context
    wm = context.window_manager
    if not wm.navguide_goal_id:
        if _cache["lines"]:
            _cache["lines"] = []
            _cache["step"] = None
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
    before = list(_cache["lines"])
    _cache["lines"] = navigator.overlay_lines(recipe, wm.navguide_goal_step, state)
    _cache["step"] = _current_step(recipe, wm.navguide_goal_step)
    if new != old or before != _cache["lines"]:
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
    _cache["lines"] = []
    _cache["step"] = None
