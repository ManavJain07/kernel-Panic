import bpy


class NAVGUIDE_OT_add_cube(bpy.types.Operator):
    bl_idname = "navguide.add_cube"
    bl_label = "Add a Cube"
    bl_description = "Adds a cube at the 3D cursor (same as Shift+A > Mesh > Cube)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add()
        self.report({"INFO"}, "Cube added. Shortcut next time: Shift + A")
        return {"FINISHED"}


class NAVGUIDE_OT_toggle_edit_mode(bpy.types.Operator):
    bl_idname = "navguide.toggle_edit_mode"
    bl_label = "Switch Edit / Object Mode"
    bl_description = "Same as pressing Tab with a mesh selected"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        bpy.ops.object.mode_set(mode="EDIT" if context.mode == "OBJECT" else "OBJECT")
        return {"FINISHED"}


classes = (NAVGUIDE_OT_add_cube, NAVGUIDE_OT_toggle_edit_mode)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
