"""Task detectors.

Every task in lessons.json has a  "detect": "<name>"  entry. The name is looked
up in DETECTORS below. A detector is a pair  (init, check):

  init(env)   optional. Runs once when the task becomes the current task, to
              remember a starting point (object count, transform, ...).
  check(env)  runs about ten times a second while the task is current.
              Returns (done, message). `message` is a short "not yet" hint
              shown under the task, or None.

`env.base` is a dict that is private to the current task. `env.flags` holds
key presses seen by the lesson (for example "shift_a" or "undo") since the
task became current.

Only the current task is ever checked, so tasks must be done in order.
"""
import bmesh
import bpy

TOL = 0.05          # tolerance for typed numbers (scale 4, 0.2, 1.5 ...)
EPS = 1e-3          # "this value changed"

# How much camera movement counts as "did it" for orbit / pan / zoom.
THRESH = {
    "orbit": 0.7,   # radians of total rotation (~40 degrees)
    "pan": 0.35,    # total slide, as a fraction of the view distance
    "zoom": 0.30,   # total zoom, as a fraction of the view distance
}

DEFAULT_COLOR = (0.8, 0.8, 0.8)


class Env:
    """What a detector is allowed to look at."""

    def __init__(self, windows, acc, flags, base, wm=None):
        self.wm = wm
        self.windows = windows
        self.acc = acc
        self.flags = flags
        self.base = base
        win = windows[0] if windows else None
        self.scene = win.scene if win else None
        self.vl = win.view_layer if win else None

    @property
    def objects(self):
        return list(self.vl.objects) if self.vl else []

    @property
    def meshes(self):
        return [o for o in self.objects if o.type == "MESH"]

    @property
    def selected(self):
        vl = self.vl
        return [o for o in self.objects if o.select_get(view_layer=vl)]

    @property
    def obj(self):
        return self.vl.objects.active if self.vl else None

    @property
    def mode(self):
        o = self.obj
        return o.mode if o else "OBJECT"

    def areas(self, kind):
        for win in self.windows:
            for area in win.screen.areas:
                if area.type == kind:
                    yield area


# ---------------------------------------------------------------- helpers ---

def _tf(obj):
    return (tuple(obj.location), tuple(obj.rotation_euler),
            tuple(obj.rotation_quaternion), tuple(obj.scale), obj.name)


def _differs(a, b, eps=EPS):
    return any(abs(x - y) > eps for x, y in zip(a, b))


def _in_edit(env):
    o = env.obj
    return o is not None and o.type == "MESH" and o.mode == "EDIT"


def _bm(env):
    return bmesh.from_edit_mesh(env.obj.data)


def _coords(env):
    return [tuple(v.co) for v in _bm(env).verts]


def _mesh_count(env):
    return len(env.meshes)


# ----------------------------------------------------- camera (lesson 1) ---

def _camera(name):
    def check(env):
        got = env.acc[name]
        if got >= THRESH[name]:
            return True, None
        if got > 0.03 * THRESH[name]:
            return False, f"{int(100 * got / THRESH[name])}% there - keep going."
        return False, None
    return None, check


# ----------------------------------------------------------- selecting -----

def _select_init(env):
    env.base["had_empty"] = False


def _select_check(env):
    if not env.objects:
        return False, "Nothing to select yet. Add a cube first (Shift + A > Mesh > Cube)."
    n = len(env.selected)
    if n == 0:
        env.base["had_empty"] = True
        return False, "Good, nothing is selected. Now click the object."
    if env.base.get("had_empty"):
        return True, None
    return False, "Click empty space first to deselect, then click the object."


# ------------------------------------------------------- add / delete ------

def _objs_init(env):
    env.base["objs"] = len(env.objects)
    env.base["meshes"] = _mesh_count(env)


def _add_menu_check(env):
    if "shift_a" in env.flags or len(env.objects) > env.base["objs"]:
        return True, None
    return False, "Hover over the 3D viewport and press Shift + A."


def _add_cube_check(env):
    if _mesh_count(env) > env.base["meshes"]:
        return True, None
    return False, "In the Add menu choose Mesh, then Cube - or click 'Add a cube'."


def _delete_check(env):
    if len(env.objects) < env.base["objs"]:
        return True, None
    if not env.selected:
        return False, "Nothing is selected. Click the object first."
    if env.mode != "OBJECT":
        return False, "Press Tab to get back to Object Mode first."
    return False, "Hover over the viewport and press Delete."


# ------------------------------------------------------ transforms ---------

def _tf_init(env):
    o = env.obj
    env.base["tf"] = _tf(o) if o else None


def _tf_state(env):
    """Return (obj, start, now) or (None, None, message)."""
    o = env.obj
    if o is None or not o.select_get(view_layer=env.vl):
        return None, None, "Select an object first (click it)."
    if env.mode != "OBJECT":
        return None, None, "Press Tab to get back to Object Mode first."
    now = _tf(o)
    start = env.base.get("tf")
    if start is None or start[4] != now[4]:
        env.base["tf"] = now
        return None, None, None
    return o, start, now


