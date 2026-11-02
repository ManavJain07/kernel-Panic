"""Accessibility: commands you can click, and shortcuts you design yourself.

Why: some people cannot press certain keys or key combinations (one hand, limited
reach, switch or adaptive devices, a mouse with extra buttons ...).

What it gives
  * COMMANDS   the commands people use most in Blender (add, move, rotate, scale,
               delete, undo, edit mode, views ...) as big buttons. They work
               anywhere in Blender, not only in the tutorial.
  * Own shortcuts   every command can get a shortcut made of one to four steps,
               in the order you choose. Each step is a keyboard key OR a mouse
               button. A step is either "hold" (keep it pressed while you press
               the next one) or "tap" (press it and let go, then press the next
               one within 1.5 seconds). The last step is the one that runs the
               command. Examples:
                   Hold Shift, then press A          (the usual way, in order)
                   Press Q, then press W             (one key after the other)
                   Hold Mouse side button, then press G
  * Own commands   add any Blender operator (for example mesh.primitive_monkey_add)
               as a command with your own name; it can get a shortcut as well.
  * Tutorial   the lessons accept these shortcuts, show them on the task card
               ("Your keys: Move = Hold Shift, then press Q"), and the tutorial's
               own command list is shown in the Accessibility tab too.

The shortcuts are kept in  accessibility.json  next to the saved tutorial
progress. Blender's normal keys keep working; the key that finishes one of your
shortcuts is used up by it, so choose keys you do not need for something else.
"""
import json
import os
import sys
import time

import bpy
from bpy.app.handlers import persistent

SEQ_TIMEOUT = 1.5            # seconds allowed between "tap" steps
MAX_STEPS = 4
FLAGS = {"add_menu": "shift_a", "sel_vert": "key_1", "sel_edge": "key_2", "sel_face": "key_3"}


# ---------------------------------------------------------------------------
# Saved settings
# ---------------------------------------------------------------------------
_data = None


def _path():
    try:
        base = bpy.utils.extension_path_user(__package__, path="", create=True)
    except Exception:
        base = os.path.join(bpy.utils.user_resource("CONFIG"), "navigation_guide")
        os.makedirs(base, exist_ok=True)
    return os.path.join(base, "accessibility.json")


