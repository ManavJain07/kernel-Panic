"""My Keys: let every learner choose their own keys for the tutorial actions.

Why: some people cannot press certain keys or combinations (one-handed use,
limited reach, switch / adaptive keyboards ...). Each action below can get an
extra key of the learner's own choice. Blender's normal keys keep working, and
the tutorial:
  * accepts the learner's key for the task (the add-on's own operator runs
    the same Blender command),
  * shows "Your keys: Move = Q" on the task card,
  * lets the learner start a lesson with their own key.

The keys are normal Blender keymap items (add-on key configuration), so they
are also visible and editable in Preferences > Keymap, and they are saved with
the user's preferences. By default no extra key is set.
"""
import sys
import time

import bpy

OP_ID = "navguide.key_action"
KEYMAP_NAME = "3D View"
SPACE_TYPE = "VIEW_3D"

# id, label in the sidebar, short name on the task card
KEY_ACTIONS = (
    ("start", "Start the lesson", "Start"),
    ("add_menu", "Open the Add menu", "Add menu"),
    ("move", "Move (grab)", "Move"),
    ("rotate", "Rotate", "Rotate"),
    ("scale", "Scale", "Scale"),
    ("edit_mode", "Edit Mode on / off", "Edit mode"),
    ("delete", "Delete", "Delete"),
    ("undo", "Undo", "Undo"),
    ("extrude", "Extrude", "Extrude"),
    ("sel_vert", "Select vertices", "Vertices"),
    ("sel_edge", "Select edges", "Edges"),
    ("sel_face", "Select faces", "Faces"),
)
LABELS = {a: lab for a, lab, _s in KEY_ACTIONS}
SHORT = {a: s for a, _l, s in KEY_ACTIONS}

# keys the detectors listen for (see detect.py)
KEY_FLAGS = {"add_menu": "shift_a", "sel_vert": "key_1", "sel_edge": "key_2",
             "sel_face": "key_3"}

_addon_items = []           # (keymap, item) pairs we created, removed on unregister
_cache = {"t": 0.0, "map": {}}


# ---------------------------------------------------------------------------
# Finding and describing the learner's keys
# ---------------------------------------------------------------------------

def _enum_name(kmi, attr):
    value = getattr(kmi, attr)
    try:
        return kmi.bl_rna.properties[attr].enum_items[value].name
    except (KeyError, AttributeError):
        return str(value).replace("_", " ").title()


def key_label(kmi):
    """Human readable text for a keymap item, e.g. 'Ctrl + Shift + Q'."""
    parts = []
    if kmi.key_modifier not in {"NONE", ""}:
        parts.append(_enum_name(kmi, "key_modifier"))
    if kmi.ctrl:
        parts.append("Ctrl")
    if kmi.alt:
        parts.append("Alt")
    if kmi.shift:
        parts.append("Shift")
    if kmi.oskey:
        parts.append("Cmd" if sys.platform == "darwin" else "Win")
    parts.append(_enum_name(kmi, "type"))
    return " + ".join(parts)


def _find(keyconfig, action):
    if keyconfig is None:
        return None
    km = keyconfig.keymaps.get(KEYMAP_NAME)
    if km is None:
        return None
    for kmi in km.keymap_items:
        if kmi.idname == OP_ID and kmi.properties.action == action:
            return km, kmi
    return None


def user_item(action):
    """(keymap, item) the learner edits. Falls back to the add-on's own item."""
    wm = bpy.context.window_manager
    return _find(wm.keyconfigs.user, action) or _find(wm.keyconfigs.addon, action)


def mapped_keys():
    """{action: 'Q'} for every action the learner gave a key (cached briefly)."""
    now = time.time()
    if now - _cache["t"] < 0.5:
        return _cache["map"]
    result = {}
    try:
        for action, _label, _short in KEY_ACTIONS:
            found = user_item(action)
            if found and found[1].active and found[1].type != "NONE":
                result[action] = key_label(found[1])
    except (AttributeError, RuntimeError, ReferenceError):
        result = {}
    _cache.update(t=now, map=result)
    return result


