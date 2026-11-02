"""Navigation side of the sidebar. Owner: navigation team.

Main panel  = guided goal ("What do you want to make?")
Sub panels  = where you are, and quick tool lookup.
"""
import bpy

from . import context as ctx
from . import finder, navigator
from .utils import draw_wrapped


class NAVGUIDE_PT_main(bpy.types.Panel):
    bl_label = "Navigation Guide"
    bl_idname = "NAVGUIDE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        recipe = navigator.get_recipe(wm.navguide_goal_id) if wm.navguide_goal_id else None

        if recipe is None:
            self._draw_picker(layout, wm)
        else:
            self._draw_guide(layout, context, wm, recipe)

        layout.separator()
        layout.prop(wm, "navguide_overlay")

    # ---- no goal yet ----
    def _draw_picker(self, layout, wm):
        layout.label(text="What do you want to make?", icon="QUESTION")
        layout.prop(wm, "navguide_goal_query", text="")
        layout.operator("navguide.start_goal", text="Guide me", icon="PLAY").recipe_id = ""
        layout.separator()
        layout.label(text="Or pick one:")
        col = layout.column(align=True)
        for r in navigator.load_recipes():
            col.operator("navguide.start_goal", text=r["title"]).recipe_id = r["id"]

    # ---- guiding ----
    def _draw_guide(self, layout, context, wm, recipe):
        steps = recipe["steps"]
        index = wm.navguide_goal_step
        state = ctx.get_state(context)
        baseline = {"object_count": wm.navguide_goal_baseline}

        layout.label(text=recipe["title"], icon="BOOKMARKS")

        # mini checklist of every step
        col = layout.column(align=True)
        for i, step in enumerate(steps):
            icon = "CHECKMARK" if i < index else ("RIGHTARROW" if i == index else "DOT")
            col.label(text=step.get("short", step["text"][:30]), icon=icon)

        if index >= len(steps):
            box = layout.box()
            box.label(text="All done. Nice work!", icon="CHECKMARK")
            box.operator("navguide.goal_nav", text="Start another goal", icon="LOOP_BACK").direction = 0
            return

        step = steps[index]
        box = layout.box()
        box.label(text=f"Now: step {index + 1} of {len(steps)}", icon="TRACKING_FORWARDS")

        message, action = navigator.problem(step, state)
        if message:
            draw_wrapped(box, message, icon="ERROR")
            if action:
                box.operator("navguide.run_action", text="Switch mode for me", icon="EDITMODE_HLT").action = action

        draw_wrapped(box, step["text"])
        if step.get("shortcut"):
            box.label(text=f"Shortcut: {step['shortcut']}", icon="EVENT_RETURN")
        if step.get("action"):
            box.operator(
                "navguide.run_action",
                text=step.get("action_label", "Do it for me"),
                icon="PLAY",
            ).action = step["action"]

        row = box.row(align=True)
        if navigator.is_done(step, state, baseline) is None:
            row.operator("navguide.goal_nav", text="I did this", icon="CHECKMARK").direction = 1
        else:
            box.label(text="Waiting for you... (moves on by itself)", icon="TIME")
            row.operator("navguide.goal_nav", text="Skip step", icon="FORWARD").direction = 1
        row.operator("navguide.goal_nav", text="Stop", icon="X").direction = 0


class NAVGUIDE_PT_state(bpy.types.Panel):
    bl_label = "Where you are"
    bl_idname = "NAVGUIDE_PT_state"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"
    bl_parent_id = "NAVGUIDE_PT_main"

    def draw(self, context):
        layout = self.layout
        state = ctx.get_state(context)
        layout.label(text=f"Mode: {state['mode']}")
        layout.label(text=f"Active: {state['active_object'] or 'None'}")
        layout.label(text=f"Selected: {state['selected_count']}")
        hint, shortcut = ctx.get_hint(state)
        box = layout.box()
        draw_wrapped(box, hint, icon="LIGHTBULB")
        box.label(text=f"Shortcut: {shortcut}", icon="EVENT_RETURN")


class NAVGUIDE_PT_find(bpy.types.Panel):
    bl_label = "Find a tool"
    bl_idname = "NAVGUIDE_PT_find"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"
    bl_parent_id = "NAVGUIDE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        state = ctx.get_state(context)
        layout.prop(wm, "navguide_query", text="", icon="VIEWZOOM")

        query = wm.navguide_query.strip()
        if not query:
            draw_wrapped(layout, "Type a tool or idea, e.g. extrude, copy, smooth.")
            return
        results = finder.search(query)
        if not results:
            draw_wrapped(layout, "No match. Try another word.", icon="ERROR")
            return
        for tool in results:
            box = layout.box()
            box.label(text=tool["name"], icon="RIGHTARROW")
            draw_wrapped(box, f"Where: {tool['where']}")
            if tool.get("shortcut"):
                box.label(text=f"Shortcut: {tool['shortcut']}", icon="EVENT_RETURN")
            message, action = finder.mode_advice(tool, state)
            if message:
                draw_wrapped(box, message, icon="ERROR")
                if action:
                    box.operator("navguide.run_action", text="Switch mode for me", icon="EDITMODE_HLT").action = action


classes = (NAVGUIDE_PT_main, NAVGUIDE_PT_state, NAVGUIDE_PT_find)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
