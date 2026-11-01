# kernel-Panic: Blender Navigation Guide

The project is targeted at the ease of access and increasing the usability of the designing software BLENDER.<br>
The heavy load of cluttered tabs often overwhelm a beginner. So, our project aims at helping the user easily navigate through the tabs and commands.

> Built for the DevLups Labs hackathon. Problem statement: make digital
> experiences more accessible for people with limited technical literacy.

## Who it is for
First-time Blender users who feel lost in the interface.

## Features (v0.1)
- Shows current mode, active object and selection count
- Gives a plain-language hint and shortcut for the current situation
- One-click helper buttons (add cube, switch Edit/Object mode)

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
  operators.py            one-click helper buttons
  panel.py                sidebar UI
```

## Roadmap
- [x] Skeleton panel and context detection
- [ ] Task library (JSON) with step-by-step guides
- [ ] Step checklist UI
- [ ] More helper operators
- [ ] User testing with beginners

## Team
- Manav - Team lead - Contributer (tutorial)
- Raghya - Contributer (nav-guide)
- Avadhoot
- Shashank

## License
MIT
