"""Accessible mode: every command the tutorial needs, as one-click buttons.

In "Accessible mode" the lesson shows a list of these commands on the right of
the viewport. Each one does, in a single mouse click, what the keyboard
shortcut does (without having to hold keys or drag the mouse), so the whole
tutorial can be done with the mouse alone, or with any switch / pointer device.

Each task in lessons.json lists the commands that complete it ("cmds"). The
task is still ticked off by the normal detector in detect.py, exactly as if the
learner had done it by hand.

A command is  id: (label, shortcut text, function, instant)
  function(context) -> None, or a short message saying why it could not run
  instant  True = it changes things in one go; tells the detectors not to wait
           for a mouse click (see detect.py, "instant").
"""
import bpy
import bmesh
from mathutils import Quaternion, Vector

from . import actions

EXTRA_FLAGS = {"add_menu": "shift_a", "sel_vert": "key_1", "sel_edge": "key_2",
               "sel_face": "key_3"}


# ---------------------------------------------------------------- helpers ---

def _mesh_objects(ctx):
    return [o for o in ctx.view_layer.objects if o.type == "MESH"]


def _active_mesh(ctx):
    o = ctx.active_object
    return o if o is not None and o.type == "MESH" else None


def _need_object_mode(ctx):
    if ctx.mode != "OBJECT":
        return "Switch to Object Mode first (use the Edit Mode command)."
    return None


# --------------------------------------------------------------- commands ---

def _orbit(ctx):
    rv = ctx.space_data.region_3d
    rv.view_rotation = Quaternion((0, 0, 1), 0.5236) @ rv.view_rotation


def _pan(ctx):
    rv = ctx.space_data.region_3d
    rv.view_location += rv.view_rotation @ Vector((rv.view_distance * 0.25, 0, 0))


def _zoom_in(ctx):
    ctx.space_data.region_3d.view_distance *= 0.6


def _zoom_out(ctx):
    ctx.space_data.region_3d.view_distance *= 1.6


def _deselect_all(ctx):
    if ctx.mode == "EDIT_MESH":
        bpy.ops.mesh.select_all(action="DESELECT")
    else:
        bpy.ops.object.select_all(action="DESELECT")


def _select_cube(ctx):
    target = _active_mesh(ctx) or next(iter(_mesh_objects(ctx)), None)
    if target is None:
        return "There is no object to select. Use 'Add a cube' first."
    if ctx.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    ctx.view_layer.objects.active = target


def _add_menu(ctx):
    bpy.ops.wm.call_menu(name="VIEW3D_MT_add")


def _add_cube(ctx):
    return actions.ACTIONS["add_cube"](ctx)


def _delete(ctx):
    return actions.ACTIONS["delete_selected"](ctx)


def _move(ctx):
    bpy.ops.transform.translate(value=(2, 1, 0))


def _move_axis(axis):
    def run(ctx):
        value = [0.0, 0.0, 0.0]
        value[axis] = 2.0 if ctx.mode == "OBJECT" else 0.5
        flags = [False, False, False]
        flags[axis] = True
        bpy.ops.transform.translate(value=tuple(value), constraint_axis=tuple(flags))
    return run


def _rotate(ctx):
    bpy.ops.transform.rotate(value=0.7854, orient_axis="Z")


def _scale(ctx):
    bpy.ops.transform.resize(value=(1.5, 1.5, 1.5))


def _undo(ctx):
    bpy.ops.ed.undo()


def _edit_mode(ctx):
    return actions.ACTIONS["toggle_edit_mode"](ctx)


def _select_mode(kind):
    def run(ctx):
        if ctx.mode != "EDIT_MESH":
            return "Switch to Edit Mode first."
        bpy.ops.mesh.select_mode(type=kind)
    return run


def _pick_face(ctx):
    if ctx.mode != "EDIT_MESH":
        return "Switch to Edit Mode first."
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="DESELECT")
    me = ctx.edit_object.data
    bm = bmesh.from_edit_mesh(me)
    bm.faces.ensure_lookup_table()
    if not bm.faces:
        return "This object has no faces."
    bm.faces[0].select_set(True)
    bmesh.update_edit_mesh(me)