def step_line(step):
    """'Your keys: Move = Q' for a lesson step, or None if nothing is mapped."""
    mine = mapped_keys()
    bits = [f"{SHORT[a]} = {mine[a]}" for a in step.get("keys", ()) if a in mine]
    return "Your keys: " + ",  ".join(bits) if bits else None


def start_label():
    return mapped_keys().get("start")


# ---------------------------------------------------------------------------
# What each key does
# ---------------------------------------------------------------------------

def _run(context, action):
    """Run the Blender command for an action. Returns None or a message."""
    ops = bpy.ops
    mode = context.mode
    if action == "add_menu":
        ops.wm.call_menu(name="VIEW3D_MT_add")
    elif action == "move":
        ops.transform.translate("INVOKE_DEFAULT")
    elif action == "rotate":
        ops.transform.rotate("INVOKE_DEFAULT")
    elif action == "scale":
        ops.transform.resize("INVOKE_DEFAULT")
    elif action == "edit_mode":
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            return "Select a mesh object first."
        ops.object.mode_set(mode="OBJECT" if mode == "EDIT_MESH" else "EDIT")
    elif action == "delete":
        if mode == "OBJECT":
            if not context.selected_objects:
                return "Nothing is selected."
            ops.object.delete()
        elif mode == "EDIT_MESH":
            ops.mesh.delete("INVOKE_DEFAULT")
        else:
            return "Switch to Object Mode first."
    elif action == "undo":
        ops.ed.undo()
    elif action == "extrude":
        if mode != "EDIT_MESH":
            return "Press Tab (or your Edit Mode key) first."
        ops.view3d.edit_mesh_extrude_move_normal("INVOKE_DEFAULT")
    elif action in {"sel_vert", "sel_edge", "sel_face"}:
        if mode != "EDIT_MESH":
            return "Switch to Edit Mode first."
        kind = {"sel_vert": "VERT", "sel_edge": "EDGE", "sel_face": "FACE"}[action]
        ops.mesh.select_mode(type=kind)
    return None


class NAVGUIDE_OT_key_action(bpy.types.Operator):
    """Runs one tutorial action. The learner's own key is attached to this."""
    bl_idname = OP_ID
    bl_label = "Tutorial key"
    bl_options = {"INTERNAL"}

    action: bpy.props.StringProperty(default="")

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        from . import lesson            # late import: lesson imports this module
        if self.action == "start":
            problem = lesson.begin_from_key(context)
        else:
            lesson.note_key(KEY_FLAGS.get(self.action))
            try:
                problem = _run(context, self.action)
            except RuntimeError as e:
                lines = str(e).strip().splitlines()
                problem = lines[-1] if lines else "That could not run here."
        if problem:
            self.report({"WARNING"}, problem)
            return {"CANCELLED"}
        return {"FINISHED"}


class NAVGUIDE_OT_clear_key(bpy.types.Operator):
    bl_idname = "navguide.clear_key"
    bl_label = "Clear my key"
    bl_description = "Remove your own key (Blender's normal key still works)"
    bl_options = {"INTERNAL"}

    action: bpy.props.StringProperty(default="")      # empty = every action

    def execute(self, context):
        for action, _label, _short in KEY_ACTIONS:
            if self.action and self.action != action:
                continue
            found = user_item(action)
            if found:
                km, kmi = found
                kmi.type = "NONE"
                kmi.shift = kmi.ctrl = kmi.alt = kmi.oskey = False
                kmi.key_modifier = "NONE"
        _cache["t"] = 0.0
        return {"FINISHED"}


classes = (NAVGUIDE_OT_key_action, NAVGUIDE_OT_clear_key)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:                       # e.g. Blender running in the background
        return
    km = kc.keymaps.new(name=KEYMAP_NAME, space_type=SPACE_TYPE)
    for action, _label, _short in KEY_ACTIONS:
        kmi = km.keymap_items.new(OP_ID, type="NONE", value="PRESS")
        kmi.properties.action = action
        _addon_items.append((km, kmi))


def unregister():
    for km, kmi in _addon_items:
        try:
            km.keymap_items.remove(kmi)
        except (RuntimeError, ReferenceError):
            pass
    _addon_items.clear()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
