import bpy
from . import access, commands, lesson


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


# ---------------------------------------------------------------------------
# Tab 1: Tutorial
# ---------------------------------------------------------------------------

class NAVGUIDE_MT_lessons(bpy.types.Menu):
    """Dropdown listing the lessons. Lessons unlock one at a time, so only
    the current one can be started (with the Start buttons)."""
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
    bl_label = "Tutorial"
    bl_idname = "NAVGUIDE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tutorial"            # tab name in the N-panel

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Lessons", icon="HELP")

        if lesson.is_active():
            cur = lesson.current()
            done, total = lesson.progress()
            box.label(text=f"Lesson {cur['number']}: {cur['title']}")
            box.label(text=f"{done} of {total} tasks done", icon="CHECKMARK")
            if lesson.phase() == "choose":
                draw_wrapped(box, "Choose Keyboard mode or Accessible mode in the 3D viewport.",
                             icon="INFO")
            elif lesson.phase() == "armed":
                text = ("Click Start lesson in the 3D viewport." if lesson.mode() == "accessible"
                        else "Press M over the 3D viewport to start.")
                draw_wrapped(box, text, icon="INFO")
            if lesson.phase() in {"armed", "running"}:
                box.label(text="Mode: " + ("Accessible (command list)" if lesson.mode() == "accessible"
                                           else "Keyboard"))
            row = box.row()
            row.scale_y = 1.8
            row.operator("navguide.exit_lesson", text="Exit lesson", icon="X")
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
            word = "Continue" if saved else "Start"
            col = box.column(align=True)
            col.scale_y = 2.4                      # big, easy to hit
            op = col.operator("navguide.start_tutorial", text=f"{word} - Keyboard mode", icon="PLAY")
            op.mode = "keyboard"
            op = col.operator("navguide.start_tutorial", text=f"{word} - Accessible mode",
                              icon="MOUSE_LMB")
            op.mode = "accessible"
            draw_wrapped(box, "Accessible mode shows a list of commands you can click, "
                              "so no shortcuts are needed. More help: the Accessibility tab.")
            if saved:
                box.label(text=f"Saved: {saved} of {len(nxt['steps'])} tasks done")
        layout.operator("navguide.reset_progress", text="Reset progress", icon="LOOP_BACK")


# ---------------------------------------------------------------------------
# Tab 2: Accessibility
# ---------------------------------------------------------------------------

class _AccessPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Accessibility"


class NAVGUIDE_PT_access(_AccessPanel, bpy.types.Panel):
    bl_label = "Accessibility"
    bl_idname = "NAVGUIDE_PT_access"

    def draw(self, context):
        layout = self.layout
        draw_wrapped(layout, "Click a command instead of pressing keys, and make your own "
                             "shortcuts: any keys or mouse buttons, in the order you like.",
                     icon="INFO")
        on = access.data()["enabled"]
        row = layout.row()
        row.scale_y = 1.6
        row.operator("navguide.sc_toggle",
                     text="My shortcuts: ON" if on else "My shortcuts: OFF",
                     icon="CHECKBOX_HLT" if on else "CHECKBOX_DEHLT", depress=on)


class NAVGUIDE_PT_access_tutorial(_AccessPanel, bpy.types.Panel):
    """The tutorial's own command list, here as well as over the viewport."""
    bl_label = "Tutorial commands"
    bl_idname = "NAVGUIDE_PT_access_tutorial"
    bl_parent_id = "NAVGUIDE_PT_access"

    @classmethod
    def poll(cls, context):
        return lesson.is_active() and lesson.mode() == "accessible" and lesson.phase() == "running"

    def draw(self, context):
        layout = self.layout
        cur = lesson.current()
        hot = lesson.current_commands()
        draw_wrapped(layout, "Highlighted = what the current task needs.", icon="INFO")
        col = layout.column(align=True)
        for cid in commands.lesson_commands(cur):
            row = col.row()
            row.scale_y = 1.6
            op = row.operator("navguide.run_command", text=commands.label(cid), depress=cid in hot)
            op.cid = cid
            op.tutorial = True


