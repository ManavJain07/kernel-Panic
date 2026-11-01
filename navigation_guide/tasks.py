"""Loads the beginner task library from tasks/tasks.json."""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "tasks", "tasks.json")
_cache = None


def load_tasks(force=False):
    global _cache
    if _cache is None or force:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _cache = json.load(f)["tasks"]
        except (OSError, ValueError, KeyError):
            _cache = []
    return _cache


def get_task(task_id):
    for task in load_tasks():
        if task["id"] == task_id:
            return task
    return None
