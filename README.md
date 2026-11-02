# Blender Navigation Guide

> A Blender add-on that makes Blender easier to learn, easier to find your way around, and easier to **operate for people who cannot use the standard keyboard-and-mouse workflow**.

Blender is powerful, but for a first-time user the interface is overwhelming: hundreds of buttons, shortcuts that must be memorised, and no hint about what to do next. For people who use one hand, have limited reach, or rely on switch or adaptive devices, many of Blender's key combinations are not just confusing, they are impossible to press.

**Blender Navigation Guide** adds three tabs to the 3D Viewport sidebar that tackle this from different angles:

| Tab | What it does | Who it helps most |
|---|---|---|
| 🎓 **Tutorial** | 20 hands-on lessons that check your progress automatically and unlock one at a time | Complete beginners |
| ♿ **Accessibility** | One-click commands, your own custom shortcuts, and your own command buttons | Anyone who cannot or does not want to use Blender's default shortcuts |
| 🧭 **Nav Guide** | Goal-based guidance, a "I'm stuck" troubleshooter and a tool finder | Anyone who feels lost mid-project |

> Built by team **Kernel-Panic** for the Devlup Labs hackathon.
> Problem statement: make digital experiences more accessible for people with limited technical literacy.

**Current version:** 0.10.0 · **Requires:** Blender 4.2 LTS or newer · **License:** MIT

---

## Table of contents