def data():
    global _data
    if _data is None:
        raw = {}
        try:
            with open(_path(), encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            pass
        shortcuts = {}
        for cid, steps in (raw.get("shortcuts") or {}).items():
            clean = [{"key": s["key"], "hold": bool(s.get("hold", True))}
                     for s in steps if isinstance(s, dict) and isinstance(s.get("key"), str)]
            if clean:
                shortcuts[cid] = clean[:MAX_STEPS]
        custom = [c for c in (raw.get("custom") or [])
                  if isinstance(c, dict) and all(isinstance(c.get(k), str) for k in ("id", "label", "op"))]
        _data = {"enabled": bool(raw.get("enabled", True)), "shortcuts": shortcuts,
                 "custom": custom, "next_id": int(raw.get("next_id", len(custom) + 1))}
    return _data


def save():
    try:
        path = _path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data(), f, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


def _redraw():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            area.tag_redraw()


# ---------------------------------------------------------------------------
# Names of keys and mouse buttons
# ---------------------------------------------------------------------------
_NAMES = {
    "LEFTMOUSE": "Left click", "MIDDLEMOUSE": "Middle click", "RIGHTMOUSE": "Right click",
    "BUTTON4MOUSE": "Mouse button 4", "BUTTON5MOUSE": "Mouse button 5",
    "BUTTON6MOUSE": "Mouse button 6", "BUTTON7MOUSE": "Mouse button 7",
    "WHEELUPMOUSE": "Wheel up", "WHEELDOWNMOUSE": "Wheel down",
    "LEFT_SHIFT": "Shift", "LEFT_CTRL": "Ctrl", "LEFT_ALT": "Alt",
    "OSKEY": "Cmd" if sys.platform == "darwin" else "Win",
    "ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5", "SIX": "6",
    "SEVEN": "7", "EIGHT": "8", "NINE": "9", "ZERO": "0", "SPACE": "Space",
    "RET": "Enter", "BACK_SPACE": "Backspace", "TAB": "Tab", "DEL": "Delete",
    "PERIOD": ".", "COMMA": ",", "SLASH": "/", "MINUS": "-", "EQUAL": "=",
}
_MOUSE_TYPES = {"LEFTMOUSE", "MIDDLEMOUSE", "RIGHTMOUSE", "BUTTON4MOUSE", "BUTTON5MOUSE",
                "BUTTON6MOUSE", "BUTTON7MOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"}
_IGNORE = {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE", "TIMER", "TIMER0", "TIMER1", "TIMER2",
           "TIMER_JOBS", "TIMER_AUTOSAVE", "TIMER_REPORT", "TIMERREGION", "NONE",
           "TEXTINPUT", "WINDOW_DEACTIVATE", "EVT_TWEAK_L", "EVT_TWEAK_M", "EVT_TWEAK_R",
           "MOUSEROTATE", "MOUSESMARTZOOM", "TRACKPADPAN", "TRACKPADZOOM"}
_MODIFIERS = {"LEFT_SHIFT", "LEFT_CTRL", "LEFT_ALT", "OSKEY"}


def normal(event_type):
    """Left and right Shift / Ctrl / Alt count as the same key."""
    return event_type.replace("RIGHT_", "LEFT_") if event_type.startswith("RIGHT_") and \
        event_type[6:] in {"SHIFT", "CTRL", "ALT"} else event_type


def nice(key):
    if key in _NAMES:
        return _NAMES[key]
    try:
        return bpy.types.KeyMapItem.bl_rna.properties["type"].enum_items[key].name
    except (KeyError, AttributeError, TypeError):
        return key.replace("_", " ").title()


def sequence_text(steps):
    """'Hold Shift, then press A' / 'Press Q, then press W' / 'Press F5'."""
    if not steps:
        return ""
    parts = [("Hold " if s.get("hold", True) else "Press ") + nice(s["key"]) for s in steps[:-1]]
    last = nice(steps[-1]["key"])
    if not parts:
        return f"Press {last}"
    return ", then ".join(parts) + f", then press {last}"


# ---------------------------------------------------------------------------
# The commands everybody uses
# ---------------------------------------------------------------------------

def _ops(path, *args, **kwargs):
    mod, name = path.split(".")
    getattr(getattr(bpy.ops, mod), name)(*args, **kwargs)


def _simple(path, *args, **kwargs):
    def run(ctx):
        _ops(path, *args, **kwargs)
    return run


def _axis_move(axis):
    def run(ctx):
        flags = [False, False, False]
        flags[axis] = True
        bpy.ops.transform.translate("INVOKE_DEFAULT", constraint_axis=tuple(flags))
    return run


def _start_lesson(ctx):
    from . import lesson
    return lesson.begin_from_key(ctx)


def _delete(ctx):
    if ctx.mode == "OBJECT":
        if not ctx.selected_objects:
            return "Nothing is selected."
        bpy.ops.object.delete()
    elif ctx.mode == "EDIT_MESH":
        bpy.ops.mesh.delete("INVOKE_DEFAULT")
    else:
        return "Switch to Object Mode first."


def _duplicate(ctx):
    if ctx.mode == "EDIT_MESH":
        bpy.ops.mesh.duplicate_move("INVOKE_DEFAULT")
    elif ctx.mode == "OBJECT":
        if not ctx.selected_objects:
            return "Nothing is selected."
        bpy.ops.object.duplicate_move("INVOKE_DEFAULT")
    else:
        return "Switch to Object Mode first."


def _select(action):
    def run(ctx):
        if ctx.mode == "EDIT_MESH":
            bpy.ops.mesh.select_all(action=action)
        else:
            bpy.ops.object.select_all(action=action)
    return run


def _edit_mode(ctx):
    obj = ctx.active_object
    if obj is None or obj.type != "MESH":
        return "Select a mesh object first."
    bpy.ops.object.mode_set(mode="OBJECT" if ctx.mode == "EDIT_MESH" else "EDIT")


def _select_mode(kind):
    def run(ctx):
        if ctx.mode != "EDIT_MESH":
            return "Switch to Edit Mode first."
        bpy.ops.mesh.select_mode(type=kind)
    return run


def _extrude(ctx):
    if ctx.mode != "EDIT_MESH":
        return "Switch to Edit Mode first."
    bpy.ops.view3d.edit_mesh_extrude_move_normal("INVOKE_DEFAULT")


def _shading(kind):
    def run(ctx):
        space = ctx.space_data
        if space is None or space.type != "VIEW_3D":
            return "Point at the 3D viewport first."
        space.shading.type = kind
    return run


# id, label, group, Blender's own shortcut (shown as a hint), function
GENERAL = (
    ("start", "Start the lesson", "Tutorial", "M", _start_lesson),
    ("add_menu", "Open the Add menu", "Add", "Shift + A", _simple("wm.call_menu", name="VIEW3D_MT_add")),
    ("add_cube", "Add a cube", "Add", "", _simple("mesh.primitive_cube_add")),
    ("add_plane", "Add a plane", "Add", "", _simple("mesh.primitive_plane_add")),
    ("add_sphere", "Add a sphere", "Add", "", _simple("mesh.primitive_uv_sphere_add")),
    ("add_cylinder", "Add a cylinder", "Add", "", _simple("mesh.primitive_cylinder_add")),
    ("add_monkey", "Add a monkey", "Add", "", _simple("mesh.primitive_monkey_add")),
    ("move", "Move (grab)", "Transform", "G", _simple("transform.translate", "INVOKE_DEFAULT")),
    ("move_x", "Move along X", "Transform", "G, X", _axis_move(0)),
    ("move_y", "Move along Y", "Transform", "G, Y", _axis_move(1)),
    ("move_z", "Move along Z", "Transform", "G, Z", _axis_move(2)),
    ("rotate", "Rotate", "Transform", "R", _simple("transform.rotate", "INVOKE_DEFAULT")),
    ("scale", "Scale", "Transform", "S", _simple("transform.resize", "INVOKE_DEFAULT")),
    ("delete", "Delete", "Edit", "Delete", _delete),
    ("duplicate", "Duplicate", "Edit", "Shift + D", _duplicate),
    ("extrude", "Extrude", "Edit", "E", _extrude),
    ("undo", "Undo", "Edit", "Ctrl / Cmd + Z", _simple("ed.undo")),
    ("redo", "Redo", "Edit", "Shift + Ctrl / Cmd + Z", _simple("ed.redo")),
    ("select_all", "Select all", "Select", "A", _select("SELECT")),
    ("deselect_all", "Select none", "Select", "Alt + A", _select("DESELECT")),
    ("invert_selection", "Invert selection", "Select", "Ctrl + I", _select("INVERT")),
    ("edit_mode", "Edit Mode on / off", "Mode", "Tab", _edit_mode),
    ("sel_vert", "Select vertices", "Mode", "1", _select_mode("VERT")),
    ("sel_edge", "Select edges", "Mode", "2", _select_mode("EDGE")),
    ("sel_face", "Select faces", "Mode", "3", _select_mode("FACE")),
    ("view_front", "Front view", "View", "Numpad 1", _simple("view3d.view_axis", type="FRONT")),
    ("view_right", "Right view", "View", "Numpad 3", _simple("view3d.view_axis", type="RIGHT")),
    ("view_top", "Top view", "View", "Numpad 7", _simple("view3d.view_axis", type="TOP")),
    ("view_camera", "Camera view", "View", "Numpad 0", _simple("view3d.view_camera")),
    ("frame_selected", "Zoom to selected", "View", "Numpad .", _simple("view3d.view_selected")),
    ("view_all", "Show everything", "View", "Home", _simple("view3d.view_all")),
    ("shade_solid", "Solid shading", "View", "", _shading("SOLID")),
    ("shade_material", "Material Preview", "View", "", _shading("MATERIAL")),
    ("save", "Save file", "File", "Ctrl / Cmd + S", _simple("wm.save_mainfile", "INVOKE_DEFAULT")),
)
REGISTRY = {c[0]: c for c in GENERAL}
GROUPS = ("Tutorial", "Add", "Transform", "Edit", "Select", "Mode", "View", "File")


def custom_by_id(cid):
    for c in data()["custom"]:
        if c["id"] == cid:
            return c
    return None


def all_ids():
    return [c[0] for c in GENERAL] + [c["id"] for c in data()["custom"]]


def label_of(cid):
    if cid in REGISTRY:
        return REGISTRY[cid][1]
    c = custom_by_id(cid)
    return c["label"] if c else cid


def run(cid, context):
    """Run a command (built-in or your own). Returns None or a short message."""
    from . import lesson
    try:
        if cid in REGISTRY:
            lesson.note_key(FLAGS.get(cid))
            return REGISTRY[cid][4](context)
        c = custom_by_id(cid)
        if c is None:
            return "That command no longer exists."
        _ops(c["op"], "INVOKE_DEFAULT")
    except RuntimeError as e:
        lines = str(e).strip().splitlines()
        return lines[-1] if lines else "That could not run here."
    except (AttributeError, TypeError, ReferenceError, ValueError):
        return "That is not possible right now."
    return None


def operator_exists(path):
    try:
        mod, name = path.strip().split(".")
        getattr(getattr(bpy.ops, mod), name)
        return True
    except (ValueError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# Your shortcuts: reading them for the tutorial
# ---------------------------------------------------------------------------

def steps_of(cid):
    return data()["shortcuts"].get(cid, [])


def mapped_keys():
    """{command id: 'Hold Shift, then press Q'} for every command that has a shortcut."""
    return {cid: sequence_text(steps) for cid, steps in data()["shortcuts"].items() if steps}


def start_label():
    return mapped_keys().get("start")


def step_line(step):
    """'Your keys: Move = Hold Shift, then press Q' for a lesson task, or None."""
    mine = mapped_keys()
    bits = [f"{label_of(a)} = {mine[a]}" for a in step.get("keys", ()) if a in mine]
    return "Your keys: " + ";  ".join(bits) if bits else None


def conflicts(cid):
    """Other commands that use exactly the same shortcut."""
    mine = [(s["key"], s.get("hold", True)) for s in steps_of(cid)]
    if not mine:
        return []
    return [other for other, steps in data()["shortcuts"].items()
            if other != cid and [(s["key"], s.get("hold", True)) for s in steps] == mine]


# ---------------------------------------------------------------------------
# The listener: watches the keys and mouse buttons and runs your shortcuts
# ---------------------------------------------------------------------------
_L = {"gen": 0, "held": set(), "recent": []}


def _find(cid_steps, key, now):
    held, recent = _L["held"], _L["recent"]
    if not cid_steps or normal(cid_steps[-1]["key"]) != key:
        return False
    allowed = {s["key"] for s in cid_steps[:-1]} | {key}
    if (held & _MODIFIERS) - allowed:
        return False                                  # e.g. Shift is held but not part of it
    pos = len(recent)
    for step in reversed(cid_steps[:-1]):
        k = step["key"]
        if step.get("hold", True):
            if k not in held:
                return False
        else:
            found = None
            for i in range(pos - 1, -1, -1):
                tk, tt = recent[i]
                if now - tt > SEQ_TIMEOUT:
                    break
                if tk == k:
                    found = i
                    break
            if found is None:
                return False
            pos = found
    return True


def match(key, now):
    """The command whose shortcut the key press just completed, or None."""
    best, best_len = None, 0
    for cid, steps in data()["shortcuts"].items():
        if _find(steps, key, now) and len(steps) > best_len:
            best, best_len = cid, len(steps)
    return best


def _area_under(window, event):
    for area in window.screen.areas:
        if area.x <= event.mouse_x < area.x + area.width and area.y <= event.mouse_y < area.y + area.height:
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            return area, region
    return None, None


class NAVGUIDE_OT_listener(bpy.types.Operator):
    """Runs in the background and carries out the shortcuts you made."""
    bl_idname = "navguide.shortcut_listener"
    bl_label = "Shortcut listener"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        _L["gen"] += 1
        self._gen = _L["gen"]
        _L["held"].clear()
        _L["recent"].clear()
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if self._gen != _L["gen"]:
            return {"CANCELLED", "PASS_THROUGH"}
        et = event.type
        if et == "WINDOW_DEACTIVATE":
            _L["held"].clear()
            return {"PASS_THROUGH"}
        if et in _IGNORE or not data()["enabled"]:
            return {"PASS_THROUGH"}
        key = normal(et)
        wheel = et in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}
        if event.value == "RELEASE":
            _L["held"].discard(key)
            return {"PASS_THROUGH"}
        if event.value != "PRESS" and not wheel:
            return {"PASS_THROUGH"}
        if getattr(event, "is_repeat", False):
            return {"PASS_THROUGH"}

        now = time.time()
        cid = match(key, now) if data()["shortcuts"] else None
        if cid:
            _L["recent"].clear()
            area, region = _area_under(context.window, event)
            try:
                with bpy.context.temp_override(window=context.window, area=area, region=region):
                    problem = run(cid, bpy.context)
            except (RuntimeError, ReferenceError, TypeError):
                problem = "That could not run here."
            if problem:
                self.report({"WARNING"}, problem)
            return {"RUNNING_MODAL"}                  # this key press belongs to the shortcut
        if not wheel:
            _L["held"].add(key)
        _L["recent"].append((key, now))
        del _L["recent"][:-8]
        return {"PASS_THROUGH"}


def _start_listener():
    wm = bpy.context.window_manager
    if not wm.windows:
        return 0.5
    try:
        with bpy.context.temp_override(window=wm.windows[0]):
            bpy.ops.navguide.shortcut_listener("INVOKE_DEFAULT")
    except Exception as exc:
        print("Navigation Guide: shortcut listener not started:", exc)
    return None


@persistent
def _on_load(*_args):
    if not bpy.app.timers.is_registered(_start_listener):
        bpy.app.timers.register(_start_listener, first_interval=1.0, persistent=True)


# ---------------------------------------------------------------------------
# Operators behind the Accessibility tab
# ---------------------------------------------------------------------------
_open = set()                  # commands whose shortcut editor is open


def _area_window_override(context):
    """Run commands in the 3D viewport's main region even when the click came from the sidebar."""
    area = context.area
    region = None
    if area is not None:
        region = next((r for r in area.regions if r.type == "WINDOW"), None)
    return region


class NAVGUIDE_OT_run_command(bpy.types.Operator):
    bl_idname = "navguide.run_command"
    bl_label = "Run command"
    bl_description = "Do this command now"
    bl_options = {"INTERNAL"}

    cid: bpy.props.StringProperty()
    tutorial: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        region = _area_window_override(context)
        with bpy.context.temp_override(region=region) if region else _null():
            if self.tutorial:
                from . import commands
                problem = commands.run(self.cid, bpy.context)
            else:
                problem = run(self.cid, bpy.context)
        if problem:
            self.report({"WARNING"}, problem)
            return {"CANCELLED"}
        return {"FINISHED"}


class _null:
    def __enter__(self): return None
    def __exit__(self, *a): return False


class NAVGUIDE_OT_sc_toggle(bpy.types.Operator):
    bl_idname = "navguide.sc_toggle"
    bl_label = "Shortcuts on / off"
    bl_description = "Switch all of your own shortcuts on or off"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        data()["enabled"] = not data()["enabled"]
        save()
        _redraw()
        return {"FINISHED"}


class NAVGUIDE_OT_sc_edit(bpy.types.Operator):
    bl_idname = "navguide.sc_edit"
    bl_label = "Edit shortcut"
    bl_description = "Show or hide the shortcut editor for this command"
    bl_options = {"INTERNAL"}

    cid: bpy.props.StringProperty()

    def execute(self, context):
        _open.symmetric_difference_update({self.cid})
        _redraw()
        return {"FINISHED"}


class NAVGUIDE_OT_sc_record(bpy.types.Operator):
    bl_idname = "navguide.sc_record"
    bl_label = "Pick a key"
    bl_description = "Press the key or click the mouse button you want to use for this step"
    bl_options = {"INTERNAL"}

    cid: bpy.props.StringProperty()
    index: bpy.props.IntProperty(default=-1)        # -1 = add as a new last step

    def invoke(self, context, event):
        context.workspace.status_text_set("Press the key or click the mouse button you want  -  Esc to cancel")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _done(self, context):
        context.workspace.status_text_set(None)

    def modal(self, context, event):
        et = event.type
        if et == "ESC":
            self._done(context)
            return {"CANCELLED"}
        if et in _IGNORE:
            return {"RUNNING_MODAL"}
        wheel = et in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}
        if event.value == "PRESS" or wheel:
            key = normal(et)
            steps = data()["shortcuts"].setdefault(self.cid, [])
            if 0 <= self.index < len(steps):
                steps[self.index]["key"] = key
            elif len(steps) < MAX_STEPS:
                if steps:
                    steps[-1]["hold"] = steps[-1].get("hold", True)
                steps.append({"key": key, "hold": True})
            save()
            self._done(context)
            _redraw()
            return {"FINISHED"}
        return {"RUNNING_MODAL"}