def _move_check(env):
    o, start, now = _tf_state(env)
    if o is None:
        return False, now
    if _differs(start[0], now[0]):
        return True, None
    return False, "Hover over the viewport, press G, move the mouse, then click."


def _move_axis_check(env):
    """Judge each separate move (grab) on its own, not the total since the
    task started. A free move first no longer blocks the task: the user can
    just try again with G, then X / Y / Z."""
    o, start, now = _tf_state(env)
    if o is None:
        env.base.pop("gstart", None)
        return False, now
    b = env.base
    loc = now[0]
    last = b.get("last", loc)
    b["last"] = loc
    if _differs(last, loc):                 # the object is moving right now
        b.setdefault("gstart", last)
        b["still"] = 0
        return False, b.get("axis_msg")
    if "gstart" in b:                       # it stopped: was that one move?
        b["still"] = b.get("still", 0) + 1
        if b["still"] >= 2:                 # still for ~0.2 s = move finished
            first = b.pop("gstart")
            b["still"] = 0
            changed = sum(abs(a - c) > EPS for a, c in zip(first, loc))
            if changed == 1:
                return True, None
            if changed > 1:
                b["axis_msg"] = ("That moved it in several directions. "
                                 "No need to undo - just try again: G, then X, Y or Z.")
    return False, b.get("axis_msg") or "Press G, then X, Y or Z, move the mouse and click."


def _rotate_check(env):
    o, start, now = _tf_state(env)
    if o is None:
        return False, now
    if _differs(start[1], now[1]) or _differs(start[2], now[2]):
        return True, None
    return False, "Hover over the viewport, press R, move the mouse, then click."


def _scale_check(env):
    o, start, now = _tf_state(env)
    if o is None:
        return False, now
    if _differs(start[3], now[3]):
        return True, None
    return False, "Hover over the viewport, press S, move the mouse, then click."


def _undo_check(env):
    if "undo" in env.flags:
        return True, None
    return False, "Press Ctrl + Z (Cmd + Z on Mac) with the mouse over the viewport."


# ------------------------------------------------------- edit mode ---------

def _edit_mode_check(env):
    if _in_edit(env):
        return True, None
    o = env.obj
    if o is None or o.type != "MESH":
        return False, "Select a mesh object first (click the cube)."
    return False, "Hover over the viewport and press Tab."


def _object_mode_check(env):
    if env.obj is not None and env.mode == "OBJECT":
        return True, None
    if env.obj is None:
        return False, "Click an object, then press Tab."
    return False, "Press Tab to leave Edit Mode."


def _modes_init(env):
    env.base["seen"] = set()
    env.base["prev"] = None


def _modes_check(env):
    if not _in_edit(env):
        return False, "You left Edit Mode. Press Tab to go back in."
    seen = env.base["seen"]
    for key, idx in (("key_1", 0), ("key_2", 1), ("key_3", 2)):
        if key in env.flags:
            seen.add(idx)
    cur = tuple(env.scene.tool_settings.mesh_select_mode)
    if env.base["prev"] is not None and cur != env.base["prev"]:
        seen.update(i for i, on in enumerate(cur) if on)
    env.base["prev"] = cur
    if seen >= {0, 1, 2}:
        return True, None
    left = [f"{n} ({name})" for n, name, i in
            ((1, "vertices", 0), (2, "edges", 1), (3, "faces", 2)) if i not in seen]
    return False, "Still to try: " + ", ".join(left) + "."


def _face_move_init(env):
    env.base["co"] = _coords(env) if _in_edit(env) else None


def _face_move_check(env):
    if not _in_edit(env):
        return False, "You left Edit Mode. Press Tab to go back in."
    if env.base.get("co") is None:
        env.base["co"] = _coords(env)
    mode = tuple(env.scene.tool_settings.mesh_select_mode)
    faces_sel = sum(1 for f in _bm(env).faces if f.select)
    now = _coords(env)
    old = env.base["co"]
    moved = len(now) != len(old) or any(_differs(a, b) for a, b in zip(now, old))
    if moved and mode[2] and faces_sel:
        return True, None
    if not mode[2]:
        return False, "Press 3 for face selection."
    if not faces_sel:
        return False, "Click one face of the cube."
    return False, "Now press G, move the mouse, and click to confirm."


def _one_face_check(env):
    if not _in_edit(env):
        return False, "You left Edit Mode. Press Tab to go back in."
    if not env.scene.tool_settings.mesh_select_mode[2]:
        return False, "Press 3 for face selection."
    n = sum(1 for f in _bm(env).faces if f.select)
    if n == 1:
        return True, None
    if n == 0:
        return False, "Click one face of the cube."
    return False, f"{n} faces are selected. Click a single face."


def _extrude_init(env):
    env.base["verts"] = len(_bm(env).verts) if _in_edit(env) else None


def _extrude_check(env):
    if not _in_edit(env):
        return False, "You left Edit Mode. Press Tab to go back in."
    if env.base.get("verts") is None:
        env.base["verts"] = len(_bm(env).verts)
    if len(_bm(env).verts) > env.base["verts"]:
        return True, None
    return False, "With one face selected, press E and move the mouse."


# ------------------------------------------------------- materials ---------

