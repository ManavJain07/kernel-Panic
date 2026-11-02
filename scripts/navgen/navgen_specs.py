"""The hint animations. Each one: name, title, subtitle, keys and a scene(t, f).

keys:  "A"  one key      "Shift+D"  keys together      "MOUSE"  move + click
       "CLICK" / "RCLICK"  a click   (list = one after the other)
scene(t, f): t = 0..1 progress of the effect, f = frame number.
"""
import math

from navgen_engine import Cam, GREYC, lerp, lerp3, ob, sm

RED = (0.82, 0.24, 0.2)
BLUEC = (0.25, 0.45, 0.85)
GREENC = (0.45, 0.62, 0.4)
CREAM = (0.93, 0.86, 0.7)
YELLOW = (255, 220, 60)


def sc(objs, cam=None, **kw):
    d = dict(cam=cam or Cam(), objs=objs)
    d.update(kw)
    return d


def pop(t, a=0.35, b=0.75):
    """0..1 appear animation between a and b."""
    return sm((t - a) / (b - a))


# ----------------------------------------------------------- lesson 8 ------
def dup(t, f):
    bx, by = lerp(-1.4, 1.4, t), lerp(0, 0.9, t)
    return sc([ob("cube", (-1.4, 0, 0), sel=t < 0.05),
               ob("cube", (bx, by, 0), sel=True, vis=t > 0.03)],
              cursor=(bx, by, 0.5), banner="Shift + D = copy, then move")


def shift_click(t, f):
    k = sm(t * 1.6)
    return sc([ob("cube", (-1.4, 0, 0), sel=True), ob("cube", (1.4, 0, 0), sel=t > 0.65)],
              cursor=(lerp(-0.2, 1.4, k), lerp(-2.4, 0, k), 0.5), banner="Shift + click adds to the selection")


def sel_all(t, f):
    s = t > 0.5
    return sc([ob("cube", (-1.9, 0, 0), sel=s), ob("sphere", (0, 0, 0), sel=s, smooth=True, detail=(12, 8)),
               ob("cone", (1.9, 0, 0), sel=s)], banner="A = select everything")


def desel_all(t, f):
    s = t < 0.5
    return sc([ob("cube", (-1.9, 0, 0), sel=s), ob("sphere", (0, 0, 0), sel=s, smooth=True, detail=(12, 8)),
               ob("cone", (1.9, 0, 0), sel=s)], banner="Alt + A = select nothing")


# ----------------------------------------------------------- lesson 9 ------
def _house_objs():
    return [ob("cube", (0, 0, 0), sel=True), ob("cone", (0, 0, 1.0), scale=(1.1, 1.1, 1.0), color=RED),
            ob("sphere", (2.0, -0.5, 0), color=BLUEC, smooth=True, detail=(12, 8))]


def view_front(t, f):
    return sc(_house_objs(), Cam(lerp(-45, 0, t), lerp(30, 0, t)), banner="Front view")


def view_top(t, f):
    return sc(_house_objs(), Cam(lerp(-45, 0, t), lerp(30, 90, t)), banner="Top view")


def view_persp(t, f):
    objs = [ob("cube", (0, y, 0), sel=(y == -3)) for y in (-3, -1, 1, 3)]
    return sc(objs, Cam(-30, 22, t), banner="Perspective" if t > 0.5 else "Orthographic")


def view_frame(t, f):
    objs = [ob("cube", (2.5, 1.5, 0), sel=True), ob("cube", (-2.2, -1, 0)), ob("cube", (0, 2.6, 0)),
            ob("sphere", (-3, 2, 0), color=BLUEC, smooth=True), ob("cone", (3.2, -2, 0), color=RED)]
    ctr = tuple(lerp(a, b, t) for a, b in zip((0, 0, 0), (2.5, 1.5, 0)))
    return sc(objs, Cam(-45, 30, 0, lerp(0.75, 1.9, t), ctr), banner="Frame selected = zoom to it")


# ----------------------------------------------------------- lesson 10 -----
def _added(kind, menu, **kw):
    def scene(t, f):
        s = pop(t)
        extra = dict(kw)
        scale = extra.pop("scale", 1.0)
        sc_ = tuple(v * s for v in scale) if isinstance(scale, tuple) else scale * s
        return sc([ob("cube", (-2.4, 0, 0)), ob(kind, (0.4, 0, 0), scale=max(sc_, 0.001) if not isinstance(sc_, tuple) else sc_,
                                               sel=True, vis=s > 0.02, **extra)],
                  banner=menu)
    return scene


