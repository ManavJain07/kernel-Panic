# Contributing

## Workflow
1. `git pull origin main`
2. `git checkout -b feature/<short-name>`
3. Make changes, then `git add . && git commit -m "Clear message"`
4. `git push origin feature/<short-name>` and open a Pull Request
5. One teammate reviews before merging. Never push straight to `main`.

## Adding or editing a task
Tasks live in `navigation_guide/tasks/tasks.json`. Each step looks like:

```json
{
  "text": "Plain-language instruction a beginner can follow.",
  "shortcut": "Tab",
  "action": "toggle_edit_mode",
  "action_label": "Switch mode"
}
```

`action` and `action_label` are optional. Allowed actions are the names in
`ACTIONS` inside `navigation_guide/operators.py`.

**Every step must be tested by hand in Blender 4.2 before it is merged.**
Then run:

```
python scripts/validate_tasks.py
```

## Adding a new helper action
Write a function in `operators.py`, add it to the `ACTIONS` dict, and use its
name in `tasks.json`.

## Who edits what
Two sub-teams work on the same add-on, so keep to your own files.

| Area | Navigation team | Tutorial team |
|---|---|---|
| Panel | `panel_nav.py` | `panel_tutorial.py` |
| Logic | `finder.py`, `context.py` | `tasks.py` |
| Data | `tools/tools.json` | `tasks/tasks.json` |
| Validator | `scripts/validate_tools.py` | `scripts/validate_tasks.py` |

Shared files (`__init__.py`, `props.py`, `operators.py`, `utils.py`): make
small edits, one block per feature, and tell the other team in your pull request.

## Verifying tools
Every entry in `tools/tools.json` has `"verified": false` until someone has
tested the menu path and shortcut in Blender 4.2. After testing, change it to
`true`. `python scripts/validate_tools.py` lists what is still unverified.
