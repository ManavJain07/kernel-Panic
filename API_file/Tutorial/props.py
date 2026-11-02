"""Properties that remember the chosen task and the current step."""
import bpy
from . import tasks

_enum_items = []  # Blender needs these strings to stay alive


def task_items(self, context):
    global _enum_items
    _enum_items = [
        (t["id"], t["title"], t.get("summary", "")) for t in tasks.load_tasks()
    ] or [("NONE", "No tasks found", "")]
    return _enum_items


def on_task_change(self, context):
    self.navguide_step = 0


def register():
    bpy.types.WindowManager.navguide_task = bpy.props.EnumProperty(
        name="Task", items=task_items, update=on_task_change
    )
    bpy.types.WindowManager.navguide_step = bpy.props.IntProperty(default=0, min=0)


def unregister():
    del bpy.types.WindowManager.navguide_task
    del bpy.types.WindowManager.navguide_step