add_sphere = _added("sphere", "Add > Mesh > UV Sphere", smooth=True, detail=(12, 8), scale=1.6)
add_cylinder = _added("cylinder", "Add > Mesh > Cylinder", scale=1.1)
add_plane = _added("plane", "Add > Mesh > Plane", scale=1.1)
add_monkey = _added("monkey", "Add > Mesh > Monkey", smooth=True, detail=(12, 8), scale=1.7, rz=0.2)


# ----------------------------------------------------------- lesson 11 -----
def _pair(**kw):
    return [ob("cube", (-1.4, 0, 0), sel=True, **kw), ob("sphere", (1.4, 0, 0), smooth=True, detail=(12, 8), **kw)]


def shade_wire(t, f):
    on = t > 0.5
    return sc([dict(o, wire=on) for o in _pair()], banner="Wireframe" if on else "Solid")


def shade_solid(t, f):
    on = t < 0.5
    return sc([dict(o, wire=on) for o in _pair()], banner="Solid" if not on else "Wireframe")


def xray(t, f):
    on = t > 0.5
    return sc([ob("sphere", (0, 0, 0), scale=0.8, color=BLUEC, smooth=True, detail=(12, 8)),
               ob("cube", (0, 0, 0), scale=1.6, xray=on, sel=True)],
              banner="X-ray: see through" if on else "Solid")


def shade_mat(t, f):
    k = sm(t * 1.4)
    return sc([ob("cube", (-1.4, 0, 0), color=lerp3(GREYC, RED, k), sel=True),
               ob("sphere", (1.4, 0, 0), color=lerp3(GREYC, BLUEC, k), smooth=True, detail=(12, 8))],
              banner="Material Preview: colours and light")


# ----------------------------------------------------------- lesson 12 -----
def rename(t, f):
    return sc([ob("cube", (0, 0, 0), sel=True, label="Cube" if t < 0.5 else "House")], banner="F2 = rename")


def hide(t, f):
    return sc([ob("cube", (-1.4, 0, 0)), ob("sphere", (1.4, 0, 0), sel=True, smooth=True, vis=t < 0.5)],
              banner="H = hide the selected object")


def unhide(t, f):
    return sc([ob("cube", (-1.4, 0, 0)), ob("sphere", (1.4, 0, 0), sel=True, smooth=True, vis=t > 0.5)],
              banner="Alt + H = show hidden objects")


def collection(t, f):
    objs = [ob("cube", (-1.6, 0, 0), sel=True), ob("sphere", (0, 0, 0), smooth=True), ob("cone", (1.6, 0, 0))]
    kw = {}
    if t > 0.5:
        r = [(-2.4, -1.0, -0.5), (2.4, -1.0, -0.5), (2.4, 1.0, -0.5), (-2.4, 1.0, -0.5), (-2.4, -1.0, -0.5)]
        kw = dict(lines=[(r, (250, 160, 60), 1.8)], ui=[("tag", ((0, -1.0, -0.5), "My Collection", (250, 200, 120)))])
    return sc(objs, banner="M > + New Collection", **kw)


# ----------------------------------------------------------- lesson 13 -----
def smooth(t, f):
    on = t > 0.5
    return sc([ob("sphere", (0, 0, 0), scale=1.7, sel=True, detail=(8, 6), smooth=on)],
              banner="Shade Smooth" if on else "Flat shading (blocky)")


def subsurf2(t, f):
    hi = t > 0.4
    return sc([ob("monkey", (0, 0, 0), scale=1.7, smooth=hi, detail=(11, 8) if hi else (6, 4), sel=True)],
              banner="Ctrl + 2 = Subdivision level 2")


def subsurf3(t, f):
    hi = t > 0.4
    return sc([ob("monkey", (0, 0, 0), scale=1.7, smooth=True, detail=(18, 12) if hi else (11, 8), sel=True)],
              banner="Ctrl + 3 = Subdivision level 3")


# ----------------------------------------------------------- lesson 14 -----
def _corners(s, z=None):
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                pts.append((sx * s, sy * s, sz * s))
    return pts