class NAVGUIDE_OT_sc_hold(bpy.types.Operator):
    bl_idname = "navguide.sc_hold"
    bl_label = "Hold or tap"
    bl_description = ("Hold = keep this key pressed while you press the next one.  "
                      "Tap = press it and let go, then press the next one within 1.5 seconds")
    bl_options = {"INTERNAL"}

    cid: bpy.props.StringProperty()
    index: bpy.props.IntProperty()

    def execute(self, context):
        steps = steps_of(self.cid)
        if 0 <= self.index < len(steps):
            steps[self.index]["hold"] = not steps[self.index].get("hold", True)
            save()
            _redraw()
        return {"FINISHED"}


class NAVGUIDE_OT_sc_remove(bpy.types.Operator):
    bl_idname = "navguide.sc_remove"
    bl_label = "Remove this key"
    bl_options = {"INTERNAL"}

    cid: bpy.props.StringProperty()
    index: bpy.props.IntProperty()

    def execute(self, context):
        steps = steps_of(self.cid)
        if 0 <= self.index < len(steps):
            del steps[self.index]
            if not steps:
                data()["shortcuts"].pop(self.cid, None)
            save()
            _redraw()
        return {"FINISHED"}


class NAVGUIDE_OT_sc_clear(bpy.types.Operator):
    bl_idname = "navguide.sc_clear"
    bl_label = "Clear shortcut"
    bl_description = "Remove the shortcut of this command (empty = every command)"
    bl_options = {"INTERNAL"}

    cid: bpy.props.StringProperty()

    def invoke(self, context, event):
        if not self.cid:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        if self.cid:
            data()["shortcuts"].pop(self.cid, None)
        else:
            data()["shortcuts"].clear()
        save()
        _redraw()
        return {"FINISHED"}


