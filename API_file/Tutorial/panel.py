import bpy
from . import context as ctx
from . import tasks


def draw_wrapped(layout, text, width=34, icon="NONE"):
    """Draw long text as several short labels so it fits the sidebar."""
    line = ""
    first = True
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            layout.label(text=line, icon=icon if first else "NONE")
            first = False
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        layout.label(text=line, icon=icon if first else "NONE")


class NAVGUIDE_PT_main(bpy.types.Panel):
    bl_label = "Navigation Guide"
    bl_idname = "NAVGUIDE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"  # tab name in the N-panel

    def draw(self, context):
        layout = self.layout
        state = ctx.get_state(context)

        # --- live context ------------------------------------------------
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

        # --- guided task -------------------------------------------------
        wm = context.window_manager
        layout.separator()
        layout.label(text="Learn a task")
        layout.prop(wm, "navguide_task", text="")

        task = tasks.get_task(wm.navguide_task)
        if task:
            steps = task["steps"]
            i = wm.navguide_step
            box = layout.box()

            if i >= len(steps):
                box.label(text="Task complete!", icon="CHECKMARK")
                box.operator("navguide.step", text="Do it again", icon="LOOP_BACK").direction = 0
            else:
                step = steps[i]
                box.label(text=f"Step {i + 1} of {len(steps)}", icon="TRACKING_FORWARDS")
                draw_wrapped(box, step["text"])
                if step.get("shortcut"):
                    box.label(text=f"Shortcut: {step['shortcut']}", icon="EVENT_RETURN")
                if step.get("action"):
                    op = box.operator(
                        "navguide.run_action",
                        text=step.get("action_label", "Do it for me"),
                        icon="PLAY",
                    )
                    op.action = step["action"]

                row = box.row(align=True)
                back = row.row(align=True)
                back.enabled = i > 0
                back.operator("navguide.step", text="Back", icon="TRIA_LEFT").direction = -1
                nxt = "Finish" if i == len(steps) - 1 else "Next"
                row.operator("navguide.step", text=nxt, icon="TRIA_RIGHT").direction = 1

        layout.separator()
        layout.label(text="Tip: keep your mouse over the", icon="QUESTION")
        layout.label(text="3D viewport when using shortcuts.")


classes = (NAVGUIDE_PT_main,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
