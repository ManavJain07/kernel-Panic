import bpy
from . import tasks


# ---- helper actions ---------------------------------------------------
# Each returns None on success or a message string explaining why it
# could not run. Task steps refer to these by name in tasks.json.

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


class NAVGUIDE_OT_run_action(bpy.types.Operator):
    bl_idname = "navguide.run_action"
    bl_label = "Do it for me"
    bl_description = "Performs this step for you so you can see what it does"
    bl_options = {"REGISTER", "UNDO"}

    action: bpy.props.StringProperty()

    def execute(self, context):
        fn = ACTIONS.get(self.action)
        if fn is None:
            self.report({"ERROR"}, f"Unknown action: {self.action}")
            return {"CANCELLED"}
        try:
            problem = fn(context)
        except RuntimeError as e:
            self.report({"WARNING"}, str(e).strip() or "That could not run here.")
            return {"CANCELLED"}
        if problem:
            self.report({"WARNING"}, problem)
            return {"CANCELLED"}
        return {"FINISHED"}


class NAVGUIDE_OT_step(bpy.types.Operator):
    bl_idname = "navguide.step"
    bl_label = "Change step"
    bl_options = {"INTERNAL"}

    direction: bpy.props.IntProperty(default=1)  # +1 next, -1 back, 0 restart

    def execute(self, context):
        wm = context.window_manager
        task = tasks.get_task(wm.navguide_task)
        if task is None:
            return {"CANCELLED"}
        if self.direction == 0:
            wm.navguide_step = 0
        else:
            last = len(task["steps"])  # index == len means "finished"
            wm.navguide_step = max(0, min(wm.navguide_step + self.direction, last))
        return {"FINISHED"}


classes = (NAVGUIDE_OT_run_action, NAVGUIDE_OT_step)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