class NAVGUIDE_OT_cmd_add(bpy.types.Operator):
    bl_idname = "navguide.cmd_add"
    bl_label = "Add my own command"
    bl_options = {"INTERNAL"}

    cmd_label: bpy.props.StringProperty(name="Name", description="What the button says")
    op_name: bpy.props.StringProperty(
        name="Blender command",
        description="The operator name, for example  mesh.primitive_monkey_add  "
                    "(turn on Python Tooltips in Preferences > Interface to see it when you hover a button)")

    def invoke(self, context, event):
        self.cmd_label, self.op_name = "", ""
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "cmd_label")
        col.prop(self, "op_name")
        col.label(text="Example:  mesh.primitive_monkey_add", icon="INFO")

    def execute(self, context):
        op = self.op_name.strip()
        if not self.cmd_label.strip() or not operator_exists(op):
            self.report({"ERROR"}, "Give it a name and a real Blender command, like mesh.primitive_monkey_add")
            return {"CANCELLED"}
        d = data()
        cid = f"custom:{d['next_id']}"
        d["next_id"] += 1
        d["custom"].append({"id": cid, "label": self.cmd_label.strip(), "op": op})
        save()
        _redraw()
        return {"FINISHED"}


class NAVGUIDE_OT_cmd_remove(bpy.types.Operator):
    bl_idname = "navguide.cmd_remove"
    bl_label = "Remove my command"
    bl_options = {"INTERNAL"}

    cid: bpy.props.StringProperty()

    def execute(self, context):
        d = data()
        d["custom"] = [c for c in d["custom"] if c["id"] != self.cid]
        d["shortcuts"].pop(self.cid, None)
        save()
        _redraw()
        return {"FINISHED"}


classes = (NAVGUIDE_OT_listener, NAVGUIDE_OT_run_command, NAVGUIDE_OT_sc_toggle,
           NAVGUIDE_OT_sc_edit, NAVGUIDE_OT_sc_record, NAVGUIDE_OT_sc_hold,
           NAVGUIDE_OT_sc_remove, NAVGUIDE_OT_sc_clear, NAVGUIDE_OT_cmd_add,
           NAVGUIDE_OT_cmd_remove)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.app.handlers.load_post.append(_on_load)
    if not bpy.app.timers.is_registered(_start_listener):
        bpy.app.timers.register(_start_listener, first_interval=1.0, persistent=True)


def unregister():
    _L["gen"] += 1                       # stops a running listener
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if bpy.app.timers.is_registered(_start_listener):
        bpy.app.timers.unregister(_start_listener)
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
