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

    def __init__(self, windows, acc, flags, base):
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


DETECTORS = {
    "orbit": _camera("orbit"),
    "pan": _camera("pan"),
    "zoom": _camera("zoom"),
    "select": (_select_init, _select_check),
    "add_menu": (_objs_init, _add_menu_check),
    "add_cube": (_objs_init, _add_cube_check),
    "delete": (_objs_init, _delete_check),
    "move": (_tf_init, _move_check),
    "move_axis": (_tf_init, _move_axis_check),
    "rotate": (_tf_init, _rotate_check),
    "scale": (_tf_init, _scale_check),
    "undo": (None, _undo_check),
    "edit_mode": (None, _edit_mode_check),
    "object_mode": (None, _object_mode_check),
    "select_modes": (_modes_init, _modes_check),
    "face_move": (_face_move_init, _face_move_check),
    "one_face": (None, _one_face_check),
    "extrude": (_extrude_init, _extrude_check),
    "material_tab": (None, _tab_check),
    "material_color": (None, _color_check),
    "material_preview": (None, _preview_check),
    "delete_cube": (_objs_init, _delete_cube_check),
    "wall_length": (None, _scale_axis(0, 4.0, "Press S, then X, type 4 and press Enter.")),
    "wall_thin": (None, _scale_axis(1, 0.2, "Press S, then Y, type 0.2 and press Enter.")),
    "wall_tall": (None, _scale_axis(2, 1.5, "Press S, then Z, type 1.5 and press Enter.")),
    "wall_ground": (None, _on_ground_check),
}