- [Why this project exists](#why-this-project-exists)
- [Installation](#installation)
- [Where to find it](#where-to-find-it)
- [Tab 1: Tutorial](#tab-1-tutorial)
- [Tab 2: Accessibility](#tab-2-accessibility)
- [Tab 3: Nav Guide](#tab-3-nav-guide)
- [How the tabs work together](#how-the-tabs-work-together)
- [Your data and settings](#your-data-and-settings)
- [Build the zip](#build-the-zip)
- [Project structure](#project-structure)
- [Adding your own content](#adding-your-own-content)
- [Roadmap](#roadmap)
- [Team](#team)
- [License](#license)

---

## Why this project exists

Three barriers keep people away from Blender, and each tab removes one of them:

1. **"I don't know where to start."** The Tutorial tab teaches the basics in small, checked steps, so you always know what to do next.
2. **"I can't press those keys."** The Accessibility tab turns every common action into a big button and lets you design your own shortcuts from any keys or mouse buttons, in any order.
3. **"I'm lost in the middle of my project."** The Nav Guide tab reads what you are doing right now and tells you the next step, what went wrong, or where a tool lives.

Everything is driven by what Blender is *actually doing*: the add-on reads the live scene (mode, selection, object sizes, modifiers, materials, shading), so tasks tick themselves off and advice matches your situation instead of being generic.

---

## Installation

1. Install **Blender 4.2 LTS or newer**.
2. Download `navigation_guide.zip` from the **Releases** page (or [build it yourself](#build-the-zip)).
3. In Blender, open `Edit > Preferences > Get Extensions`.
4. Click the dropdown at the top right and choose **Install from Disk**, then pick the zip.
5. Make sure the add-on is enabled.

## Where to find it

Hover over the **3D Viewport** and press **`N`** to open the sidebar. You will see three tabs along its edge:

- **Tutorial**
- **Accessibility**
- **Nav Guide**

> **Tip:** keep your mouse over the 3D Viewport when using shortcuts. Blender sends key presses to whichever area the mouse is over.

---

## Tab 1: Tutorial

A structured course of **20 lessons and 89 tasks** that takes you from "how do I rotate the view?" to rendering a finished scene. Every task is verified automatically against Blender's live state, so you never have to tick anything off yourself.

### The lessons

Lessons **unlock one at a time**, so you cannot skip ahead and miss the basics. The dropdown in the sidebar shows each lesson as done ✔, up next ▶, or locked 🔒.

| # | Lesson | Tasks | What you learn |
|---|---|:-:|---|
| 1 | Mouse controls | 4 | Orbit, pan, zoom and select |
| 2 | Add and delete objects | 4 | The Add menu, selecting, deleting |
| 3 | Move, rotate and scale | 6 | `G`, `R`, `S`, axis locking, typing exact values, undo |
| 4 | Edit an object's shape | 5 | Edit Mode, vertex/edge/face select, moving a face |
| 5 | Extrude a face | 4 | Pulling new shape out of a face with `E` |
| 6 | Add colour to an object | 4 | Materials, base colour, Material Preview |
| 7 | Build a simple wall | 6 | Scaling and lifting a cube into a wall using exact numbers |
| 8 | Duplicate and select many objects | 5 | `Shift+D`, multi-select, select all / none |
| 9 | Look at your scene from every side | 4 | Front, top, perspective vs orthographic, frame selected |
| 10 | Add more shapes | 4 | Sphere, cylinder, plane and the Blender monkey |
| 11 | See your model in different ways | 4 | Wireframe, solid, X-ray, Material Preview |
| 12 | Name and organise your objects | 4 | Rename, hide / unhide, collections |
| 13 | Smooth shapes | 4 | Shade Smooth and Subdivision Surface |
| 14 | Edit Mode tools | 5 | Loop cut, inset, bevel |
| 15 | Shiny, rough and metal materials | 5 | Metallic and Roughness |
| 16 | Join and separate | 4 | `Ctrl+J` and separating by loose parts |
| 17 | Add 3D text | 3 | Text objects, editing words, extruding to 3D |
| 18 | Light, camera, render | 3 | Sun light, camera view, `F12` render |
| 19 | Make it move | 5 | Keyframes, the timeline, playback |
| 20 | **Final project: build a tiny house** | 6 | Combines everything: ground, walls, roof, colour, render |

### Two ways to learn: Keyboard mode and Accessible mode

When you press **Start** (or **Continue**), the viewport asks how you want to work:

- **Keyboard mode**: use Blender's shortcuts and the mouse, exactly as you will in real projects.
- **Accessible mode**: a **command list** appears on the right of the viewport. One click on a command does what the shortcut would do, so the whole course can be finished **with the mouse alone**, or with any single-switch or pointer device. Your choice is remembered for next time.

### What a lesson looks like

1. **Choose a mode.** A card in the viewport asks Keyboard or Accessible.
2. **Get ready.** The interface dims so your attention stays on the viewport. In Keyboard mode an animated **M** key asks you to press `M` over the viewport to begin; in Accessible mode you click **Start lesson**. You can even assign your own start key in the Accessibility tab.
3. **Work through the tasks.** The viewport is enlarged for focus (lessons that need the Properties editor, like materials, keep the normal layout), and a **task card** shows one task at a time:
   - a counter and progress bar (for example `2/6`),
   - the task title and a plain-language **hint**,
   - the **shortcut** to use,
   - a live **"not yet" message** that explains what is still missing,
   - a **Do it for me** button on tasks where it helps, so you can *see* what a step does,
   - a short **looping animation** demonstrating the action (Mac users get Mac-specific key animations). You can hide or show it.
4. **Tasks complete themselves.** The add-on checks Blender about ten times a second. When you finish, the card flashes **"Task completed"** and moves on. For move, rotate, scale and extrude, it waits for the click that *confirms* the change, just like real Blender.
5. **Finish the lesson.** A **Lesson complete!** card offers **Next lesson** or **Finish**, and the next lesson unlocks.

### Designed to be forgiving

- **Progress is saved after every task.** Close Blender and the sidebar offers **Continue** (with "Saved: 3 of 6 tasks done") next time.
- **Exit any time** with the **Exit lesson** button. Your layout and viewport settings are restored.
- **Reset progress** starts the course again.
- Typed values (such as scale `4` or `0.2`) are accepted with a small tolerance, so you are not penalised for tiny differences.
- If you set your own shortcuts, the task card shows them: *"Your keys: Move = Hold Shift, then press Q"*.

---

## Tab 2: Accessibility

Some people cannot press certain keys or key combinations: one-handed users, people with limited reach, users of switch or adaptive devices, or people with extra mouse buttons they would rather use. This tab makes Blender's most-used commands available **as buttons** and lets you **design your own shortcuts**. It works **anywhere in Blender**, not only in the tutorial.

The tab has four sections:

### 1. Master switch

A large **My shortcuts: ON / OFF** toggle turns all of your custom shortcuts on or off in one click. Blender's normal keys always keep working.

### 2. Commands: click instead of pressing keys

Big, easy-to-hit buttons for **33 everyday commands**, grouped so they are easy to scan:

| Group | Commands |
|---|---|
| **Add** | Open the Add menu, cube, plane, sphere, cylinder, monkey |
| **Transform** | Move (free), move along X / Y / Z, rotate, scale |
| **Edit** | Delete, duplicate, extrude, undo, redo |
| **Select** | Select all, select none, invert selection |
| **Mode** | Edit Mode on / off, select vertices, edges, faces |
| **View** | Front, right, top, camera view, zoom to selected, show everything, solid shading, Material Preview |
| **File** | Save file |

There is also a **Start the lesson** command, which you can bind to your own key so you can begin tutorial lessons without touching `M`.

Commands are context-aware. If one cannot run (for example, *Extrude* while in Object Mode), Blender shows a short, friendly message such as "Switch to Edit Mode first" instead of failing silently.

### 3. My shortcuts: build your own key combinations

Click any command to open its shortcut editor. A shortcut is made of **one to four steps**, and each step can be **any keyboard key or mouse button**, including extra side buttons (4 to 7) and the scroll wheel.

- **Hold**: keep this key pressed while you press the next one (`Hold Shift, then press A`).
- **Tap**: press and release, then press the next one within 1.5 seconds (`Press Q, then press W`).
- **The last step runs the command.**

**Examples**

```
Hold Shift, then press A              the usual Blender way, in order
Press Q, then press W                 one key after the other, no chord needed
Hold Mouse side button, then press G  a mouse button combined with a key
```

Other helpful details:

- Click **Pick the key**, then press the key or click the button you want. **Esc** cancels.
- Each step can be re-recorded, switched between Hold and Tap, or removed.
- The panel shows your sequence in plain words, and warns you with **"Also used by: …"** if two commands share a shortcut.
- **Clear** removes one shortcut; **Clear all my shortcuts** asks for confirmation first.
- Left and right Shift / Ctrl / Alt count as the same key.
- The key that finishes one of your shortcuts is used up by it, so choose keys you do not need for something else. It is best not to end a shortcut with a plain left or right click.

### 4. My own commands: add anything Blender can do

Blender has thousands of operations. Add any of them as your own named button:

1. Click **Add my own command**.
2. Give it a name (for example, "Add monkey").
3. Enter the Blender operator name (for example, `mesh.primitive_monkey_add`). The add-on checks that it exists before saving.

Your commands appear under **My commands**, work as buttons, and **can be given shortcuts** just like the built-in ones.

### Tutorial commands (appears automatically)

While an **Accessible mode** lesson is running, this section mirrors the lesson's command list inside the sidebar, with the commands the current task needs **highlighted**. You can therefore click them from the sidebar *or* from the viewport, whichever is easier.

---

## Tab 3: Nav Guide

Where the Tutorial teaches a fixed course, the Nav Guide helps with **whatever you are making right now**. It continuously reads the state of your scene and responds to it.

At the top of the tab:

- A **status line** shows your current mode, active object and selection count (for example `Object | Cube | 1 sel`).
- **Show hints in the viewport** turns the on-screen guidance on or off.
- **Animated guidance** turns the animations on or off (useful if you find motion distracting).
- Three pages switch the view: **Guide**, **Help** and **Tools**. Only the active page is drawn, so the sidebar stays short.

### Page 1: Guide (goal-based help)

Tell the add-on **what you want to make** and it walks you there step by step.

**Choose a goal** by typing it ("a wall", "window hole") and pressing **Go**, or by picking from the dropdown. There are **20 goals**:

| | | |
|---|---|---|
| Move around the 3D view | Build a wall | Build a floor slab |
| Build a column | Add a large ground plane | Copy an object |
| Repeat an object in a row (Array) | Cut a window or door hole (Boolean) | Pull a shape out of a face (Extrude) |
| Round off sharp edges (Bevel) | Add colour to an object | Turn an object 90 degrees |
| Join objects into one | Clear the scene | Save your project |
| Model one side, get both (Mirror) | Build stairs | Make an object smooth |
| Light the scene and render a picture | Group objects so they move together | |

**What makes it smart**

- **It starts where you are.** If you have already done the first steps, it skips them ("Skipped 2 step(s) you have already done").
- **It moves on by itself.** Each step has a condition checked against live Blender state. When you do it, the guide advances. Steps that cannot be detected show an **I did this** button instead.
- **It warns you about the wrong mode.** If a step needs Object Mode and you are in Edit Mode, a warning appears with a **Switch mode for me** button.
- **It can do steps for you.** **Do it for me** buttons (add a cube, and so on) let you see what a step does.
- **It shows live progress** inside a step (for example, how close your wall's length is to the target), plus an overall **Step X of Y** bar.
- **You stay in control.** Skip steps, stop the goal with ✕, or expand **All steps** to see the whole plan.
- With no goal active, a **contextual hint** tells you what you can do right now (for example, "Nothing is selected. Add an object to start. (Shift + A)").

**Guidance inside the 3D viewport**

A banner in the viewport shows the current step, so you do not have to look away from your model. With animations on, you also get:

- animated **keycaps** that press down one after another,
- an animated **mouse** with click ripples and a moving dot for drags,
- **ripple rings and a bobbing arrow** highlighting the active object,
- an **axis line** with travelling dashes and a bouncing axis letter for X / Y / Z moves,
- a **success burst** when a step completes and **confetti** when a goal is finished,
- a gentle nudge after about 15 seconds on one step: *"Stuck? Open the Help tab."*

All drawing is wrapped defensively, so a display problem can never break Blender.

### Page 2: Help (the "I'm stuck" troubleshooter)

Most beginner problems come down to a handful of causes. The Help page finds the one that applies to **you**.

- **Automatic quick check.** It scans your scene and flags things that look wrong right now, each with a one-click **fix** button, or shows "Nothing looks wrong right now".
- **Describe it or pick it.** Type "can't see my object" or choose from **18 common problems** covering **63 causes**:

  *I can't see my object · My shortcuts do nothing · I'm stuck in another mode · I can't select anything · Everything looks like wireframe or see-through · Faces look dark, black or inside-out · I did something by accident · No middle mouse button or numpad · My object looks blocky or rough · My object is tiny, huge or off-centre · A panel, toolbar or tab disappeared · Blender is slow or laggy · I want to save or recover my work · Moving or scaling goes the wrong way · It rotates or scales around a strange point · My modifier does nothing · Extrude, loop cut or bevel does nothing · My render is black or empty*

- **Likely causes come first.** Causes that match your live scene are marked and listed on top; the rest follow, with a "+N more tips" expander.
- **One-click fixes.** Add a cube, show hidden objects, frame everything, return to Object Mode, switch to solid view, select all, recalculate normals, toggle Edit Mode, or undo.

### Page 3: Tools (find any tool)

Do not remember where a tool lives? Type what you want in plain words ("make a hole", "extrude", "mirror", "snap", "light") and the Tools page shows, for each match:

- **where** to find it in Blender's menus,
- **what it does**, in plain language,
- the **keyboard shortcut**,
- a **mode warning** (with **Switch mode for me**) if you are in the wrong mode.

The library has **70 tools**, from basics (add, move, rotate, scale, undo) to modelling (extrude, inset, bevel, loop cut, knife, bridge, proportional editing), modifiers (Boolean, Mirror, Array, Solidify, Subdivision), scene setup (lights, cameras, keyframes, snapping, 3D cursor, pivot point) and file handling. With an empty search box, a **Popular** list is shown.

### Learn a task (second panel in the Nav Guide tab)

A lighter, in-sidebar alternative to the full lessons: pick one of **7 short tasks** (look around, add and delete, move/rotate/scale, edit a shape, extrude, add colour, build a simple wall) and step through it with **Back** and **Next**. Each step shows the shortcut and, where useful, a **Do it for me** button.

---

## How the tabs work together

- **Start in Tutorial** to learn the basics in order, in Keyboard or Accessible mode.
- **Use Accessibility** to remove any input barrier. Your custom shortcuts and buttons work in the tutorial, the Nav Guide and normal Blender, and the task card shows your own keys.
- **Use Nav Guide** when you are working on your own project and need a next step, a fix, or a tool.

---

## Your data and settings

The add-on stores two small files in your Blender extension user folder:

| File | Contents |
|---|---|
| `progress.json` | Which lessons you have completed, the task you reached in each, and your chosen mode |
| `accessibility.json` | Whether shortcuts are on, your shortcuts, and your own commands |

No account or internet connection is needed, and nothing leaves your computer.

---

## Build the zip

```bash
cd navigation_guide
zip -r ../navigation_guide.zip .
```

The manifest (`blender_manifest.toml`) **must be at the root of the zip**. If you are working from this repository, where the add-on files already sit at the top level, run `zip -r navigation_guide.zip . -x ".git/*"` from the repository root instead.

## Project structure

```
navigation_guide/
├── blender_manifest.toml     Extension metadata (id, version, Blender 4.2+, MIT)
├── __init__.py               Registers the four modules below
│
├── panel.py                  Sidebar for the Tutorial and Accessibility tabs
├── lesson.py                 Lesson engine: modes, task card, overlay, progress, layout
├── detect.py                 Detectors that check whether each task is done
├── commands.py               One-click command list for Accessible mode (72 commands)
├── actions.py                "Do it for me" helper actions
├── access.py                 Accessibility: commands, custom shortcuts, shortcut listener
├── lessons/lessons.json      The 20 lessons and their tasks
├── media/                    Hint animations (sprite sheets) and meta.json
│
└── guide/                    The Nav Guide tab
    ├── __init__.py
    ├── context.py            Reads live Blender state and produces hints
    ├── navigator.py          Goal logic: matching, "done" checks, mode warnings
    ├── finder.py             Tool search
    ├── troubleshoot.py       "I'm stuck" troubleshooter logic
    ├── session.py            Timer that watches Blender and advances steps
    ├── overlay.py            Banner and animations in the 3D viewport
    ├── goal_ops.py           Start / skip / stop a goal
    ├── operators.py          Helper actions and step navigation
    ├── props.py              Remembers chosen goal, page, task and step
    ├── panel_nav.py          Guide / Help / Tools sidebar
    ├── panel_tutorial.py     "Learn a task" sidebar panel
    ├── tasks.py              Loader for tasks.json
    ├── utils.py              Shared UI helpers
    ├── recipes/recipes.json  The 20 guided goals
    ├── tools/tools.json      The 70 find-a-tool entries
    ├── problems/problems.json  The 18 troubleshooter problems
    └── tasks/tasks.json      The 7 short "Learn a task" tasks
```

## Adding your own content

Most of the teaching content lives in JSON files, so you can extend the add-on **without writing code**:

- **New lesson or task:** edit `lessons/lessons.json` (each task names a detector from `detect.py` and the commands that complete it).
- **New guided goal:** edit `guide/recipes/recipes.json` (each step can have a `done` condition, a mode, a shortcut and an optional action).
- **New tool entry:** edit `guide/tools/tools.json`.
- **New "I'm stuck" problem:** edit `guide/problems/problems.json` (causes can carry a `when` condition and a one-click `fix`).

---

## Roadmap

- [x] Sidebar panels and live context detection
- [x] 20-lesson tutorial with automatic task detection and saved progress
- [x] Keyboard mode and Accessible mode
- [x] Custom shortcuts (hold / tap sequences, keys and mouse buttons) and custom commands
- [x] Goal-based guidance with in-viewport animated hints
- [x] "I'm stuck" troubleshooter with one-click fixes
- [x] Find-a-tool search
- [ ] User testing with beginners and users of assistive devices
- [ ] More lessons and goals (sculpting, UV unwrapping, geometry nodes)
- [ ] Review every Find-a-tool entry against the latest Blender release

## Team

**Kernel-Panic**, built for the Devlup Labs hackathon.

| Name | Role |
|---|---|
|Manav | Team Lead - Contributer (tutorials) |
|Raghya | Contributer (nav guide) |
|Avadhoot |
|Shashank | 

## License

MIT
