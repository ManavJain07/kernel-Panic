import bpy


# ---- helper actions ---------------------------------------------------
# Each returns None on success or a message string explaining why it
# could not run. Lesson steps refer to these by name in lessons.json
# ("action": "add_cube") and the lesson's "Do it for me" button runs them.

def _add_cube(context):
    bpy.ops.mesh.primitive_cube_add()


def _toggle_edit_mode(context):
    obj = context.active_object
    if obj is None or obj.type != "MESH":
        return "Select a mesh object first."
    bpy.ops.object.mode_set(mode="EDIT" if context.mode == "OBJECT" else "OBJECT")


def _delete_selected(context):
    if context.mode != "OBJECT":
        return "Switch to Object Mode first (press Tab)."
    if not context.selected_objects:
        return "Nothing is selected."
    bpy.ops.object.delete()


def _frame_selected(context):
    if not context.selected_objects:
        return "Select an object first."
    bpy.ops.view3d.view_selected()


def _view_all(context):
    bpy.ops.view3d.view_all()


def _material_preview(context):
    space = context.space_data
    if space is None or space.type != "VIEW_3D":
        return "Run this from the 3D Viewport."
    space.shading.type = "MATERIAL"


ACTIONS = {
    "add_cube": _add_cube,
    "toggle_edit_mode": _toggle_edit_mode,
    "delete_selected": _delete_selected,
    "frame_selected": _frame_selected,
    "view_all": _view_all,
    "material_preview": _material_preview,
}
