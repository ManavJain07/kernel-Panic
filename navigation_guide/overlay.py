"""Draws the current step as a banner inside the 3D viewport.

Owner: navigation team.
"""
import textwrap

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from . import session

_handle = None
_COLORS = {
    "title": (0.55, 0.85, 1.0, 1.0),
    "step": (1.0, 1.0, 1.0, 1.0),
    "warn": (1.0, 0.7, 0.2, 1.0),
}


def _draw():
    try:
        context = bpy.context
        if not context.window_manager.navguide_overlay:
            return
        raw = session.lines()
        if not raw or context.region is None:
            return

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
        x0, y0 = 20, 30

        try:
            shader = gpu.shader.from_builtin("UNIFORM_COLOR")
            verts = ((x0, y0), (x0 + width, y0), (x0 + width, y0 + height), (x0, y0 + height))
            batch = batch_for_shader(shader, "TRI_FAN", {"pos": verts})
            gpu.state.blend_set("ALPHA")
            shader.uniform_float("color", (0.0, 0.0, 0.0, 0.65))
            batch.draw(shader)
            gpu.state.blend_set("NONE")
        except Exception:
            pass  # text still draws without the background box

        y = y0 + height - pad - size
        for text, kind in flat:
            blf.color(0, *_COLORS.get(kind, _COLORS["step"]))
            blf.position(0, x0 + pad, y, 0)
            blf.draw(0, text)
            y -= line_h
    except Exception:
        pass


def register():
    global _handle
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), "WINDOW", "POST_PIXEL")


def unregister():
    global _handle
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None