def _tab_check(env):
    for area in env.areas("PROPERTIES"):
        if area.spaces.active.context == "MATERIAL":
            return True, None
    if not any(True for _ in env.areas("PROPERTIES")):
        return False, "The Properties editor is hidden. Press Ctrl + Space over it to restore the layout."
    return False, "Click the round sphere icon in the tab column of the Properties editor."


def _base_color(mat):
    tree = getattr(mat, "node_tree", None)
    if tree:
        for node in tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                return tuple(node.inputs["Base Color"].default_value)[:3]
    return tuple(mat.diffuse_color)[:3]


def _color_check(env):
    o = env.obj
    if o is None or o.type != "MESH":
        return False, "Select the object you want to colour."
    mat = o.active_material
    if mat is None:
        return False, "In the Material tab, click New."
    if _differs(_base_color(mat), DEFAULT_COLOR, 0.02):
        return True, None
    return False, "Click the Base Color box and pick a colour."


def _preview_check(env):
    for area in env.areas("VIEW_3D"):
        if area.spaces.active.shading.type in {"MATERIAL", "RENDERED"}:
            return True, None
    return False, "Click the third sphere icon at the top-right of the viewport."


# ------------------------------------------------------------ the wall -----

def _delete_cube_check(env):
    if _mesh_count(env) == 0 or len(env.objects) < env.base["objs"]:
        return True, None
    if not env.selected:
        return False, "Click the cube to select it, then press Delete."
    return False, "Hover over the viewport and press Delete."


def _scale_axis(axis, want, how):
    def check(env):
        o = env.obj
        if o is None or o.type != "MESH":
            return False, "Select the cube first."
        if env.mode != "OBJECT":
            return False, "Press Tab to get back to Object Mode first."
        if abs(o.scale[axis] - want) <= TOL:
            return True, None
        return False, f"{how}  (it is {o.scale[axis]:.2f} now, it should be {want}.)"
    return check


def _on_ground_check(env):
    from mathutils import Vector
    o = env.obj
    if o is None or o.type != "MESH":
        return False, "Select the wall first."
    low = min((o.matrix_world @ Vector(c)).z for c in o.bound_box)
    if abs(low) <= TOL and abs(o.scale[2] - 1.5) <= TOL:
        return True, None
    return False, "Press G, then Z, type 1.5 and press Enter."


# ---------------------------------------------- waiting for the click ------
# Move / rotate / scale / extrude tasks are only finished when the user CONFIRMS
# the change (left click or Enter). A confirmed change shows up as a new
# operator at the end of wm.operators. While the object has changed but there
# is no new operator yet, the card says "Now click to confirm".
# Fallbacks, so nobody is ever stuck:
#   * "instant" in env.flags : the accessible-mode command buttons set it,
#     because they apply the change in one go.
#   * the value has been still for 1.5 s (typed into the sidebar, for example).
#   * wm.operators cannot be read in this Blender: the older checks above run.

CLICK_MSG = "Now click (or press Enter) to confirm. Esc cancels."


def _ops_readable(env):
    try:
        len(env.wm.operators)
        return True
    except Exception:
        return False


def _last_sig(env, match):
    """Signature of the most recent operator if its name contains one of the
    words in `match`, else None."""
    try:
        ops = env.wm.operators
        if not len(ops):
            return None
        op = ops[-1]
        name = op.bl_idname.upper()
        if not any(m in name for m in match):
            return None
        try:
            val = str(tuple(op.properties.value))
        except Exception:
            val = ""
        return (op.as_pointer(), name, val)
    except Exception:
        return None


def _confirm_init(match, base_init=None):
    def init(env):
        if base_init:
            base_init(env)
        env.base["ops_ok"] = _ops_readable(env)
        env.base["sig"] = _last_sig(env, match)
        env.base["still"] = 0
        env.base["prev"] = None
    return init


def _is_new(env, match):
    """True once (and only once) for each newly confirmed operator."""
    sig = _last_sig(env, match)
    if sig is not None and sig != env.base.get("sig"):
        env.base["sig"] = sig
        return True
    return False


def _stable(env, now):
    """How many checks in a row `now` has stayed the same."""
    b = env.base
    b["still"] = b.get("still", 0) + 1 if b.get("prev") == now else 0
    b["prev"] = now
    return b["still"]


def _kind_changed(kind, start, now):
    if kind in ("move", "axis"):
        if kind == "axis":
            return sum(abs(a - c) > EPS for a, c in zip(start[0], now[0])) == 1
        return _differs(start[0], now[0])
    if kind == "rotate":
        return _differs(start[1], now[1]) or _differs(start[2], now[2])
    return _differs(start[3], now[3])


def _axis_ok(env):
    """Was the move that was just confirmed locked to one direction?"""
    try:
        props = env.wm.operators[-1].properties
        axis = tuple(props.constraint_axis)
        locked = sum(bool(a) for a in axis) == 1
    except Exception:
        locked = False
    try:
        value = tuple(env.wm.operators[-1].properties.value)
        one_dir = sum(abs(v) > EPS for v in value) == 1
    except Exception:
        one_dir = False
    return locked or one_dir