def loopcut(t, f):
    s = 0.8
    h = lerp(-0.55, 0.0, sm(min(1.0, t * 1.5)))
    ring = [(-s, -s, h), (s, -s, h), (s, s, h), (-s, s, h), (-s, -s, h)]
    dots = [(p, (235, 235, 235), 2.6) for p in _corners(s)]
    if t > 0.8:
        dots += [(p, ORANGE_DOT, 2.8) for p in ring[:4]]
    return sc([ob("cube", (0, 0, 0), scale=1.6)], lines=[(ring, YELLOW, 2.0)], dots=dots,
              banner="Ctrl + R, click, click = loop cut")


ORANGE_DOT = (255, 150, 40)


def inset(t, f):
    s = 0.8
    k = lerp(1.0, 0.55, t)
    top = [(-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)]
    inner = [(x * k, y * k, z) for x, y, z in top]
    dots = [(p, (235, 235, 235), 2.6) for p in _corners(s) if p[2] < 0]
    dots += [(p, ORANGE_DOT, 2.8) for p in top]
    if t > 0.1:
        dots += [(p, ORANGE_DOT, 2.8) for p in inner]
    lines = []
    if t > 0.1:
        lines = [(inner + [inner[0]], (250, 200, 120), 1.6)] + [([a, b], (250, 200, 120), 1.2) for a, b in zip(top, inner)]
    return sc([ob("cube", (0, 0, 0), scale=1.6)], polys=[(top, (255, 150, 40, 110))], lines=lines, dots=dots,
              banner="I = inset the face")


def bevel(t, f):
    return sc([ob("cube", (0, 0, 0), scale=1.7, bevel=lerp(0.0, 0.2, t))], banner="Ctrl + B = round the edges")


# ----------------------------------------------------------- lesson 15 -----
def metallic(t, f):
    return sc([ob("sphere", (-0.3, 0, 0), scale=1.9, smooth=True, detail=(16, 12), metal=t, hl=True, rough=0.25, sel=False)],
              ui=[("slider", ("Metallic", t))], banner="Properties > Material > Metallic")


def roughness(t, f):
    r = 1 - t
    return sc([ob("sphere", (-0.3, 0, 0), scale=1.9, smooth=True, detail=(16, 12), metal=0.9, hl=True, rough=r)],
              ui=[("slider", ("Roughness", r))], banner="Properties > Material > Roughness")


# ----------------------------------------------------------- lesson 16 -----
def join(t, f):
    d = lerp(1.35, 0.5, sm(min(1, t * 1.6)))
    return sc([ob("cube", (-d, 0, 0), sel=True), ob("cube", (d, 0, 0), sel=True)],
              ui=[("tag", ((0, 0, 1.2), "2 objects" if t < 0.6 else "1 object"))], banner="Ctrl + J = join")


def separate(t, f):
    d = lerp(0.5, 1.35, sm(min(1, t * 1.6)))
    return sc([ob("cube", (-d, 0, 0), sel=True), ob("cube", (d, 0, 0), sel=True)],
              ui=[("tag", ((0, 0, 1.2), "1 object" if t < 0.6 else "2 objects"))], banner="P > By Loose Parts")


# ----------------------------------------------------------- lesson 17 -----
def _text(label, **kw):
    d = ob("text", (0, 0, 0.3), scale=1.4, color=(0.9, 0.9, 0.92), sel=True)
    d["label"] = label
    d.update(kw)
    return d


def add_text(t, f):
    return sc([_text("Text", vis=t > 0.35)], banner="Add > Text")


def edit_text(t, f):
    words = ["Text", "Tex", "Te", "T", "H", "Hi", "Hi!"]
    w = words[min(len(words) - 1, int(t * len(words)))]
    if f % 6 < 3 and t < 0.95:
        w += "|"
    return sc([_text(w)], banner="Tab, type, Tab")


def text_extrude(t, f):
    return sc([_text("Hi!", extrude=t * 0.4)], ui=[("slider", ("Extrude", t * 0.4))], banner="Data tab > Geometry > Extrude")


# ----------------------------------------------------------- lesson 18 -----
def add_light(t, f):
    k = pop(t)
    return sc([ob("cube", (0, 0, 0), color=lerp3((0.45, 0.45, 0.48), GREYC, k)),
               dict(ob("light", (2.6, -1.6, 2.4), vis=k > 0.05, scale=1.0))],
              banner="Add > Light > Sun")


