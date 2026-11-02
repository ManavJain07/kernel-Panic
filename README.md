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

# Blender Navigation Guide

A Blender add-on that tells beginners **where they are** in Blender and
**what they can do next**, so the cluttered interface feels less overwhelming.

> Built for the DevLups Labs hackathon. Problem statement: make digital
> experiences more accessible for people with limited technical literacy.
## How to install :
click on final project . zip and see its description .
## Who it is for
First-time Blender users who feel lost in the interface.

## Features (v0.2)
- Shows current mode, active object and selection count
- Gives a plain-language hint and shortcut for the current situation
- Lessons: mouse controls, add/delete, move/rotate/scale, edit mode, extrude, materials, a simple wall
- "Do it for me" buttons on steps, so beginners see what a step does
- **Lessons (v0.4):** each lesson dims the rest of the interface, shows "Lesson N" at the top of the viewport and a task checklist at the bottom-left. Tasks are crossed out when done (mouse tasks are detected automatically), and a **Hint** button plays a short how-to animation on the right

- **Tutorial flow (v0.5):** click **Start tutorial**, hover over the viewport and press **M**; the bigger workspace opens and the lesson begins. Tasks unlock one at a time and every task is checked automatically. Progress is saved after each task, lessons unlock in order, and a dropdown shows which lessons are done, next, or locked.

- **Two modes (v0.8):** when a tutorial starts, the viewport asks *Keyboard mode* (shortcuts and mouse) or *Accessible mode* (a list of every command the lesson needs on the right of the viewport; one click does what the shortcut does, see `commands.py`). The choice is remembered.
- **Waits for your click (v0.8):** move / rotate / scale / extrude tasks only finish once you confirm with a click (or Enter). The hint animations now show the mouse moving, then clicking.
- **Tutorial World (v0.8):** `python scripts/build_release.py` also builds `dist/BlenderTutorialWorld.zip`, a standalone Blender application template with launchers for Windows, macOS and Linux. Unzip, double-click, and the tutorial opens with no setup (see `tutorial_world/README.txt`).

- **Two tabs (v0.9):** the sidebar now has a **Tutorial** tab and an **Accessibility** tab. Accessibility has big command buttons that work anywhere in Blender, your own shortcuts (keys or mouse buttons, each step *hold* or *tap*, in the order you choose), and your own commands (any Blender operator). While a tutorial runs in Accessible mode, its command list is shown there as well.

- **20 lessons:** lessons 8-20 (duplicate and select many, views, more shapes, shading modes, names and collections, smooth shapes, loop cut / inset / bevel, shiny materials, join and separate, 3D text, light + camera + render, animation, and a final tiny-house project) come with their own hint animations. Every task also works in Accessible mode.
- **navgen:** `scripts/navgen/` makes the hint animations for lessons 8-20: `python scripts/navgen/navgen.py navigation_guide/media [name ...]`.

## Install
1. Install **Blender 4.2 LTS or newer**.
2. Download `navigation_guide.zip` from Releases (or build it, see below).
3. In Blender: `Edit > Preferences > Get Extensions`, open the dropdown at the
   top right, choose **Install from Disk**, and pick the zip.
4. In the 3D Viewport press `N` and open the **Nav Guide** tab.

## Build the zip
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
(The manifest must be at the root of the zip.)

## Project structure
```
navigation_guide/
  blender_manifest.toml   extension metadata
  __init__.py             register / unregister
  context.py              reads Blender state, produces hints
  lesson.py               lessons: dimming, viewport checklist, hints, detection
  lessons/lessons.json    the lesson library
  media/                  hint animation frame sheets
  actions.py              "Do it for me" helper actions
  panel.py                sidebar UI
scripts/validate_lessons.py checks lessons.json
scripts/make_hint_gifs.py builds docs/gifs/*.gif and media/*.png
```




## Team
Manav
Raghya
avadhoot
shashank



so overall a fun project :)

## License
MIT