FREE_MOVE_MSG = ("That moved it freely. Try again: press G, then X, Y or Z, "
                 "move the mouse and click.")


def _confirm_xform(match, fallback, kind, tip):
    def check(env):
        b = env.base
        if env.wm is None or not b.get("ops_ok"):
            return fallback(env)
        o = env.obj
        if o is None or not o.select_get(view_layer=env.vl):
            return False, "Select an object first (click it)."
        if env.mode != "OBJECT":
            return False, "Press Tab to get back to Object Mode first."
        now = _tf(o)
        if b.get("tf") is None or b["tf"][4] != now[4]:
            b["tf"] = now
            return False, None
        if _is_new(env, match):
            ok = kind != "axis" or _axis_ok(env)
            b["tf"] = now
            return (True, None) if ok else (False, FREE_MOVE_MSG)
        changed = _kind_changed(kind, b["tf"], now)
        still = _stable(env, now)
        if changed and ("instant" in env.flags or still >= 15):
            return True, None
        if _differs(b["tf"][0], now[0]) or _differs(b["tf"][1], now[1]) or \
                _differs(b["tf"][3], now[3]):
            return False, CLICK_MSG
        return False, tip
    return check


def _confirm_extrude(env):
    b = env.base
    if env.wm is None or not b.get("ops_ok"):
        return _extrude_check(env)
    if not _in_edit(env):
        return False, "You left Edit Mode. Press Tab to go back in."
    if b.get("verts") is None:
        b["verts"] = len(_bm(env).verts)
    more = len(_bm(env).verts) > b["verts"]
    if more and (_is_new(env, ("EXTRUDE",)) or "instant" in env.flags):
        return True, None
    if more:
        return False, "Now click to confirm the extrusion. Esc cancels."
    return False, "With one face selected, press E and move the mouse."


def _confirm_face_move(env):
    b = env.base
    if env.wm is None or not b.get("ops_ok"):
        return _face_move_check(env)
    if not _in_edit(env):
        return False, "You left Edit Mode. Press Tab to go back in."
    if b.get("co") is None:
        b["co"] = _coords(env)
    mode = tuple(env.scene.tool_settings.mesh_select_mode)
    if not mode[2]:
        return False, "Press 3 for face selection."
    if not any(f.select for f in _bm(env).faces):
        return False, "Click one face of the cube."
    now, old = _coords(env), b["co"]
    moved = len(now) != len(old) or any(_differs(a, c) for a, c in zip(now, old))
    if moved and (_is_new(env, ("TRANSFORM_OT_TRANSLATE",)) or "instant" in env.flags):
        return True, None
    if moved:
        return False, "Now click to confirm the move. Esc cancels."
    return False, "Now press G, move the mouse, and click to confirm."


def _confirm_value(match, ok_fn, tip):
    """Wall tasks: the value must be right AND confirmed."""
    def check(env):
        b = env.base
        o = env.obj
        if o is None or o.type != "MESH":
            return False, "Select the cube first."
        if env.mode != "OBJECT":
            return False, "Press Tab to get back to Object Mode first."
        ok, now_msg = ok_fn(env, o)
        if not ok:
            b["still"] = 0
            return False, now_msg or tip
        if not b.get("ops_ok") or env.wm is None:
            return True, None
        still = _stable(env, _tf(o))
        if _is_new(env, match) or "instant" in env.flags or still >= 15:
            return True, None
        return False, "Right value. Now press Enter (or click) to confirm."
    return check


def _scale_is(axis, want, how):
    def ok(env, o):
        if abs(o.scale[axis] - want) <= TOL:
            return True, None
        return False, f"{how}  (it is {o.scale[axis]:.2f} now, it should be {want}.)"
    return ok


def _lifted(env, o):
    from mathutils import Vector
    low = min((o.matrix_world @ Vector(c)).z for c in o.bound_box)
    if abs(low) <= TOL and abs(o.scale[2] - 1.5) <= TOL:
        return True, None
    return False, "Press G, then Z, type 1.5 and press Enter."


_T, _R, _S_ = ("TRANSFORM_OT_TRANSLATE",), ("TRANSFORM_OT_ROTATE",), ("TRANSFORM_OT_RESIZE",)

# ===========================================================================
# Lessons 8 - 20
# ===========================================================================

def _lowest_z(o):
    from mathutils import Vector
    return min((o.matrix_world @ Vector(c)).z for c in o.bound_box)


def _highest_z(o):
    from mathutils import Vector
    return max((o.matrix_world @ Vector(c)).z for c in o.bound_box)


def _named(env, prefix, kind="MESH"):
    return [o for o in env.objects if o.type == kind and o.name.startswith(prefix)]


# ---- "what did Blender just do?" (operator history) -----------------------
# Used where the result of a tool cannot be told from the scene alone
# (loop cut, inset, bevel, join, separate). Falls back to counting vertices /
# objects if this Blender does not give us the history.

def _op_ptrs():
    try:
        return {op.as_pointer() for op in bpy.context.window_manager.operators}
    except (AttributeError, RuntimeError, ReferenceError):
        return set()


def _norm_op(name):
    return name.lower().replace("_ot_", ".")


