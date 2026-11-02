# Nav Guide: overview of the `nav-guide` branch

> Part of **kernel-Panic**, built for the DevLups Labs hackathon.
> This document describes the **navigation** half of the project (the **Nav Guide** tab).
> The **Basic Tutorials** tab lives on the `Tutorial` branch and is documented separately.

## What it does

Blender's interface is crowded, and beginners often don't know where they are or what to do next.
The Nav Guide is a Blender add-on that reads Blender's **current state** (mode, active object,
selection) and walks a stuck user through the next steps. It does this with plain-language hints,
guided goals, animated viewport cues and a troubleshooter.

Open it in Blender: **3D Viewport → press `N` → Nav Guide tab**.

## Features (v0.7)

- **Live context**: shows the current mode, active object and selection, with a plain-language hint
  and shortcut for the situation you are in.
- **Compact sidebar** with three pages: **Guide**, **Help** and **Tools**, a status line,
  overlay/animation toggles and a live progress bar.
- **Guided goals**: 20 step-by-step goals (76 steps in total). Each step highlights what to do next
  and can run one-click helpers.
- **Viewport overlay and animations**: keycap prompts with press glow, a mouse icon, pulsing rings,
  click ripples, travelling axis lines, a "Step done!" burst, confetti when a goal is completed,
  and a nudge if you stay stuck.
- **"I'm stuck" troubleshooter**: 18 common beginner problems (63 possible causes), with search and
  one-click fixes.
- **Find-a-tool**: a searchable library of 70 commands that tells you where a command lives and
  how to run it.

## Install

1. Install **Blender 4.2 LTS or newer**.
2. Get `navigation_guide.zip` (from Releases, or build it as shown below).
3. In Blender: `Edit → Preferences → Get Extensions`, open the dropdown at the top right,
   choose **Install from Disk**, and pick the zip.
4. In the 3D Viewport press `N` and open the **Nav Guide** tab.

### Build the zip

```
cd navigation_guide
zip -r ../navigation_guide.zip .
```

The manifest (`blender_manifest.toml`) must be at the root of the zip.

## Code layout

```
navigation_guide/
  blender_manifest.toml   extension metadata
  __init__.py             registers all modules
  context.py              reads Blender state, produces hints (no UI)
  navigator.py            decides the next step from the live state
  session.py              runs a guided-goal session
  goal_ops.py             one-click helper and fix operators
  overlay.py              viewport drawing and animations
  panel_nav.py            the Nav Guide sidebar panel
  finder.py               Find-a-tool search
  troubleshoot.py         "I'm stuck" troubleshooter logic (no bpy)
  tasks.py                loads task data
  operators.py            basic helper operators
  props.py                scene / window properties
  utils.py                shared UI helpers (e.g. wrapped text)
  panel_tutorial.py       tutorial panel (owned by the tutorial branch)
  tasks/ tools/ recipes/ problems/    JSON data libraries
scripts/
  validate_*.py           checkers for the JSON libraries
Docs/nav-guide/           per-version notes (v0.1 to v0.7)
```

Ownership: files above are **navigation-owned**, except `panel_tutorial.py` and the tutorial
data, which belong to the tutorial branch. Edit only your own files to avoid merge conflicts.

## Data libraries

Content lives in JSON, so new goals and fixes can be added without touching the Python code:

| Folder | Holds |
|---|---|
| `tasks/` | tutorial-style tasks |
| `tools/` | the Find-a-tool command library |
| `recipes/` | guided goals (steps and actions) |
| `problems/` | troubleshooter problems and causes |

Each library has a checker in `scripts/` (`validate_tasks.py`, `validate_tools.py`,
`validate_recipes.py`, `validate_problems.py`). Run one from the repo root, for example
`python scripts/validate_recipes.py`, before merging changes to its data.

## Version history

Notes for each version are in [`Docs/nav-guide/`](.):

| Version | Focus |
|---|---|
| v0.1 | Skeleton panel, mode/selection hints, one-click helpers |
| v0.2 | Task library and step checklist, props, validation script |
| v0.3 | Find-a-tool, tools library, nav and tutorial panels split |
| v0.4 | Guided goals, live-state navigator, overlay banner, recipes |
| v0.5 | Animated viewport guidance, 15 goals, "I'm stuck" troubleshooter |
| v0.6 | Compact tabbed panel (Guide / Help / Tools), livelier animations, stuck nudge |
| v0.7 | 70 commands, 20 goals, 18 troubleshooter problems, smoother overlay |

## Testing status

- v0.1 to v0.6 were run in Blender.
- **v0.7:** TODO, confirm before release. Note which commands and goals have been checked in Blender.

## Working on this branch

- Branch: `nav-guide` (navigation). Tutorial work: `Tutorial`. Stable: `main`.
- Never commit directly to `main`; merge through a Pull Request.
- One commit per version, with the notes in a separate commit:
  `docs: add v0.x notes`, then `nav: v0.x <summary>`.
- Merge `origin/main` into your branch before opening a Pull Request, so conflicts are fixed on the branch.
- Shared files to coordinate on: `__init__.py`, `blender_manifest.toml`, the root `README.md`.

## Team

- Manav: team lead, tutorial
- Raghya: navigation (this branch)
- Avadhoot
- Shashank

## License

See [`LICENSE`](../../LICENSE).
