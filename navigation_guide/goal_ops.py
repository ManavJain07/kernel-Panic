"""Operators that start, skip and stop a guided goal. Owner: navigation team."""
import bpy

from . import context as ctx
from . import navigator, session


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
                names = ", ".join(r["title"].lower() for r in navigator.load_recipes())
                self.report({"WARNING"}, f"No guide for that yet. Try: {names}")
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


classes = (NAVGUIDE_OT_start_goal, NAVGUIDE_OT_goal_nav)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