def _op_seen(env, names):
    want = {_norm_op(n) for n in names}
    old = env.base.get("ptrs", set())
    try:
        for op in bpy.context.window_manager.operators:
            if op.as_pointer() not in old and _norm_op(op.bl_idname) in want:
                return True
    except (AttributeError, RuntimeError, ReferenceError):
        pass
    return False


def _op_history_works():
    try:
        return len(bpy.context.window_manager.operators) > 0
    except (AttributeError, RuntimeError, ReferenceError):
        return False


def _edit_tool(names, msg):
    """A tool used in Edit Mode: done when the operator ran (or, if Blender
    keeps no history, when the vertex count grew)."""
    def init(env):
        env.base["ptrs"] = _op_ptrs()
        env.base["n0"] = len(_bm(env).verts) if _in_edit(env) else 0

    def check(env):
        if not _in_edit(env):
            return False, "You left Edit Mode. Press Tab to go back in."
        if _op_seen(env, names):
            return True, None
        if not _op_history_works() and len(_bm(env).verts) > env.base.get("n0", 0):
            return True, None
        return False, msg
    return init, check


def _object_tool(names, count_fallback, msg):
    """A tool used on objects (join / separate). count_fallback(env, n0) -> bool."""
    def init(env):
        env.base["ptrs"] = _op_ptrs()
        env.base["n0"] = _mesh_count(env)

    def check(env):
        if _op_seen(env, names):
            return True, None
        if not _op_history_works() and count_fallback(_mesh_count(env), env.base["n0"]):
            return True, None
        return False, msg
    return init, check


# ---- lesson 8: duplicate and select many ----------------------------------

def _dup_check(env):
    if len(env.objects) > env.base["objs"]:
        return True, None
    if not env.selected:
        return False, "Click the cube to select it first."
    return False, "Hover over the viewport, press Shift + D, move the mouse and click."


def _multi_select_check(env):
    n = len(env.selected)
    if n >= 2:
        return True, None
    if len(env.objects) < 2:
        return False, "You need two objects. Go back and duplicate the cube (Shift + D)."
    return False, "Hold Shift and click the other object, so that two are selected."


def _selectable(env):
    return [o for o in env.objects if not o.hide_get(view_layer=env.vl) and not o.hide_select]


def _select_all_init(env):
    env.base["partial"] = False


def _select_all_check(env):
    sel = _selectable(env)
    n = len([o for o in sel if o.select_get(view_layer=env.vl)])
    if len(sel) >= 2 and n == len(sel):
        if env.base["partial"]:
            return True, None
        return False, "Click empty space to deselect, then press A."
    env.base["partial"] = True
    return False, "Hover over the viewport and press A."


def _deselect_all_init(env):
    env.base["had"] = False


def _deselect_all_check(env):
    n = len(env.selected)
    if n:
        env.base["had"] = True
        return False, "Hover over the viewport and press Alt + A (Option + A on Mac)."
    if env.base["had"]:
        return True, None
    return False, "Select something first (press A), then press Alt + A."


# ---- lesson 9: views ------------------------------------------------------

def _r3d(env):
    best = None
    for area in env.areas("VIEW_3D"):
        sp = area.spaces.active
        r3d = getattr(sp, "region_3d", None)
        if r3d is not None and (best is None or area.width * area.height > best[0]):
            best = (area.width * area.height, sp, r3d)
    return (best[1], best[2]) if best else (None, None)


def _view_is(rot, label):
    def check(env):
        from mathutils import Quaternion
        _sp, r3d = _r3d(env)
        if r3d is None:
            return False, "Open a 3D viewport first."
        if abs(r3d.view_rotation.dot(Quaternion(rot))) > 0.995:
            return True, None
        return False, f"Press Numpad {label[0]}, or use View > Viewpoint > {label[1]}."
    return None, check


def _persp_init(env):
    _sp, r3d = _r3d(env)
    env.base["persp"] = r3d.is_perspective if r3d else None


def _persp_check(env):
    _sp, r3d = _r3d(env)
    if r3d is None:
        return False, "Open a 3D viewport first."
    if env.base.get("persp") is None:
        env.base["persp"] = r3d.is_perspective
    if r3d.is_perspective != env.base["persp"]:
        return True, None
    return False, "Press Numpad 5, or View > Perspective / Orthographic."


def _vframe_init(env):
    _sp, r3d = _r3d(env)
    if r3d:
        env.base["loc"] = tuple(r3d.view_location)
        env.base["dist"] = r3d.view_distance


def _vframe_check(env):
    _sp, r3d = _r3d(env)
    o = env.obj
    if r3d is None or "loc" not in env.base:
        return False, None
    if o is None or not o.select_get(view_layer=env.vl):
        return False, "Click the cube to select it first."
    moved = (_differs(env.base["loc"], tuple(r3d.view_location), 0.05)
             or abs(r3d.view_distance - env.base["dist"]) > 0.3)
    near = (r3d.view_location - o.matrix_world.translation).length < 1.5
    if moved and near:
        return True, None
    return False, "Press Numpad . (period), or View > Frame Selected."


