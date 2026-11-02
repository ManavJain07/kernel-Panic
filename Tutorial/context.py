"""Reads what the user is currently doing in Blender.

Everything the guide shows should come from here, so the panel stays
dumb and this file is the single place to extend detection.
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


def get_state(context):
    """Return a plain dict describing the current Blender state."""
    obj = context.active_object
    return {
        "mode_id": context.mode,
        "mode": MODE_NAMES.get(context.mode, context.mode.title()),
        "active_object": obj.name if obj else None,
        "active_type": obj.type if obj else None,
        "selected_count": len(context.selected_objects),
    }


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
