import bpy
from . import context as ctx


class NAVGUIDE_PT_main(bpy.types.Panel):
    bl_label = "Navigation Guide"
    bl_idname = "NAVGUIDE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"  # tab name in the N-panel

    def draw(self, context):
        layout = self.layout
        state = ctx.get_state(context)

        box = layout.box()
        box.label(text="Where you are", icon="INFO")
        box.label(text=f"Mode: {state['mode']}")
        box.label(text=f"Active: {state['active_object'] or 'None'}")
        box.label(text=f"Selected: {state['selected_count']}")

        hint, shortcut = ctx.get_hint(state)
        box = layout.box()
        box.label(text="What you can do next", icon="LIGHTBULB")
        # Wrap long hints into short lines so they fit the narrow sidebar.
        words, line = hint.split(), ""
        for w in words:
            if len(line) + len(w) > 32:
                box.label(text=line)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            box.label(text=line)
        box.label(text=f"Shortcut: {shortcut}", icon="EVENT_RETURN")

        col = layout.column(align=True)
        col.label(text="Quick actions")
        col.operator("navguide.add_cube", icon="MESH_CUBE")
        col.operator("navguide.toggle_edit_mode", icon="EDITMODE_HLT")


classes = (NAVGUIDE_PT_main,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