# ---- lesson 10: shapes ----------------------------------------------------

def _names_init(env):
    env.base["names"] = {o.name for o in env.objects}


def _added(prefix, how):
    def check(env):
        for o in env.objects:
            if o.name not in env.base["names"] and o.name.startswith(prefix):
                return True, None
        return False, how
    return _names_init, check


def _added_type(kind, how):
    def init(env):
        env.base["n0"] = len([o for o in env.objects if o.type == kind])

    def check(env):
        if len([o for o in env.objects if o.type == kind]) > env.base["n0"]:
            return True, None
        return False, how
    return init, check


# ---- lesson 11: shading modes ---------------------------------------------

def _shading_types(env):
    return [a.spaces.active.shading for a in env.areas("VIEW_3D")]


def _wire_check(env):
    if any(s.type == "WIREFRAME" for s in _shading_types(env)):
        return True, None
    return False, "Press Shift + Z, or click the first (wireframe) sphere at the top right."


def _solid_init(env):
    env.base["other"] = False


def _solid_check(env):
    types = [s.type for s in _shading_types(env)]
    if any(x != "SOLID" for x in types):
        env.base["other"] = True
    if types and all(x == "SOLID" for x in types) and env.base["other"]:
        return True, None
    return False, "Press Shift + Z again, or click the second (solid) sphere."


def _xray_check(env):
    for s in _shading_types(env):
        if s.type == "SOLID" and s.show_xray:
            return True, None
        if s.type == "WIREFRAME" and s.show_xray_wireframe:
            return True, None
    return False, "Press Alt + Z (Option + Z on Mac), or the X-ray button next to the shading buttons."


# ---- lesson 12: names, hiding, collections ----------------------------------

def _rename_init(env):
    env.base["names"] = sorted(o.name for o in env.objects)


def _rename_check(env):
    now = sorted(o.name for o in env.objects)
    if len(now) == len(env.base["names"]) and now != env.base["names"]:
        return True, None
    if env.obj is None:
        return False, "Click an object first."
    return False, "Hover over the viewport, press F2, type a new name and press Enter."


def _hidden(env):
    return [o for o in env.objects if o.hide_get(view_layer=env.vl)]


def _hide_init(env):
    env.base["h0"] = len(_hidden(env))


def _hide_check(env):
    if len(_hidden(env)) > env.base["h0"]:
        return True, None
    if not env.selected:
        return False, "Click an object first, then press H."
    return False, "Hover over the viewport and press H."


def _unhide_init(env):
    env.base["maxh"] = len(_hidden(env))


def _unhide_check(env):
    n = len(_hidden(env))
    env.base["maxh"] = max(env.base["maxh"], n)
    if n == 0 and env.base["maxh"] > 0:
        return True, None
    if n == 0:
        return False, "Nothing is hidden. Select an object and press H first."
    return False, "Press Alt + H (Option + H on Mac) to show everything again."


def _collection_init(env):
    env.base["cols"] = len(bpy.data.collections)


def _collection_check(env):
    if len(bpy.data.collections) > env.base["cols"]:
        return True, None
    if not env.selected:
        return False, "Select an object first."
    return False, "Press M, choose + New Collection, type a name and press OK."


# ---- lesson 13: smooth shapes ---------------------------------------------

def _smooth_check(env):
    o = env.obj
    if o is None or o.type != "MESH" or not o.data.polygons:
        return False, "Select the sphere first."
    try:
        smooth = all(p.use_smooth for p in o.data.polygons)
    except AttributeError:
        smooth = False
    if smooth:
        return True, None
    return False, "Right-click the object and choose Shade Smooth (or Object > Shade Smooth)."


def _subsurf_level(want):
    def check(env):
        o = env.obj
        if o is None or o.type != "MESH":
            return False, "Select the object first."
        for m in o.modifiers:
            if m.type == "SUBSURF" and m.levels >= want:
                return True, None
        return False, f"Hover over the viewport and press Ctrl + {want}."
    return None, check


# ---- lesson 15: shiny materials ---------------------------------------------

def _principled(mat):
    tree = getattr(mat, "node_tree", None)
    if tree:
        for node in tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                return node
    return None


def _material_value(name, test, how):
    def check(env):
        o = env.obj
        if o is None or o.type != "MESH":
            return False, "Select the object first."
        mat = o.active_material
        if mat is None:
            return False, "In the Material tab, click New."
        node = _principled(mat)
        if node is None:
            return False, "This material has no Principled BSDF."
        if test(node.inputs[name].default_value):
            return True, None
        return False, how
    return None, check


# ---- lesson 17: text ---------------------------------------------------------

def _text_obj(env):
    o = env.obj
    return o if o is not None and o.type == "FONT" else None


def _text_edit_check(env):
    o = _text_obj(env)
    if o is None:
        return False, "Select the text object first."
    if o.mode != "OBJECT":
        return False, "Type your text, then press Tab to finish."
    if o.data.body != "Text":
        return True, None
    return False, "Press Tab, delete the letters with Backspace, type something, then Tab."


