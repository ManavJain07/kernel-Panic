"""Operators that start, skip and stop a guided goal. Owner: navigation team."""
import bpy

from . import context as ctx
from . import navigator, operators, session


class NAVGUIDE_OT_start_goal(bpy.types.Operator):
    bl_idname = "navguide.start_goal"
    bl_label = "Guide me"
    bl_description = "Start guiding you from where you are right now"
    bl_options = {"INTERNAL"}

    recipe_id: bpy.props.StringProperty()  # empty = use the typed goal

    def execute(self, context):
        wm = context.window_manager
        rid = self.recipe_id
        if not rid:
            matches = navigator.match(wm.navguide_goal_query)
            if not matches:
                self.report({"WARNING"}, "No guide for that yet. Pick one from 'Or choose a goal'.")
                return {"CANCELLED"}
            rid = matches[0]["id"]

        recipe = navigator.get_recipe(rid)
        if recipe is None:
            return {"CANCELLED"}

        state = ctx.get_state(context)
        baseline = {"object_count": state["object_count"]}
        index = navigator.first_unfinished(recipe, state, baseline)

        wm.navguide_goal_id = rid
        wm.navguide_goal_baseline = baseline["object_count"]
        wm.navguide_goal_step = index
        if index > 0:
            self.report({"INFO"}, f"Skipped {index} step(s) you have already done.")
        session.refresh(context)
        session.redraw_all()
        return {"FINISHED"}


class NAVGUIDE_OT_goal_nav(bpy.types.Operator):
    bl_idname = "navguide.goal_nav"
    bl_label = "Goal navigation"
    bl_options = {"INTERNAL"}

    direction: bpy.props.IntProperty(default=1)  # 1 = next / skip, 0 = stop guiding

    def execute(self, context):
        wm = context.window_manager
        recipe = navigator.get_recipe(wm.navguide_goal_id)
        if self.direction == 0 or recipe is None:
            wm.navguide_goal_id = ""
            wm.navguide_goal_step = 0
        else:
            wm.navguide_goal_step = min(wm.navguide_goal_step + 1, len(recipe["steps"]))
        session.refresh(context)
        session.redraw_all()
        return {"FINISHED"}


# ---- one-click fixes used by the troubleshooter ----------------------------
# Each returns None on success or a message explaining why it could not run.
def _view3d_space(context):
    space = context.space_data
    if space is not None and space.type == "VIEW_3D":
        return space
    return None


def _fix_solid_view(context):
    space = _view3d_space(context)
    if space is None:
        return "Run this from the 3D Viewport."
    space.shading.type = "SOLID"


def _fix_object_mode(context):
    if context.mode == "OBJECT":
        return None
    if context.active_object is None:
        return "Nothing is active."
    bpy.ops.object.mode_set(mode="OBJECT")


def _fix_show_hidden(context):
    if context.mode != "OBJECT":
        return "Switch to Object Mode first (press Tab)."
    bpy.ops.object.hide_view_clear()


def _fix_select_all(context):
    if context.mode != "OBJECT":
        return "Switch to Object Mode first (press Tab)."
    bpy.ops.object.select_all(action="SELECT")


def _fix_undo(context):
    bpy.ops.ed.undo()


def _fix_recalc_normals(context):
    if context.mode != "EDIT_MESH":
        return "Select the object and press Tab to enter Edit Mode first."
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)


FIXES = {
    "solid_view": _fix_solid_view,
    "object_mode": _fix_object_mode,
    "show_hidden": _fix_show_hidden,
    "select_all": _fix_select_all,
    "undo": _fix_undo,
    "recalc_normals": _fix_recalc_normals,
}


class NAVGUIDE_OT_fix(bpy.types.Operator):
    bl_idname = "navguide.fix"
    bl_label = "Fix it"
    bl_description = "Applies this fix for you"
    bl_options = {"REGISTER", "UNDO"}

    fix: bpy.props.StringProperty()

    def execute(self, context):
        fn = {**operators.ACTIONS, **FIXES}.get(self.fix)
        if fn is None:
            self.report({"ERROR"}, f"Unknown fix: {self.fix}")
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


classes = (NAVGUIDE_OT_start_goal, NAVGUIDE_OT_goal_nav, NAVGUIDE_OT_fix)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
