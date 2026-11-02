"""Navigation side of the sidebar. Owner: navigation team.

Main panel  = guided goal ("What do you want to make?")
Sub panels  = where you are, "I'm stuck", and quick tool lookup.
"""
import bpy

from . import context as ctx
from . import finder, navigator, troubleshoot
from .utils import draw_wrapped


def _fix_button(layout, cause):
    if cause.get("fix"):
        op = layout.operator("navguide.fix", text=cause.get("fix_label", "Fix it"), icon="PLAY")
        op.fix = cause["fix"]


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
        row = layout.row()
        row.enabled = wm.navguide_overlay
        row.prop(wm, "navguide_animate")

    # ---- no goal yet ----
    def _draw_picker(self, layout, wm):
        layout.label(text="What do you want to make?", icon="QUESTION")
        layout.prop(wm, "navguide_goal_query", text="")
        layout.operator("navguide.start_goal", text="Guide me", icon="PLAY").recipe_id = ""
        layout.separator()
        layout.label(text="Or choose a goal:")
        layout.prop(wm, "navguide_goal_pick", text="")
        op = layout.operator("navguide.start_goal", text="Start this goal", icon="PLAY")
        op.recipe_id = wm.navguide_goal_pick

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


class NAVGUIDE_PT_stuck(bpy.types.Panel):
    bl_label = "I'm stuck, what's wrong?"
    bl_idname = "NAVGUIDE_PT_stuck"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"
    bl_parent_id = "NAVGUIDE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        state = ctx.get_state(context)

        # 1. automatic check of the live scene
        findings = troubleshoot.quick_check(state)
        box = layout.box()
        if findings:
            box.label(text="Right now I notice:", icon="ERROR")
            for c in findings:
                draw_wrapped(box, c["text"])
                _fix_button(box, c)
        else:
            box.label(text="Nothing looks wrong right now.", icon="CHECKMARK")

        # 2. describe a problem
        layout.separator()
        layout.label(text="Describe the problem")
        layout.prop(wm, "navguide_problem_query", text="", icon="VIEWZOOM")
        layout.prop(wm, "navguide_problem_pick", text="")

        query = wm.navguide_problem_query.strip()
        if query:
            problems = troubleshoot.search(query)
        elif wm.navguide_problem_pick != "NONE":
            picked = troubleshoot.get_problem(wm.navguide_problem_pick)
            problems = [picked] if picked else []
        else:
            draw_wrapped(layout, "Try: can't see my object, shortcut does nothing, undo, laptop.")
            return

        if not problems:
            draw_wrapped(layout, "No match. Try other words.", icon="ERROR")
            return

        for p in problems:
            box = layout.box()
            box.label(text=p["title"], icon="QUESTION")
            for cause, likely in troubleshoot.causes_for(p, state):
                draw_wrapped(box, cause["text"], icon="ERROR" if likely else "DOT")
                _fix_button(box, cause)


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


classes = (NAVGUIDE_PT_main, NAVGUIDE_PT_state, NAVGUIDE_PT_stuck, NAVGUIDE_PT_find)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