def cam_view(t, f):
    return sc([ob("cube", (0, 0, 0), sel=True)], Cam(-40, 28, 0.6, lerp(1.0, 1.35, t)), ui=[("frame", (t,))],
              banner="Numpad 0 = look through the camera")


def render(t, f):
    return sc([ob("cube", (0, 0, 0), sel=True)], ui=[("image", (t,))], banner="F12 = render a picture")


# ----------------------------------------------------------- lesson 19 -----
def keyframe(t, f):
    return sc([ob("cube", (-2.0, 0, 0), sel=True)], ui=[("timeline", (0.0, [0.0] if t > 0.4 else []))],
              banner="I = keyframe (frame 1)")


def frame_jump(t, f):
    return sc([ob("cube", (-2.0, 0, 0), sel=True)], ui=[("timeline", (lerp(0, 0.6, t), [0.0]))],
              banner="Go to frame 60")


def keyframe2(t, f):
    return sc([ob("cube", (lerp(-2.0, 2.0, sm(min(1, t * 1.5))), 0, 0), sel=True)],
              ui=[("timeline", (0.6, [0.0] + ([0.6] if t > 0.7 else [])))], banner="G = move, then I = keyframe")


def play(t, f):
    head = lerp(0.0, 0.6, t)
    return sc([ob("cube", (lerp(-2.0, 2.0, min(1.0, head / 0.6)), 0, 0), sel=True)],
              ui=[("timeline", (head, [0.0, 0.6]))], banner="Space = play")


# ----------------------------------------------------------- lesson 20 -----
def _floor(s=2.4):
    return ob("plane", (0, 0, -0.5), scale=(s, s, 1), color=GREENC)


def cap_floor(t, f):
    k = lerp(0.35, 2.4, sm(t))
    return sc([_floor(k) if t > 0.0 else _floor(0.35)], Cam(-45, 32, 0, 0.95), banner="Plane, then S 4 = big floor")


def cap_house(t, f):
    return sc([_floor(), ob("cube", (0, 0, lerp(-0.5, 0, sm(t))), sel=True)], Cam(-45, 32, 0, 0.95),
              banner="Cube, then G Z 1 = onto the floor")


def cap_roof(t, f):
    return sc([_floor(), ob("cube", (0, 0, 0)), ob("cone", (0, 0, lerp(-0.5, 1.0, sm(t))), scale=(1.15, 1.15, 1.0), sel=True)],
              Cam(-45, 32, 0, 0.95), banner="Cone, then G Z 3 = on the roof")


def cap_paint(t, f):
    a, b = sm(t * 2), sm(t * 2 - 1)
    return sc([_floor(), ob("cube", (0, 0, 0), color=lerp3(GREYC, CREAM, b)),
               ob("cone", (0, 0, 1.0), scale=(1.15, 1.15, 1.0), color=lerp3(GREYC, RED, a))],
              Cam(-45, 32, 0, 0.95), banner="Material > New > Base Color")


def _spec(name, title, sub, keys, scene, caption=None):
    return dict(name=name, title=title, sub=sub, keys=keys, scene=scene, caption=caption)