def _extrude(ctx):
    if ctx.mode != "EDIT_MESH":
        return "Switch to Edit Mode first."
    bpy.ops.mesh.extrude_region()
    bpy.ops.transform.translate(value=(0, 0, 1), orient_type="NORMAL",
                                constraint_axis=(False, False, True))


def _set_scale(axis, value):
    def run(ctx):
        o = _active_mesh(ctx)
        if o is None:
            return "Select the cube first."
        msg = _need_object_mode(ctx)
        if msg:
            return msg
        o.scale[axis] = value
    return run


def _lift(ctx):
    o = _active_mesh(ctx)
    if o is None:
        return "Select the wall first."
    low = min((o.matrix_world @ Vector(c)).z for c in o.bound_box)
    o.location.z -= low


def _material_tab(ctx):
    found = False
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "PROPERTIES":
                try:
                    area.spaces.active.context = "MATERIAL"
                    found = True
                except (TypeError, AttributeError):
                    pass
    if not found:
        return "The Properties editor is hidden or has no Material tab for this object."


def _new_material(ctx):
    o = _active_mesh(ctx)
    if o is None:
        return "Select the object first."
    mat = bpy.data.materials.new("Tutorial material")
    try:
        mat.use_nodes = True
    except (AttributeError, RuntimeError):
        pass
    o.data.materials.append(mat)
    o.active_material_index = len(o.data.materials) - 1


def _pick_colour(ctx):
    o = _active_mesh(ctx)
    mat = o.active_material if o else None
    if mat is None:
        return "Use 'New material' first."
    blue = (0.1, 0.4, 1.0, 1.0)
    tree = getattr(mat, "node_tree", None)
    done = False
    if tree:
        for node in tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Base Color"].default_value = blue
                done = True
    if not done:
        mat.diffuse_color = blue


def _material_preview(ctx):
    return actions.ACTIONS["material_preview"](ctx)


# ------------------------------------------------ lessons 8 - 20 ------------

def _act(name):
    """A command that does what the lesson's "Do it for me" button does."""
    def run(ctx):
        return actions.ACTIONS[name](ctx)
    return run


def _select_both(ctx):
    bpy.ops.object.select_all(action="SELECT")


def _edit_only(ctx):
    if ctx.mode != "EDIT_MESH":
        return "Switch to Edit Mode first."
    return None


def _loopcut(ctx):
    msg = _edit_only(ctx)
    if msg:
        return msg
    bpy.ops.mesh.loopcut(number_cuts=1, edge_index=0, object_index=0)


def _inset(ctx):
    msg = _edit_only(ctx)
    if msg:
        return msg
    bpy.ops.mesh.inset(thickness=0.2)


def _bevel(ctx):
    msg = _edit_only(ctx)
    if msg:
        return msg
    bpy.ops.mesh.select_mode(type="EDGE")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bevel(offset=0.1, segments=2)


def _principled(ctx):
    o = _active_mesh(ctx)
    if o is None:
        return None, "Select the object first."
    if o.active_material is None:
        _new_material(ctx)
    tree = getattr(o.active_material, "node_tree", None)
    for node in (tree.nodes if tree else ()):
        if node.type == "BSDF_PRINCIPLED":
            return node, None
    return None, "This material has no Principled BSDF."


def _material_value(name, value):
    def run(ctx):
        node, msg = _principled(ctx)
        if node is None:
            return msg
        node.inputs[name].default_value = value
    return run


def _separate(ctx):
    o = _active_mesh(ctx)
    if o is None:
        return "Select the joined object first."
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")


def _text_object(ctx):
    o = ctx.active_object
    return o if o is not None and o.type == "FONT" else None


def _edit_text(ctx):
    o = _text_object(ctx)
    if o is None:
        return "Select the text object first."
    o.data.body = "Hello"


