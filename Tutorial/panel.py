import bpy
from . import context as ctx
from . import lesson


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

        # --- lessons -----------------------------------------------------
        box = layout.box()
        box.label(text="Lessons", icon="HELP")
        if lesson.is_active():
            cur = lesson.current()
            done, total = lesson.progress()
            box.label(text=f"Lesson {cur['number']}: {cur['title']}")
            box.label(text=f"{done} of {total} tasks done", icon="CHECKMARK")
            full = getattr(context.screen, "show_fullscreen", False)
            box.operator(
                "navguide.toggle_maximize",
                text="Normal layout" if full else "Bigger workspace",
                icon="FULLSCREEN_EXIT" if full else "FULLSCREEN_ENTER",
            )
            box.operator("navguide.exit_lesson", text="Exit lesson", icon="X")
        else:
            for item in lesson.load_lessons():
                op = box.operator(
                    "navguide.start_lesson",
                    text=f"Lesson {item['number']}: {item['title']}",
                    icon="PLAY",
                )
                op.lesson_id = item["id"]

        # --- live context ------------------------------------------------
        box = layout.box()
        box.label(text="Where you are", icon="INFO")
        box.label(text=f"Mode: {state['mode']}")
        box.label(text=f"Active: {state['active_object'] or 'None'}")
        box.label(text=f"Selected: {state['selected_count']}")

        hint, shortcut = ctx.get_hint(state)
        box = layout.box()
        box.label(text="What you can do next", icon="LIGHT")
        draw_wrapped(box, hint)
        box.label(text=f"Shortcut: {shortcut}", icon="EVENT_RETURN")

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
