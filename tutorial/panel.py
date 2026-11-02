import bpy
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


class NAVGUIDE_MT_lessons(bpy.types.Menu):
    """Dropdown listing the lessons. Lessons unlock one at a time, so only
    the current one can be started (with the Start tutorial button)."""
    bl_label = "Lessons"
    bl_idname = "NAVGUIDE_MT_lessons"

    def draw(self, context):
        layout = self.layout
        for item in lesson.load_lessons():
            text = f"Lesson {item['number']}: {item['title']}"
            status = lesson.lesson_status(item)
            if status == "done":
                layout.label(text=text, icon="CHECKMARK")
            elif status == "current":
                layout.label(text=f"{text}  (up next)", icon="PLAY")
            else:
                row = layout.row()
                row.enabled = False
                row.label(text=text, icon="LOCKED")


class NAVGUIDE_PT_main(bpy.types.Panel):
    bl_label = "Navigation Guide"
    bl_idname = "NAVGUIDE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nav Guide"  # tab name in the N-panel

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Lessons", icon="HELP")

        if lesson.is_active():
            cur = lesson.current()
            done, total = lesson.progress()
            box.label(text=f"Lesson {cur['number']}: {cur['title']}")
            box.label(text=f"{done} of {total} tasks done", icon="CHECKMARK")
            if lesson.phase() == "armed":
                draw_wrapped(box, "Press M over the 3D viewport to start.",
                             icon="INFO")
            box.operator("navguide.exit_lesson", text="Exit lesson", icon="X")
            return

        nxt = lesson.current_lesson()
        if nxt is None:
            box.menu("NAVGUIDE_MT_lessons", text="All lessons done", icon="CHECKMARK")
            box.label(text="Well done - you finished every lesson!")
        else:
            box.menu("NAVGUIDE_MT_lessons",
                     text=f"Lesson {nxt['number']}: {nxt['title']}",
                     icon="DOWNARROW_HLT")
            saved = lesson.saved_step(nxt["id"])
            box.operator(
                "navguide.start_tutorial",
                text="Continue tutorial" if saved else "Start tutorial",
                icon="PLAY",
            )
            if saved:
                box.label(text=f"Saved: {saved} of {len(nxt['steps'])} tasks done")
        layout.operator("navguide.reset_progress", text="Reset progress", icon="LOOP_BACK")


classes = (NAVGUIDE_MT_lessons, NAVGUIDE_PT_main)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
