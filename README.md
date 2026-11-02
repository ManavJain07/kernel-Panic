# Blender Navigation Guide

A Blender add-on that tells beginners **where they are** in Blender and
**what they can do next**, so the cluttered interface feels less overwhelming.

> Built for the DevLups Labs hackathon. Problem statement: make digital
> experiences more accessible for people with limited technical literacy.

**Current version: v0.7.0** by team Kernel-Panic.

## Who it is for
First-time Blender users who feel lost in the interface.

## What's new in v0.7
- New **My keys (accessibility)** panel (`keys.py`): learners can choose their own key for 12 actions (start, add menu, move, rotate, scale, edit mode, delete, undo, extrude, select vertices / edges / faces) if they cannot press the default ones
- The tutorial accepts the learner's key, shows "Your keys" on the task card, and lets them start a lesson with their own key; Blender's normal keys keep working
- Custom keys are normal Blender keymap items, so they also appear in Preferences > Keymap and are saved with the user's preferences
- Tasks now list which key actions apply (`keys` field in `lessons.json`)
- Animations for move, move-on-axis, rotate and scale were changed in this version

## Lessons (7 lessons, 33 tasks)
| # | Lesson | Tasks | Notes |
|---|---|---|---|
| 1 | Mouse controls | 4 |  |
| 2 | Add and delete objects | 4 |  |
| 3 | Move, rotate and scale | 6 |  |
| 4 | Edit an object's shape | 5 |  |
| 5 | Extrude a face | 4 |  |
| 6 | Add colour to an object | 4 | keeps normal layout (uses Properties editor) |
| 7 | Build a simple wall | 6 |  |

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
  lesson.py               lesson mode: overlay drawing, task flow, progress, start/exit operators
  panel.py                Nav Guide sidebar tab
  actions.py              "Do it for me" helper actions
  detect.py               task detectors that decide when a task is done
  keys.py                 My keys: learner-chosen keys (accessibility)
  context.py              reads Blender state, produces hints
  lessons/lessons.json    the lesson library
  media/                  how-to animations (sprite sheets) + meta.json
scripts/validate_lessons.py, validate_media.py check the lesson and animation data
```

`context.py` is not imported by any other file in this version. It is a leftover from v0.4 and can be removed or reused.

## Check your changes
```
python scripts/validate_lessons.py
python scripts/validate_media.py
```

## Roadmap
- [x] Skeleton panel and context detection
- [x] Lesson mode with dimmed UI
- [x] Auto-detect step completion (all 33 tasks)
- [x] Saved progress and locked lessons
- [x] Hint animations for every task
- [x] One-task-at-a-time card with progress bar
- [x] Accessibility: learner-chosen keys
- [ ] More lessons (Boolean, modifiers, cameras)
- [ ] User testing with beginners

## Team
Kernel-Panic. 
Manav
Raghya
avadhoot 
Shashank


## License
MIT