def _text_extrude(ctx):
    o = _text_object(ctx)
    if o is None:
        return "Select the text object first."
    o.data.extrude = 0.2


def _add_floor(ctx):
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))


def _add_house(ctx):
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))


def _add_roof(ctx):
    bpy.ops.mesh.primitive_cone_add(radius1=1.6, depth=1.5, location=(0, 0, 2.75))


def _paint_two(ctx):
    colours = ((0.8, 0.2, 0.2, 1.0), (0.2, 0.4, 0.9, 1.0), (0.3, 0.7, 0.3, 1.0))
    for i, o in enumerate(_mesh_objects(ctx)[:3]):
        mat = bpy.data.materials.new(f"Tutorial colour {i + 1}")
        try:
            mat.use_nodes = True
        except (AttributeError, RuntimeError):
            pass
        tree = getattr(mat, "node_tree", None)
        done = False
        for node in (tree.nodes if tree else ()):
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Base Color"].default_value = colours[i]
                done = True
        if not done:
            mat.diffuse_color = colours[i]
        o.data.materials.append(mat)


COMMANDS = {
    "orbit": ("Orbit the view", "", _orbit, True),
    "pan": ("Pan the view", "", _pan, True),
    "zoom_in": ("Zoom in", "", _zoom_in, True),
    "zoom_out": ("Zoom out", "", _zoom_out, True),
    "deselect_all": ("Deselect everything", "Alt + A", _deselect_all, True),
    "select_cube": ("Select the cube", "Click it", _select_cube, True),
    "add_menu": ("Open the Add menu", "Shift + A", _add_menu, False),
    "add_cube": ("Add a cube", "Shift + A", _add_cube, True),
    "delete": ("Delete selected", "Delete", _delete, True),
    "move": ("Move (free)", "G", _move, True),
    "move_x": ("Move along X", "G, X", _move_axis(0), True),
    "move_y": ("Move along Y", "G, Y", _move_axis(1), True),
    "move_z": ("Move along Z", "G, Z", _move_axis(2), True),
    "rotate": ("Rotate 45 degrees", "R", _rotate, True),
    "scale": ("Scale bigger", "S", _scale, True),
    "undo": ("Undo", "Ctrl / Cmd + Z", _undo, False),
    "edit_mode": ("Edit Mode on / off", "Tab", _edit_mode, True),
    "sel_vert": ("Select vertices", "1", _select_mode("VERT"), False),
    "sel_edge": ("Select edges", "2", _select_mode("EDGE"), False),
    "sel_face": ("Select faces", "3", _select_mode("FACE"), False),
    "pick_face": ("Pick one face", "Click it", _pick_face, True),
    "extrude": ("Extrude the face", "E", _extrude, True),
    "wall_x": ("Make it long (X = 4)", "S, X, 4", _set_scale(0, 4.0), True),
    "wall_y": ("Make it thin (Y = 0.2)", "S, Y, 0.2", _set_scale(1, 0.2), True),
    "wall_z": ("Make it taller (Z = 1.5)", "S, Z, 1.5", _set_scale(2, 1.5), True),
    "wall_lift": ("Lift onto the ground", "G, Z, 1.5", _lift, True),
    "material_tab": ("Open the Material tab", "", _material_tab, True),
    "new_material": ("New material", "", _new_material, True),
    "pick_colour": ("Colour it blue", "", _pick_colour, True),
    "material_preview": ("Material Preview", "", _material_preview, True),
    "select_all": ("Select all", "A", _act("select_all"), True),
    "duplicate": ("Duplicate", "Shift + D", _act("duplicate"), True),
    "select_both": ("Select both cubes", "Shift + click", _select_both, True),
    "view_front": ("Front view", "Numpad 1", _act("view_front"), True),
    "view_top": ("Top view", "Numpad 7", _act("view_top"), True),
    "view_persp": ("Perspective / flat", "Numpad 5", _act("view_persp"), True),
    "frame_selected": ("Zoom to selected", "Numpad .", _act("frame_selected"), True),
    "add_sphere": ("Add a sphere", "Shift + A", _act("add_sphere"), True),
    "add_cylinder": ("Add a cylinder", "Shift + A", _act("add_cylinder"), True),
    "add_plane": ("Add a plane", "Shift + A", _act("add_plane"), True),
    "add_monkey": ("Add the monkey", "Shift + A", _act("add_monkey"), True),
    "shade_wire": ("Wireframe view", "Shift + Z", _act("shade_wire"), True),
    "shade_solid": ("Solid view", "Shift + Z", _act("shade_solid"), True),
    "xray": ("See through", "Alt + Z", _act("xray"), True),
    "rename": ("Rename the object", "F2", _act("rename"), True),
    "hide": ("Hide it", "H", _act("hide"), True),
    "unhide": ("Show everything", "Alt + H", _act("unhide"), True),
    "new_collection": ("New collection", "M", _act("new_collection"), True),
    "shade_smooth": ("Shade Smooth", "", _act("shade_smooth"), True),
    "subsurf2": ("More detail (level 2)", "Ctrl + 2", _act("subsurf2"), True),
    "subsurf3": ("Even more detail (level 3)", "Ctrl + 3", _act("subsurf3"), True),
    "loopcut": ("Add a loop cut", "Ctrl + R", _loopcut, True),
    "inset": ("Inset the face", "I", _inset, True),
    "bevel": ("Bevel the edges", "Ctrl + B", _bevel, True),
    "metallic": ("Make it metal", "", _material_value("Metallic", 1.0), True),
    "roughness": ("Make it shiny", "", _material_value("Roughness", 0.1), True),
    "join": ("Join objects", "Ctrl + J", _act("join"), True),
    "separate": ("Separate by parts", "P", _separate, True),
    "add_text": ("Add text", "Shift + A", _act("add_text"), True),
    "edit_text": ("Change the words", "Tab", _edit_text, True),
    "text_extrude": ("Make the text 3D", "", _text_extrude, True),
    "add_sun": ("Add a light (Sun)", "Shift + A", _act("add_sun"), True),
    "camera_view": ("Look through the camera", "Numpad 0", _act("camera_view"), True),
    "render_fast": ("Render a picture", "F12", _act("render_fast"), True),
    "keyframe": ("Set a keyframe", "I", _act("keyframe"), True),
    "jump_frame": ("Jump to frame 60", "", _act("jump_frame"), True),
    "move_and_key": ("Move it and set a keyframe", "G, I", _act("move_and_key"), True),
    "play": ("Play the animation", "Space", _act("play"), True),
    "add_floor": ("Add the floor", "", _add_floor, True),
    "add_house": ("Add the house body", "", _add_house, True),
    "add_roof": ("Add the roof", "", _add_roof, True),
    "paint_two": ("Paint the objects", "", _paint_two, True),
}


def label(cid):
    return COMMANDS[cid][0]


def shortcut(cid):
    return COMMANDS[cid][1]


def lesson_commands(lesson):
    """Every command the lesson's tasks use, in order, without repeats."""
    seen, out = set(), []
    for step in lesson["steps"]:
        for cid in step.get("cmds", ()):
            if cid in COMMANDS and cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


def run(cid, context):
    """Run a command. Returns None, or a message when it could not run."""
    from . import lesson as lesson_mod          # late import: lesson imports us
    entry = COMMANDS.get(cid)
    if entry is None:
        return f"Unknown command: {cid}"
    _label, _short, fn, instant = entry
    if instant:
        lesson_mod.note_key("instant")
    lesson_mod.note_key(EXTRA_FLAGS.get(cid))
    try:
        return fn(context)
    except RuntimeError as e:
        lines = str(e).strip().splitlines()
        return lines[-1] if lines else "That could not run here."
    except (AttributeError, ReferenceError, TypeError):
        return "That is not possible right now."