def _text_extrude_check(env):
    o = _text_obj(env)
    if o is None:
        return False, "Select the text object first."
    if o.data.extrude >= 0.05:
        return True, None
    return False, "Properties editor > green 'a' Data tab > Geometry > Extrude: type 0.2."


# ---- lesson 18: light, camera, render ----------------------------------------

def _camera_view_check(env):
    for a in env.areas("VIEW_3D"):
        r3d = getattr(a.spaces.active, "region_3d", None)
        if r3d is not None and r3d.view_perspective == "CAMERA":
            return True, None
    if not any(o.type == "CAMERA" for o in env.objects):
        return False, "The scene has no camera. Click 'Camera view' and one will be added."
    return False, "Press Numpad 0, or View > Cameras > Active Camera."


def _render_init(env):
    env.base["running"] = False


def _render_check(env):
    try:
        running = bpy.app.is_job_running("RENDER")
    except (AttributeError, ValueError):
        running = False
    if running:
        env.base["running"] = True
        return False, "Rendering... wait a moment."
    if env.base["running"]:
        return True, None
    if not any(o.type == "CAMERA" for o in env.objects):
        return False, "The scene has no camera. Add one first (Shift + A > Camera)."
    return False, "Hover over the viewport and press F12."


# ---- lesson 19: animation ------------------------------------------------------

def _fcurves(action):
    try:
        return list(action.fcurves)
    except AttributeError:                      # Blender 5: layered actions
        out = []
        for layer in getattr(action, "layers", []):
            for strip in getattr(layer, "strips", []):
                for bag in getattr(strip, "channelbags", []):
                    out.extend(bag.fcurves)
        return out


def _key_frames(o):
    ad = getattr(o, "animation_data", None)
    if ad is None or ad.action is None:
        return set()
    return {round(kp.co.x) for fc in _fcurves(ad.action) for kp in fc.keyframe_points}


def _key1_check(env):
    o = env.obj
    if o is None or not o.select_get(view_layer=env.vl):
        return False, "Click the cube to select it first."
    if _key_frames(o):
        return True, None
    return False, "Hover over the viewport and press I."


def _frame_jump_check(env):
    if env.scene.frame_current >= 30:
        return True, None
    return False, "In the Timeline, click or drag the numbers at the top to frame 60."


def _key2_check(env):
    o = env.obj
    if o is not None and len(_key_frames(o)) >= 2:
        return True, None
    return False, "Press G and move the cube, click, then press I again."


def _play_check(env):
    for win in env.windows:
        if win.screen.is_animation_playing:
            return True, None
    return False, "Hover over the viewport and press Space."


# ---- lesson 20: build a tiny house ----------------------------------------------

def _floor_check(env):
    for o in _named(env, "Plane"):
        if o.dimensions.x >= 5.5 and o.dimensions.y >= 5.5:
            return True, None
    if not _named(env, "Plane"):
        return False, "Add a plane: Shift + A > Mesh > Plane."
    return False, "Make the plane big: hover over the viewport, press S, type 4, press Enter."


def _house_body(env):
    for o in _named(env, "Cube"):
        if abs(_lowest_z(o)) <= 0.1 and o.matrix_world.translation.z > 0.5:
            return o
    return None


def _house_check(env):
    if _house_body(env) is not None:
        return True, None
    if not _named(env, "Cube"):
        return False, "Add a cube: Shift + A > Mesh > Cube."
    return False, "Lift the cube onto the floor: press G, then Z, type 1, press Enter."


def _roof_check(env):
    body = _house_body(env)
    if body is None:
        return False, "Build the house body first (go back one task)."
    top = _highest_z(body)
    for o in _named(env, "Cone"):
        if top - 0.15 <= _lowest_z(o) <= top + 0.5:
            return True, None
    if not _named(env, "Cone"):
        return False, "Add a cone: Shift + A > Mesh > Cone."
    return False, "Lift the cone onto the house: press G, then Z, type 3, press Enter."


def _two_coloured_check(env):
    n = 0
    for o in env.meshes:
        mat = o.active_material
        if mat is not None and _differs(_base_color(mat), DEFAULT_COLOR, 0.02):
            n += 1
    if n >= 2:
        return True, None
    return False, f"{n} of 2 objects coloured. Select an object, then Material tab > New > Base Color."


