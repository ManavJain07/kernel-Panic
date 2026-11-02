"""Properties used by the panels.

Shared file: keep edits small, one block per feature, to avoid merge conflicts.
"""
import bpy
from . import tasks

_enum_items = []  # Blender needs these strings to stay alive


# --- tutorial side --------------------------------------------------------
def task_items(self, context):
    global _enum_items
    _enum_items = [
        (t["id"], t["title"], t.get("summary", "")) for t in tasks.load_tasks()
    ] or [("NONE", "No tasks found", "")]
    return _enum_items


def on_task_change(self, context):
    self.navguide_step = 0


def register():
    wm = bpy.types.WindowManager
    # tutorial
    wm.navguide_task = bpy.props.EnumProperty(name="Task", items=task_items, update=on_task_change)
    wm.navguide_step = bpy.props.IntProperty(default=0, min=0)
    # navigation
    wm.navguide_query = bpy.props.StringProperty(
        name="Find a tool", description="Describe what you want to do", options={"TEXTEDIT_UPDATE"}
    )


def unregister():
    wm = bpy.types.WindowManager
    del wm.navguide_task
    del wm.navguide_step
    del wm.navguide_query
