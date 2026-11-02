# Blender Navigation Guide

A Blender add-on that tells beginners **where they are** in Blender and
**what they can do next**, so the cluttered interface feels less overwhelming.

> Built for the DevLups Labs hackathon. Problem statement: make digital
> experiences more accessible for people with limited technical literacy.

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

## Roadmap
- [x] Skeleton panel and context detection
- [x] Lesson library (JSON) with task checklists and hint animations
- [x] Step checklist UI
- [x] Helper operators
- [ ] Auto-detect step completion
- [ ] More tasks (Boolean, modifiers, cameras)
- [ ] User testing with beginners

## Team
Add names and roles here.

## License
MIT
