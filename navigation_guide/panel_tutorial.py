"""Tutorial side of the sidebar: guided tasks with a step checklist.

Owner: tutorial team.
"""
import bpy
from . import tasks
from .utils import draw_wrapped


class NAVGUIDE_PT_tutorial(bpy.types.Panel):
    bl_label = "Learn a task"
    bl_idname = "NAVGUIDE_PT_tutorial"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
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


classes = (NAVGUIDE_PT_tutorial,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
