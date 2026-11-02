"""Navigation side of the sidebar: where you are, what next, find a tool.

Owner: navigation team.
"""
import bpy
from . import context as ctx
from . import finder
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
        state = ctx.get_state(context)

        # --- where you are ----------------------------------------------
        box = layout.box()
        box.label(text="Where you are", icon="INFO")
        box.label(text=f"Mode: {state['mode']}")
        box.label(text=f"Active: {state['active_object'] or 'None'}")
        box.label(text=f"Selected: {state['selected_count']}")

        hint, shortcut = ctx.get_hint(state)
        box = layout.box()
        box.label(text="What you can do next", icon="LIGHTBULB")
        draw_wrapped(box, hint)
        box.label(text=f"Shortcut: {shortcut}", icon="EVENT_RETURN")

        # --- find a tool ------------------------------------------------
        wm = context.window_manager
        layout.separator()
        layout.label(text="Find a tool")
        layout.prop(wm, "navguide_query", text="", icon="VIEWZOOM")

        query = wm.navguide_query.strip()
        if not query:
            draw_wrapped(layout, "Type what you want to do, e.g. extrude, make a hole, add colour.")
            return

        results = finder.search(query)
        if not results:
            draw_wrapped(layout, "No match. Try another word, e.g. move, delete, smooth, camera.", icon="ERROR")
            return

        for tool in results:
            box = layout.box()
            box.label(text=tool["name"], icon="RIGHTARROW")
            draw_wrapped(box, tool["what"])
            draw_wrapped(box, f"Where: {tool['where']}")
            if tool.get("shortcut"):
                box.label(text=f"Shortcut: {tool['shortcut']}", icon="EVENT_RETURN")

            message, action = finder.mode_advice(tool, state)
            if message:
                draw_wrapped(box, message, icon="ERROR")
                if action:
                    op = box.operator("navguide.run_action", text="Switch mode for me", icon="EDITMODE_HLT")
                    op.action = action


classes = (NAVGUIDE_PT_main,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
