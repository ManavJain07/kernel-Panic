"""Properties used by the panels.

Shared file: keep edits small, one block per feature, to avoid merge conflicts.
"""
import bpy
from . import navigator, tasks, troubleshoot

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


# --- navigation side: goal and problem dropdowns ---------------------------
_goal_items = []
_problem_items = []


def goal_items(self, context):
    global _goal_items
    _goal_items = [
        (r["id"], r["title"], r.get("summary", "")) for r in navigator.load_recipes()
    ] or [("NONE", "No goals found", "")]
    return _goal_items


def problem_items(self, context):
    global _problem_items
    _problem_items = [("NONE", "Choose a problem...", "")] + [
        (p["id"], p["title"], p.get("summary", "")) for p in troubleshoot.load_problems()
    ]
    return _problem_items


def register():
    wm = bpy.types.WindowManager
    # tutorial
    wm.navguide_task = bpy.props.EnumProperty(name="Task", items=task_items, update=on_task_change)
    wm.navguide_step = bpy.props.IntProperty(default=0, min=0)
    # navigation: find a tool
    wm.navguide_query = bpy.props.StringProperty(
        name="Find a tool", description="Describe what you want to do", options={"TEXTEDIT_UPDATE"}
    )
    # navigation: guided goal
    wm.navguide_goal_query = bpy.props.StringProperty(
        name="Goal", description="What do you want to make? e.g. a wall"
    )
    wm.navguide_goal_id = bpy.props.StringProperty()
    wm.navguide_goal_step = bpy.props.IntProperty(default=0, min=0)
    wm.navguide_goal_baseline = bpy.props.IntProperty(default=0, min=0)
    wm.navguide_overlay = bpy.props.BoolProperty(
        name="Show hints in the viewport", default=True
    )
    wm.navguide_animate = bpy.props.BoolProperty(
        name="Animated guidance", description="Animated keys, mouse, ring and axis lines", default=True
    )
    wm.navguide_goal_pick = bpy.props.EnumProperty(name="Goal", items=goal_items)
    # navigation: troubleshooter
    wm.navguide_problem_query = bpy.props.StringProperty(
        name="Problem", description="Describe what is going wrong", options={"TEXTEDIT_UPDATE"}
    )
    wm.navguide_problem_pick = bpy.props.EnumProperty(name="Problem", items=problem_items)


def unregister():
    wm = bpy.types.WindowManager
    for name in (
        "navguide_task", "navguide_step", "navguide_query", "navguide_goal_query",
        "navguide_goal_id", "navguide_goal_step", "navguide_goal_baseline", "navguide_overlay",
        "navguide_animate", "navguide_goal_pick", "navguide_problem_query", "navguide_problem_pick",
    ):
        if hasattr(wm, name):
            delattr(wm, name)