SPECS = [
    _spec("dup", "Duplicate", "Press Shift + D, move, then click", ["Shift+D", "MOUSE"], dup),
    _spec("shift_click", "Select more than one", "Hold Shift and click", ["Shift+CLICK"], shift_click),
    _spec("sel_all", "Select all", "Press A over the viewport", ["A"], sel_all),
    _spec("desel_all", "Select nothing", "Press Alt + A (Option + A on Mac)", ["Alt+A"], desel_all),
    _spec("view_front", "Front view", "Press Numpad 1", ["Num 1"], view_front, "No numpad? Use the View menu > Viewpoint"),
    _spec("view_top", "Top view", "Press Numpad 7", ["Num 7"], view_top, "No numpad? Use the View menu > Viewpoint"),
    _spec("view_persp", "Perspective or flat", "Press Numpad 5", ["Num 5"], view_persp, "No numpad? View > Perspective / Orthographic"),
    _spec("view_frame", "Zoom to the selection", "Press Numpad . (period)", ["Num ."], view_frame, "No numpad? View > Frame Selected"),
    _spec("add_sphere", "Add a sphere", "Shift + A, then Mesh > UV Sphere", ["Shift+A", "CLICK"], add_sphere),
    _spec("add_cylinder", "Add a cylinder", "Shift + A, then Mesh > Cylinder", ["Shift+A", "CLICK"], add_cylinder),
    _spec("add_plane", "Add a plane", "Shift + A, then Mesh > Plane", ["Shift+A", "CLICK"], add_plane),
    _spec("add_monkey", "Add the monkey", "Shift + A, then Mesh > Monkey", ["Shift+A", "CLICK"], add_monkey),
    _spec("shade_wire", "Wireframe", "Press Shift + Z", ["Shift+Z"], shade_wire),
    _spec("shade_solid", "Solid view", "Press Shift + Z again", ["Shift+Z"], shade_solid),
    _spec("xray", "X-ray", "Press Alt + Z (Option + Z on Mac)", ["Alt+Z"], xray),
    _spec("shade_mat", "Material Preview", "Press Z, then choose Material Preview", ["Z", "CLICK"], shade_mat),
    _spec("rename", "Rename", "Press F2, type a name, press Enter", ["F2"], rename),
    _spec("hide", "Hide", "Press H", ["H"], hide),
    _spec("unhide", "Show hidden objects", "Press Alt + H (Option + H on Mac)", ["Alt+H"], unhide),
    _spec("collection", "Collections", "Press M, then + New Collection", ["M", "CLICK"], collection),
    _spec("smooth", "Shade Smooth", "Right-click, then Shade Smooth", ["RCLICK", "CLICK"], smooth),
    _spec("subsurf2", "More detail", "Press Ctrl + 2", ["Ctrl+2"], subsurf2),
    _spec("subsurf3", "Even more detail", "Press Ctrl + 3", ["Ctrl+3"], subsurf3),
    _spec("loopcut", "Loop cut", "Ctrl + R, then click twice", ["Ctrl+R", "CLICK"], loopcut, "In Edit Mode"),
    _spec("inset", "Inset", "Select a face, press I, move, click", ["I", "MOUSE"], inset, "In Edit Mode"),
    _spec("bevel", "Bevel", "Select edges, Ctrl + B, move, click", ["Ctrl+B", "MOUSE"], bevel, "In Edit Mode"),
    _spec("metallic", "Metallic", "Drag the Metallic slider to 1", ["MOUSE"], metallic),
    _spec("roughness", "Roughness", "Drag Roughness down to 0.1", ["MOUSE"], roughness),
    _spec("join", "Join", "Select both objects, press Ctrl + J", ["Ctrl+J"], join),
    _spec("separate", "Separate", "Edit Mode, A, then P > By Loose Parts", ["P"], separate),
    _spec("add_text", "Add text", "Shift + A, then Text", ["Shift+A", "CLICK"], add_text),
    _spec("edit_text", "Change the words", "Tab, type your text, Tab", ["Tab", "abc", "Tab"], edit_text),
    _spec("text_extrude", "Make text 3D", "Data tab > Geometry > Extrude", ["MOUSE"], text_extrude),
    _spec("add_light", "Add a light", "Shift + A, then Light > Sun", ["Shift+A", "CLICK"], add_light),
    _spec("cam_view", "Camera view", "Press Numpad 0", ["Num 0"], cam_view, "No numpad? View > Cameras > Active Camera"),
    _spec("render", "Render a picture", "Press F12", ["F12"], render),
    _spec("keyframe", "Keyframe", "Press I to save the position", ["I"], keyframe),
    _spec("frame_jump", "Go to frame 60", "Click in the Timeline numbers", ["CLICK"], frame_jump),
    _spec("keyframe2", "Second keyframe", "Move it (G), then press I", ["G", "I"], keyframe2),
    _spec("play", "Play the animation", "Press Space over the viewport", ["Space"], play),
    _spec("cap_floor", "Make the floor", "Add a plane, press S, 4, Enter", ["S", "4", "Enter"], cap_floor),
    _spec("cap_house", "Build the house", "Add a cube, press G, Z, 1, Enter", ["G", "Z", "1"], cap_house),
    _spec("cap_roof", "Add the roof", "Add a cone, press G, Z, 3, Enter", ["G", "Z", "3"], cap_roof),
    _spec("cap_paint", "Paint it", "Material tab > New > Base Color", ["CLICK"], cap_paint),
]
