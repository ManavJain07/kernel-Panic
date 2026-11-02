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


# ---- lessons 8 - 20 ---------------------------------------------------------

def _need_viewport(context):
    space = context.space_data
    if space is None or space.type != "VIEW_3D":
        return None
    return space


def _dup(context):
    obj = context.active_object
    if obj is None or not obj.select_get():
        return "Select an object first."
    bpy.ops.object.duplicate()
    context.active_object.location.x += 2.5


def _select_all(context):
    bpy.ops.object.select_all(action="SELECT")


def _deselect_all(context):
    bpy.ops.object.select_all(action="DESELECT")


def _view_front(context):
    bpy.ops.view3d.view_axis(type="FRONT")


def _view_top(context):
    bpy.ops.view3d.view_axis(type="TOP")


def _view_persp(context):
    bpy.ops.view3d.view_persportho()


def _add_sphere(context):
    bpy.ops.mesh.primitive_uv_sphere_add(location=(2, 0, 0))


def _add_cylinder(context):
    bpy.ops.mesh.primitive_cylinder_add(location=(-2, 0, 0))


def _add_plane(context):
    bpy.ops.mesh.primitive_plane_add(location=(0, 3, 0))


def _add_monkey(context):
    bpy.ops.mesh.primitive_monkey_add(location=(0, -3, 1))


def _shading(kind):
    def run(context):
        space = _need_viewport(context)
        if space is None:
            return "Run this from the 3D Viewport."
        space.shading.type = kind
    return run


def _xray(context):
    space = _need_viewport(context)
    if space is None:
        return "Run this from the 3D Viewport."
    if space.shading.type == "WIREFRAME":
        space.shading.show_xray_wireframe = True
    else:
        space.shading.type = "SOLID"
        space.shading.show_xray = True


def _rename(context):
    obj = context.active_object
    if obj is None:
        return "Select an object first."
    obj.name = "My " + obj.name.split(".")[0]


def _hide(context):
    if not context.selected_objects:
        return "Select an object first."
    bpy.ops.object.hide_view_set(unselected=False)


def _unhide(context):
    bpy.ops.object.hide_view_clear()


def _new_collection(context):
    if not context.selected_objects:
        return "Select an object first."
    bpy.ops.object.move_to_collection(collection_index=0, is_new=True,
                                      new_collection_name="My Collection")


def _shade_smooth(context):
    if context.active_object is None:
        return "Select an object first."
    bpy.ops.object.shade_smooth()


def _subsurf(level):
    def run(context):
        if context.active_object is None:
            return "Select an object first."
        bpy.ops.object.subdivision_set(level=level)
    return run


def _join(context):
    if len(context.selected_objects) < 2:
        return "Select two objects first (press A)."
    bpy.ops.object.join()


def _add_text(context):
    bpy.ops.object.text_add(location=(0, 0, 0))


def _add_sun(context):
    bpy.ops.object.light_add(type="SUN", location=(4, -4, 6))


def _camera_view(context):
    if not any(o.type == "CAMERA" for o in context.scene.objects):
        bpy.ops.object.camera_add(location=(7, -7, 5), rotation=(1.1, 0, 0.8))
        context.scene.camera = context.active_object
    elif context.scene.camera is None:
        context.scene.camera = next(o for o in context.scene.objects if o.type == "CAMERA")
    bpy.ops.view3d.view_camera()


def _render_fast(context):
    if not any(o.type == "CAMERA" for o in context.scene.objects):
        return "The scene has no camera. Click 'Camera view' in the previous task."
    context.scene.render.resolution_percentage = 25
    bpy.ops.render.render("INVOKE_DEFAULT")


def _keyframe(context):
    obj = context.active_object
    if obj is None:
        return "Select an object first."
    obj.keyframe_insert(data_path="location")


def _jump_frame(context):
    context.scene.frame_set(60)


def _move_and_key(context):
    obj = context.active_object
    if obj is None:
        return "Select an object first."
    obj.location.x += 4
    obj.keyframe_insert(data_path="location")


def _play(context):
    bpy.ops.screen.animation_play()


ACTIONS = {
    "add_cube": _add_cube,
    "toggle_edit_mode": _toggle_edit_mode,
    "delete_selected": _delete_selected,
    "frame_selected": _frame_selected,
    "view_all": _view_all,
    "material_preview": _material_preview,
    "duplicate": _dup,
    "select_all": _select_all,
    "deselect_all": _deselect_all,
    "view_front": _view_front,
    "view_top": _view_top,
    "view_persp": _view_persp,
    "add_sphere": _add_sphere,
    "add_cylinder": _add_cylinder,
    "add_plane": _add_plane,
    "add_monkey": _add_monkey,
    "shade_wire": _shading("WIREFRAME"),
    "shade_solid": _shading("SOLID"),
    "xray": _xray,
    "rename": _rename,
    "hide": _hide,
    "unhide": _unhide,
    "new_collection": _new_collection,
    "shade_smooth": _shade_smooth,
    "subsurf2": _subsurf(2),
    "subsurf3": _subsurf(3),
    "join": _join,
    "add_text": _add_text,
    "add_sun": _add_sun,
    "camera_view": _camera_view,
    "render_fast": _render_fast,
    "keyframe": _keyframe,
    "jump_frame": _jump_frame,
    "move_and_key": _move_and_key,
    "play": _play,
}
