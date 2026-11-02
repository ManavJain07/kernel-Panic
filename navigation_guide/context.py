"""Reads what the user is currently doing in Blender.

Everything the guide decides comes from here: one plain dict describing the
live state. Owner: navigation team.
"""

MODE_NAMES = {
    "OBJECT": "Object Mode",
    "EDIT_MESH": "Edit Mode (Mesh)",
    "SCULPT": "Sculpt Mode",
    "POSE": "Pose Mode",
    "PAINT_VERTEX": "Vertex Paint",
    "PAINT_WEIGHT": "Weight Paint",
    "PAINT_TEXTURE": "Texture Paint",
}


def _shading(context):
    """Viewport shading type (SOLID, MATERIAL, ...) or None if no 3D view."""
    try:
        space = getattr(context, "space_data", None)
        if space is not None and getattr(space, "type", "") == "VIEW_3D":
            return space.shading.type
        window = getattr(context, "window", None)
        if window is not None:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    return area.spaces.active.shading.type
    except Exception:
        pass
    return None


def get_state(context):
    """Return a plain dict describing the current Blender state."""
    obj = context.active_object

    try:
        objects = list(context.view_layer.objects)
        selected_count = sum(1 for o in objects if o.select_get())
    except Exception:
        objects = []
        selected_count = len(getattr(context, "selected_objects", []))

    state = {
        "mode_id": context.mode,
        "mode": MODE_NAMES.get(context.mode, context.mode.title()),
        "active_object": obj.name if obj else None,
        "active_type": obj.type if obj else None,
        "selected_count": selected_count,
        "object_count": len(objects),
        "mesh_object_count": sum(1 for o in objects if o.type == "MESH"),
        "dims": None,
        "bottom_z": None,
        "modifier_types": [],
        "ready_modifiers": [],
        "has_material": False,
        "shading": _shading(context),
        "rot_deg": None,
        "active_hidden": False,
        "saved": False,
    }

    try:
        import bpy  # only available inside Blender
        state["saved"] = bool(bpy.data.is_saved and not bpy.data.is_dirty)
    except Exception:
        pass

    if obj is not None:
        try:
            d = tuple(obj.dimensions)
            state["dims"] = {"x": d[0], "y": d[1], "z": d[2]}
            state["bottom_z"] = obj.location.z - d[2] / 2  # assumes origin at centre
        except Exception:
            pass
        try:
            import math
            r = obj.rotation_euler
            state["rot_deg"] = {"x": math.degrees(r.x), "y": math.degrees(r.y), "z": math.degrees(r.z)}
        except Exception:
            pass
        try:
            state["active_hidden"] = bool(obj.hide_get() or obj.hide_viewport)
        except Exception:
            pass
        try:
            for m in obj.modifiers:
                state["modifier_types"].append(m.type)
                if getattr(m, "object", None) is not None:
                    state["ready_modifiers"].append(m.type)
        except Exception:
            pass
        try:
            state["has_material"] = any(s.material for s in obj.material_slots)
        except Exception:
            pass
    return state


def get_hint(state):
    """Return (hint_text, shortcut) for the current state."""
    if state["active_object"] is None:
        return "Nothing is selected. Add an object to start.", "Shift + A"

    if state["selected_count"] == 0:
        return "Click an object in the viewport to select it.", "Left click"

    if state["mode_id"] == "OBJECT":
        if state["active_type"] == "MESH":
            return "You can move (G), rotate (R) or scale (S) the object. Press Tab to edit its shape.", "Tab"
        return "You can move (G), rotate (R) or scale (S) the object.", "G / R / S"

    if state["mode_id"] == "EDIT_MESH":
        return "You are editing the shape. Press Tab to go back to Object Mode.", "Tab"

    return "Press Tab or use the mode menu at the top-left to return to Object Mode.", "Tab"