class NAVGUIDE_PT_access_commands(_AccessPanel, bpy.types.Panel):
    bl_label = "Commands"
    bl_idname = "NAVGUIDE_PT_access_commands"
    bl_parent_id = "NAVGUIDE_PT_access"

    def draw(self, context):
        layout = self.layout
        for group in access.GROUPS:
            items = [c for c in access.GENERAL if c[2] == group and c[0] != "start"]
            if not items:
                continue
            box = layout.box()
            box.label(text=group)
            col = box.column(align=True)
            for cid, label, _g, _hint, _fn in items:
                row = col.row()
                row.scale_y = 1.5
                row.operator("navguide.run_command", text=label).cid = cid
        mine = access.data()["custom"]
        if mine:
            box = layout.box()
            box.label(text="My commands")
            col = box.column(align=True)
            for c in mine:
                row = col.row()
                row.scale_y = 1.5
                row.operator("navguide.run_command", text=c["label"]).cid = c["id"]


class NAVGUIDE_PT_access_shortcuts(_AccessPanel, bpy.types.Panel):
    bl_label = "My shortcuts"
    bl_idname = "NAVGUIDE_PT_access_shortcuts"
    bl_parent_id = "NAVGUIDE_PT_access"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        draw_wrapped(layout, "Click a command to set its shortcut. Each step is a key or a "
                             "mouse button. 'Hold' = keep it pressed while you press the next "
                             "one. 'Tap' = press and let go, then the next one.", icon="INFO")
        draw_wrapped(layout, "The LAST step runs the command. Avoid plain left/right click "
                             "as the last step.")
        layout.separator()
        for cid in access.all_ids():
            self.draw_command(layout, cid)
        layout.separator()
        layout.operator("navguide.sc_clear", text="Clear all my shortcuts", icon="LOOP_BACK").cid = ""

    def draw_command(self, layout, cid):
        steps = access.steps_of(cid)
        is_open = cid in access._open
        col = layout.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.3
        op = row.operator("navguide.sc_edit", text=access.label_of(cid),
                          icon="DOWNARROW_HLT" if is_open else "RIGHTARROW", depress=is_open)
        op.cid = cid
        if steps and not is_open:
            col.label(text="    " + access.sequence_text(steps))
        if not is_open:
            return
        box = col.box()
        for i, st in enumerate(steps):
            last = i == len(steps) - 1
            row = box.row(align=True)
            row.scale_y = 1.3
            title = ("Then press: " if last and len(steps) > 1 else "") + access.nice(st["key"])
            op = row.operator("navguide.sc_record", text=title)
            op.cid, op.index = cid, i
            if not last:
                op = row.operator("navguide.sc_hold", text="Hold" if st.get("hold", True) else "Tap",
                                  depress=st.get("hold", True))
                op.cid, op.index = cid, i
            op = row.operator("navguide.sc_remove", text="", icon="X")
            op.cid, op.index = cid, i
        if steps:
            box.label(text=access.sequence_text(steps), icon="CHECKMARK")
            clash = access.conflicts(cid)
            if clash:
                box.label(text="Also used by: " + ", ".join(access.label_of(c) for c in clash),
                          icon="ERROR")
        row = box.row()
        row.scale_y = 1.4
        if len(steps) < access.MAX_STEPS:
            op = row.operator("navguide.sc_record",
                              text="Pick the key" if not steps else "+ Add another key",
                              icon="ADD")
            op.cid, op.index = cid, -1
        if steps:
            row.operator("navguide.sc_clear", text="Clear", icon="TRASH").cid = cid


class NAVGUIDE_PT_access_custom(_AccessPanel, bpy.types.Panel):
    bl_label = "My own commands"
    bl_idname = "NAVGUIDE_PT_access_custom"
    bl_parent_id = "NAVGUIDE_PT_access"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        draw_wrapped(layout, "Add any Blender command as your own button. It can get a "
                             "shortcut above, too.", icon="INFO")
        for c in access.data()["custom"]:
            row = layout.row(align=True)
            row.label(text=f"{c['label']}   ({c['op']})")
            row.operator("navguide.cmd_remove", text="", icon="X").cid = c["id"]
        row = layout.row()
        row.scale_y = 1.8
        row.operator("navguide.cmd_add", text="Add my own command", icon="ADD")


classes = (NAVGUIDE_MT_lessons, NAVGUIDE_PT_main, NAVGUIDE_PT_access,
           NAVGUIDE_PT_access_tutorial, NAVGUIDE_PT_access_commands,
           NAVGUIDE_PT_access_shortcuts, NAVGUIDE_PT_access_custom)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