DETECTORS = {
    "orbit": _camera("orbit"),
    "pan": _camera("pan"),
    "zoom": _camera("zoom"),
    "select": (_select_init, _select_check),
    "add_menu": (_objs_init, _add_menu_check),
    "add_cube": (_objs_init, _add_cube_check),
    "delete": (_objs_init, _delete_check),
    "move": (_confirm_init(_T, _tf_init),
             _confirm_xform(_T, _move_check, "move",
                            "Hover over the viewport, press G, move the mouse, then click.")),
    "move_axis": (_confirm_init(_T, _tf_init),
                  _confirm_xform(_T, _move_axis_check, "axis",
                                 "Press G, then X, Y or Z, move the mouse and click.")),
    "rotate": (_confirm_init(_R, _tf_init),
               _confirm_xform(_R, _rotate_check, "rotate",
                              "Hover over the viewport, press R, move the mouse, then click.")),
    "scale": (_confirm_init(_S_, _tf_init),
              _confirm_xform(_S_, _scale_check, "scale",
                             "Hover over the viewport, press S, move the mouse, then click.")),
    "undo": (None, _undo_check),
    "edit_mode": (None, _edit_mode_check),
    "object_mode": (None, _object_mode_check),
    "select_modes": (_modes_init, _modes_check),
    "face_move": (_confirm_init(_T, _face_move_init), _confirm_face_move),
    "one_face": (None, _one_face_check),
    "extrude": (_confirm_init(("EXTRUDE",), _extrude_init), _confirm_extrude),
    "material_tab": (None, _tab_check),
    "material_color": (None, _color_check),
    "material_preview": (None, _preview_check),
    "delete_cube": (_objs_init, _delete_cube_check),
    "wall_length": (_confirm_init(_S_),
                    _confirm_value(_S_, _scale_is(0, 4.0, "Press S, then X, type 4 and press Enter."),
                                   "Press S, then X, type 4 and press Enter.")),
    "wall_thin": (_confirm_init(_S_),
                  _confirm_value(_S_, _scale_is(1, 0.2, "Press S, then Y, type 0.2 and press Enter."),
                                 "Press S, then Y, type 0.2 and press Enter.")),
    "wall_tall": (_confirm_init(_S_),
                  _confirm_value(_S_, _scale_is(2, 1.5, "Press S, then Z, type 1.5 and press Enter."),
                                 "Press S, then Z, type 1.5 and press Enter.")),
    "wall_ground": (_confirm_init(_T),
                    _confirm_value(_T, _lifted, "Press G, then Z, type 1.5 and press Enter.")),
    # lesson 8
    "duplicate": (_objs_init, _dup_check),
    "multi_select": (None, _multi_select_check),
    "select_all": (_select_all_init, _select_all_check),
    "deselect_all": (_deselect_all_init, _deselect_all_check),
    # lesson 9
    "view_front": _view_is((0.7071068, 0.7071068, 0.0, 0.0), ("1", "Front")),
    "view_top": _view_is((1.0, 0.0, 0.0, 0.0), ("7", "Top")),
    "view_persp": (_persp_init, _persp_check),
    "view_frame": (_vframe_init, _vframe_check),
    # lesson 10
    "add_sphere": _added("Sphere", "Shift + A > Mesh > UV Sphere"),
    "add_cylinder": _added("Cylinder", "Shift + A > Mesh > Cylinder"),
    "add_plane": _added("Plane", "Shift + A > Mesh > Plane"),
    "add_monkey": _added("Suzanne", "Shift + A > Mesh > Monkey"),
    # lesson 11
    "shade_wire": (None, _wire_check),
    "shade_solid": (_solid_init, _solid_check),
    "xray": (None, _xray_check),
    # lesson 12
    "rename": (_rename_init, _rename_check),
    "hide": (_hide_init, _hide_check),
    "unhide": (_unhide_init, _unhide_check),
    "collection": (_collection_init, _collection_check),
    # lesson 13
    "smooth": (None, _smooth_check),
    "subsurf2": _subsurf_level(2),
    "subsurf3": _subsurf_level(3),
    # lesson 14
    "loopcut": _edit_tool(("mesh.loopcut_slide", "mesh.loopcut"),
                          "Hover over the cube, press Ctrl + R, move the mouse over a ring, click, then right-click."),
    "inset": _edit_tool(("mesh.inset",),
                        "Select one face (press 3, click a face), press I, move the mouse and click."),
    "bevel": _edit_tool(("mesh.bevel",),
                        "Press 2, then A to select all edges, press Ctrl + B, move the mouse and click."),
    # lesson 15
    "metallic": _material_value("Metallic", lambda v: v >= 0.8,
                                "Drag the Metallic slider to the right (or type 1)."),
    "roughness": _material_value("Roughness", lambda v: v <= 0.3,
                                 "Drag the Roughness slider to the left (or type 0.1)."),
    # lesson 16
    "two_meshes": (None, lambda env: (_mesh_count(env) >= 2, "Click 'Add a cube' so that there are two cubes.")),
    "join": _object_tool(("object.join",), lambda now, n0: now < n0,
                         "Hover over the viewport and press Ctrl + J."),
    "separate": _object_tool(("mesh.separate",), lambda now, n0: now > n0,
                             "Press Tab, press A, then P and choose By Loose Parts. Press Tab again."),
    # lesson 17
    "add_text": _added_type("FONT", "Shift + A > Text"),
    "edit_text": (None, _text_edit_check),
    "text_extrude": (None, _text_extrude_check),
    # lesson 18
    "add_light": _added_type("LIGHT", "Shift + A > Light > Sun"),
    "camera_view": (None, _camera_view_check),
    "render": (_render_init, _render_check),
    # lesson 19
    "keyframe1": (None, _key1_check),
    "frame_jump": (None, _frame_jump_check),
    "keyframe2": (None, _key2_check),
    "play": (None, _play_check),
    # lesson 20
    "floor": (None, _floor_check),
    "house": (None, _house_check),
    "roof": (None, _roof_check),
    "two_coloured": (None, _two_coloured_check),
}
