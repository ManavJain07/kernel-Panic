"""Navigation sidebar: ONE compact panel with three pages (Guide / Help / Tools).

Only the active page is drawn, so the tab stays short. Owner: navigation team.
"""
import bpy

from . import context as ctx
from . import finder, navigator, troubleshoot


def _text(layout, text, icon="NONE", width=36, alert=False):
    """Tight, wrapped text (small line spacing keeps the sidebar short)."""
    col = layout.column(align=True)
    col.scale_y = 0.8
    col.alert = alert
    line, first = "", True
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            col.label(text=line, icon=icon if first else "NONE")
            first, line = False, word
        else:
            line = f"{line} {word}".strip()
    if line:
        col.label(text=line, icon=icon if first else "NONE")


def _progress(layout, factor, text):
    try:
        layout.progress(factor=factor, text=text)
    except Exception:
        layout.label(text=text)


def _fix_button(layout, cause):
    if cause.get("fix"):
        layout.operator("navguide.fix", text=cause.get("fix_label", "Fix it"), icon="PLAY").fix = cause["fix"]


def _short_mode(state):
    return state["mode"].replace(" Mode", "").replace(" (Mesh)", "")


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
        state = ctx.get_state(context)

        # status line
        layout.label(text=f"{_short_mode(state)} | {(state['active_object'] or 'nothing')[:14]} | {state['selected_count']} sel")

        # display toggles: plain labelled checkboxes
        col = layout.column(align=True)
        col.prop(wm, "navguide_overlay", text="Show hints in the viewport")
        sub = col.column(align=True)
        sub.enabled = wm.navguide_overlay
        sub.prop(wm, "navguide_animate", text="Animated guidance")

        layout.prop(wm, "navguide_page", expand=True)

        if wm.navguide_page == "HELP":
            self._page_help(layout, wm, state)
        elif wm.navguide_page == "TOOLS":
            self._page_tools(layout, wm, state)
        else:
            recipe = navigator.get_recipe(wm.navguide_goal_id) if wm.navguide_goal_id else None
            if recipe is None:
                self._page_picker(layout, wm, state)
            else:
                self._page_guide(layout, wm, state, recipe)

    # ---- GUIDE: choose a goal ----
    def _page_picker(self, layout, wm, state):
        layout.label(text="What do you want to make?")
        row = layout.row(align=True)
        row.prop(wm, "navguide_goal_query", text="", icon="VIEWZOOM")
        row.operator("navguide.start_goal", text="Go").recipe_id = ""
        row = layout.row(align=True)
        row.prop(wm, "navguide_goal_pick", text="")
        row.operator("navguide.start_goal", text="", icon="PLAY").recipe_id = wm.navguide_goal_pick

        hint, shortcut = ctx.get_hint(state)
        box = layout.box()
        _text(box, f"{hint} ({shortcut})", icon="LIGHTBULB")

    # ---- GUIDE: following a goal ----
    def _page_guide(self, layout, wm, state, recipe):
        steps = recipe["steps"]
        index = wm.navguide_goal_step
        baseline = {"object_count": wm.navguide_goal_baseline}

        row = layout.row(align=True)
        row.label(text=recipe["title"], icon="BOOKMARKS")
        row.operator("navguide.goal_nav", text="", icon="X").direction = 0

        if index >= len(steps):
            _progress(layout, 1.0, "Goal complete!")
            layout.operator("navguide.goal_nav", text="Start another goal", icon="LOOP_BACK").direction = 0
        else:
            _progress(layout, index / len(steps), f"Step {index + 1} of {len(steps)}")
            step = steps[index]
            box = layout.box()

            message, action = navigator.problem(step, state)
            if message:
                _text(box, message, icon="ERROR", alert=True)
                if action:
                    box.operator("navguide.run_action", text="Switch mode for me", icon="EDITMODE_HLT").action = action

            _text(box, step["text"])
            if step.get("shortcut"):
                box.label(text=step["shortcut"], icon="EVENT_RETURN")

            live = navigator.progress(step, state)
            if live:
                _progress(box, live[0], live[1])

            row = box.row(align=True)
            if step.get("action"):
                row.operator(
                    "navguide.run_action", text=step.get("action_label", "Do it for me"), icon="PLAY"
                ).action = step["action"]
            manual = navigator.is_done(step, state, baseline) is None
            row.operator(
                "navguide.goal_nav", text="I did this" if manual else "Skip", icon="CHECKMARK" if manual else "FORWARD"
            ).direction = 1
            if not manual:
                box.label(text="Moves on by itself when done", icon="TIME")

        # all steps (collapsed by default)
        layout.prop(
            wm, "navguide_show_steps", text="All steps", emboss=False,
            icon="TRIA_DOWN" if wm.navguide_show_steps else "TRIA_RIGHT",
        )
        if wm.navguide_show_steps:
            col = layout.column(align=True)
            col.scale_y = 0.8
            for i, st in enumerate(steps):
                icon = "CHECKMARK" if i < index else ("RIGHTARROW" if i == index else "DOT")
                col.label(text=st.get("short", st["text"][:30]), icon=icon)

    # ---- HELP ----
    def _page_help(self, layout, wm, state):
        findings = troubleshoot.quick_check(state)
        box = layout.box()
        if findings:
            for c in findings:
                _text(box, c["text"], icon="ERROR", alert=True)
                _fix_button(box, c)
        else:
            box.label(text="Nothing looks wrong right now", icon="CHECKMARK")

        layout.prop(wm, "navguide_problem_query", text="", icon="VIEWZOOM")
        layout.prop(wm, "navguide_problem_pick", text="")

        query = wm.navguide_problem_query.strip()
        if query:
            problems = troubleshoot.search(query)
        elif wm.navguide_problem_pick != "NONE":
            picked = troubleshoot.get_problem(wm.navguide_problem_pick)
            problems = [picked] if picked else []
        else:
            _text(layout, "Describe it or pick one, e.g. can't see my object.")
            return
        if not problems:
            _text(layout, "No match. Try other words.", icon="ERROR")
            return

        for p in problems:
            box = layout.box()
            box.label(text=p["title"], icon="QUESTION")
            causes = troubleshoot.causes_for(p, state)
            shown = causes if wm.navguide_show_all else causes[:3]
            for cause, likely in shown:
                _text(box, cause["text"], icon="ERROR" if likely else "DOT")
                _fix_button(box, cause)
            if len(causes) > 3:
                box.prop(
                    wm, "navguide_show_all", text="Fewer tips" if wm.navguide_show_all else f"+{len(causes) - 3} more tips",
                    emboss=False, icon="TRIA_UP" if wm.navguide_show_all else "TRIA_DOWN",
                )

    # ---- TOOLS ----
    def _page_tools(self, layout, wm, state):
        layout.prop(wm, "navguide_query", text="", icon="VIEWZOOM")
        query = wm.navguide_query.strip()
        if not query:
            _text(layout, "Type a tool or idea, e.g. extrude, mirror, snap, light.")
            box = layout.box()
            box.label(text="Popular", icon="BOOKMARKS")
            col = box.column(align=True)
            col.scale_y = 0.8
            for tool in finder.popular():
                col.label(text=f"{tool['name']}: {tool.get('shortcut', '')}")
            return
        results = finder.search(query, limit=3)
        if not results:
            _text(layout, "No match. Try another word.", icon="ERROR")
            return
        for tool in results:
            box = layout.box()
            box.label(text=tool["name"], icon="RIGHTARROW")
            _text(box, tool["where"])
            if tool.get("what"):
                _text(box, tool["what"])
            if tool.get("shortcut"):
                box.label(text=tool["shortcut"], icon="EVENT_RETURN")
            message, action = finder.mode_advice(tool, state)
            if message:
                _text(box, message, icon="ERROR", alert=True)
                if action:
                    box.operator("navguide.run_action", text="Switch mode for me", icon="EDITMODE_HLT").action = action


classes = (NAVGUIDE_PT_main,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
