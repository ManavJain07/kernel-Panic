"""Generates the hint animations.

For every animation this writes
  docs/gifs/<name>.gif                         a normal GIF (README, sharing)
  navigation_guide/media/<name>.png            the same frames as one sprite sheet
                                               (Blender cannot play GIFs, so the
                                               add-on plays the sheet instead)
and navigation_guide/media/meta.json (frame counts, used by the add-on).
To give a lesson task a Hint button, add  "gif": "<name>"  to the task in
lessons.json.

Run from the repo root:  python scripts/make_hint_gifs.py      (needs Pillow)
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
GIF_DIR = ROOT / "docs" / "gifs"
SHEET_DIR = ROOT / "navigation_guide" / "media"
W, H = 360, 270          # final frame size
SS = 2                   # supersampling for smooth edges
FRAMES = 30
COLS = 6
FPS = 20

BG = (30, 30, 34)
PANEL = (52, 52, 58)
GRID = (66, 66, 72)
MOUSE = (74, 74, 82)
MOUSE_EDGE = (170, 170, 178)
ORANGE = (255, 150, 40)
BLUE = (70, 140, 255)
WHITE = (240, 240, 240)
GREY = (150, 150, 158)

_FD = "/usr/share/fonts/truetype/dejavu/"


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(_FD + name, int(size * SS))


def S(v):
    return int(round(v * SS))


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)


# ------------------------------------------------------------------ cube ---
def cube_faces(yaw, pitch, cx, cy, size, dist=6.0):
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    def rot(v):
        x, y, z = v
        x, z = x * cy_ + z * sy_, -x * sy_ + z * cy_      # yaw
        y, z = y * cp - z * sp, y * sp + z * cp           # pitch
        return x, y, z

    def proj(v):
        x, y, z = rot(v)
        f = size / (z + dist)
        return (cx + x * f * dist * 0.5, cy - y * f * dist * 0.5), z

    # (outward normal, four corners)
    faces = [
        ((0, 0, -1), [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)]),
        ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
        ((-1, 0, 0), [(-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)]),
        ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
        ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
        ((0, 1, 0), [(-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)]),
    ]
    out = []
    for normal, corners in faces:
        nx, ny, nz = rot(normal)
        if nz >= 0:            # pointing away from the camera: hidden
            continue
        pr = [proj(c) for c in corners]
        depth = sum(z for _p, z in pr) / 4
        light = 0.55 + 0.25 * (-nz) + 0.25 * max(ny, 0)
        out.append((depth, light, [p for p, _z in pr]))
    return out


def draw_cube(d, yaw, pitch, cx, cy, size, selected=True):
    faces = cube_faces(yaw, pitch, cx, cy, size)
    faces.sort(key=lambda f: -f[0])
    for depth, facing, poly in faces:
        shade = int(min(1.0, facing) * 150 + 30)
        d.polygon([(S(x), S(y)) for x, y in poly], fill=(shade, shade, shade + 4),
                  outline=ORANGE if selected else (25, 25, 28), width=S(2))


# ----------------------------------------------------------------- mouse ---
def draw_mouse(d, cx, cy, left=False, middle=False, right=False):
    w, h = 62, 92
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    d.rounded_rectangle([S(x0), S(y0), S(x1), S(y1)], radius=S(28), fill=MOUSE,
                        outline=MOUSE_EDGE, width=S(2))
    split = y0 + h * 0.42
    if left:
        d.pieslice([S(x0), S(y0), S(x1), S(y0 + 56)], 180, 270, fill=BLUE)
        d.rectangle([S(x0 + 1), S(y0 + 28), S(cx - 1), S(split)], fill=BLUE)
    if right:
        d.pieslice([S(x0), S(y0), S(x1), S(y0 + 56)], 270, 360, fill=BLUE)
        d.rectangle([S(cx + 1), S(y0 + 28), S(x1 - 1), S(split)], fill=BLUE)
    d.rounded_rectangle([S(x0), S(y0), S(x1), S(y1)], radius=S(28), outline=MOUSE_EDGE,
                        width=S(2))
    d.line([S(x0 + 2), S(split), S(x1 - 2), S(split)], fill=MOUSE_EDGE, width=S(2))
    d.line([S(cx), S(y0 + 2), S(cx), S(split)], fill=MOUSE_EDGE, width=S(2))
    wheel = [S(cx - 5), S(y0 + 12), S(cx + 5), S(y0 + 34)]
    d.rounded_rectangle(wheel, radius=S(5), fill=ORANGE if middle else (110, 110, 118),
                        outline=MOUSE_EDGE, width=S(1))


def draw_arrow(d, x0, y0, x1, y1, color, width=3):
    d.line([S(x0), S(y0), S(x1), S(y1)], fill=color, width=S(width))
    ang = math.atan2(y1 - y0, x1 - x0)
    for da in (2.6, -2.6):
        d.line([S(x1), S(y1), S(x1 + 8 * math.cos(ang + da)), S(y1 + 8 * math.sin(ang + da))],
               fill=color, width=S(width))


def badge(d, x, y, text, active):
    w = 12 + len(text) * 8
    d.rounded_rectangle([S(x), S(y), S(x + w), S(y + 24)], radius=S(6),
                        fill=ORANGE if active else (70, 70, 78),
                        outline=MOUSE_EDGE, width=S(1))
    d.text((S(x + w / 2), S(y + 12)), text, font=font(12, True),
           fill=(20, 20, 20) if active else WHITE, anchor="mm")


# -------------------------------------------------------------- viewport ---
VP = (140, 62, 348, 258)   # viewport card, in final pixels


def new_scene(title, subtitle):
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    d.text((S(14), S(10)), title, font=font(20, True), fill=WHITE)
    d.text((S(14), S(38)), subtitle, font=font(11), fill=GREY)
    return img, d


def viewport_layer(draw_inside):
    """Draws the 3D-viewport card, with its content clipped to the card."""
    vw, vh = VP[2] - VP[0], VP[3] - VP[1]
    layer = Image.new("RGB", (vw * SS, vh * SS), PANEL)
    ld = ImageDraw.Draw(layer)
    for i in range(1, 8):  # fake ground grid
        y = S(vh * 0.55 + (i * i) * 2.2)
        ld.line([0, y, vw * SS, y], fill=GRID, width=S(1))
    for i in range(-6, 7):
        ld.line([S(vw / 2 + i * 6), S(vh * 0.55), S(vw / 2 + i * 30), vh * SS], fill=GRID,
                width=S(1))
    draw_inside(ld)
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, layer.size[0] - 1, layer.size[1] - 1],
                                           radius=S(10), fill=255)
    return layer, mask


def finish(img, frame_scene):
    return img.resize((W, H), Image.LANCZOS)


VW, VH = VP[2] - VP[0], VP[3] - VP[1]


def paste_vp(img, inside):
    layer, mask = viewport_layer(inside)
    img.paste(layer, (S(VP[0]), S(VP[1])), mask)
    ImageDraw.Draw(img).rounded_rectangle(
        [S(VP[0]), S(VP[1]), S(VP[2]), S(VP[3])], radius=S(10), outline=(95, 95, 104),
        width=S(2))


# ---------------------------------------------------------------- scenes ---
def orbit(i):
    t = i / FRAMES
    sw = math.sin(2 * math.pi * t)
    img, d = new_scene("Orbit", "Hold the middle mouse button and drag")
    draw_mouse(d, 70, 150, middle=True)
    # drag line with a moving dot
    d.line([S(25), S(222), S(115), S(222)], fill=(90, 90, 98), width=S(3))
    draw_arrow(d, 40, 222, 25, 222, GREY)
    draw_arrow(d, 100, 222, 115, 222, GREY)
    d.ellipse([S(70 + 38 * sw - 6), S(216), S(70 + 38 * sw + 6), S(228)], fill=ORANGE)
    paste_vp(img, lambda ld: _cube_in_vp(ld, 0.6 + 0.9 * sw, 0.45, VW / 2, VH / 2, 70))
    return finish(img, None)


def _cube_in_vp(ld, yaw, pitch, cx, cy, size, selected=True):
    draw_cube(ld, yaw, pitch, cx, cy, size, selected)


def pan(i):
    t = i / FRAMES
    sw = math.sin(2 * math.pi * t)
    img, d = new_scene("Pan", "Hold Shift + middle mouse button and drag")
    draw_mouse(d, 70, 150, middle=True)
    badge(d, 38, 212, "Shift", True)
    d.line([S(25), S(248), S(115), S(248)], fill=(90, 90, 98), width=S(3))
    d.ellipse([S(70 + 38 * sw - 6), S(242), S(70 + 38 * sw + 6), S(254)], fill=ORANGE)
    paste_vp(img, lambda ld: _cube_in_vp(ld, 0.7, 0.4, VW / 2 + 40 * sw, VH / 2 - 8 * sw, 62))
    return finish(img, None)


def zoom(i):
    t = i / FRAMES
    sw = math.sin(2 * math.pi * t)
    img, d = new_scene("Zoom", "Scroll the mouse wheel")
    draw_mouse(d, 70, 150, middle=True)
    up_active = sw > 0.15
    down_active = sw < -0.15
    draw_arrow(d, 118, 140, 118, 112, ORANGE if up_active else (90, 90, 98), 4)
    draw_arrow(d, 118, 160, 118, 188, ORANGE if down_active else (90, 90, 98), 4)
    d.text((S(70), S(222)), "scroll up = zoom in", font=font(10), fill=GREY, anchor="mm")
    d.text((S(70), S(238)), "scroll down = zoom out", font=font(10), fill=GREY, anchor="mm")
    paste_vp(img, lambda ld: _cube_in_vp(ld, 0.7, 0.4, VW / 2, VH / 2, 62 + 32 * sw))
    return finish(img, None)


def _cursor(d, x, y, press=False):
    pts = [(x, y), (x, y + 18), (x + 5, y + 14), (x + 9, y + 22), (x + 12, y + 20),
           (x + 8, y + 13), (x + 14, y + 13)]
    d.polygon([(S(px), S(py)) for px, py in pts], fill=(250, 250, 250), outline=(10, 10, 10))
    if press:
        d.ellipse([S(x - 10), S(y - 10), S(x + 10), S(y + 10)], outline=BLUE, width=S(3))


def select(i):
    n = FRAMES
    img, d = new_scene("Select", "Click empty space, then click the cube")
    phase = i / n
    # 0-0.5: go to empty space and click (cube deselects). 0.5-1: go to cube, click.
    empty = (VW * 0.18, VH * 0.2)
    cube_pt = (VW / 2 + 4, VH / 2 + 4)
    start = (VW * 0.45, VH * 0.9)
    if phase < 0.5:
        p = ease(min(phase / 0.3, 1))
        pos = (start[0] + (empty[0] - start[0]) * p, start[1] + (empty[1] - start[1]) * p)
        press = 0.3 <= phase < 0.42
        selected = phase < 0.35
    else:
        q = (phase - 0.5)
        p = ease(min(q / 0.3, 1))
        pos = (empty[0] + (cube_pt[0] - empty[0]) * p, empty[1] + (cube_pt[1] - empty[1]) * p)
        press = 0.8 <= phase < 0.92
        selected = phase >= 0.83
    draw_mouse(d, 70, 150, left=press)
    label = "click empty space" if phase < 0.5 else "click the cube"
    d.text((S(70), S(222)), label, font=font(11, True), fill=ORANGE if press else GREY,
           anchor="mm")

    def inside(ld):
        _cube_in_vp(ld, 0.7, 0.4, VW / 2, VH / 2, 66, selected)
        _cursor(ld, pos[0], pos[1], press)

    paste_vp(img, inside)
    return finish(img, None)



# ------------------------------------------------------- keyboard hints ---
# A keyboard hint shows a sequence of "groups". A group is a chord of keys that
# are pressed together (["Shift", "A"]); groups are pressed one after another.
# Special tokens:  "@hover" = move the mouse around,  "@click" = a mouse click,
# "@Mesh" = a menu item to click.
KEY_FRAMES_PER = 14          # frames each group takes
GREEN = (80, 200, 110)
_measure = ImageDraw.Draw(Image.new("RGB", (4, 4)))

KEYANIMS = {
    "key_m": dict(size=(240, 130), cap=84, seq=[["M"]]),
    "shift_a": dict(title="Open the Add menu",
                    sub="Mouse over the viewport, then press",
                    seq=[["Shift", "A"]]),
    "add_cube": dict(title="Add a cube", sub="Shift + A, then Mesh, then Cube",
                     seq=[["Shift", "A"], ["@Mesh"], ["@Cube"]]),
    "delete": dict(title="Delete the object", sub="Select it, then press Delete",
                   caption=["X also works, but asks you to confirm"],
                   seq=[["Delete"]]),
    "g": dict(title="Grab (move)", sub="Press G, move the mouse, then click",
              caption=["Click to confirm  -  Esc cancels"],
              seq=[["G"], ["@hover"], ["@click"]]),
    "g_axis": dict(title="Move one way only", sub="Press G, then X, Y or Z, then click",
                   caption=["Type a number and press Enter for an exact distance"],
                   seq=[["G"], ["X"], ["@hover"], ["@click"]]),
    "r": dict(title="Rotate", sub="Press R, move the mouse, then click",
              caption=["Click to confirm  -  Esc cancels"],
              seq=[["R"], ["@hover"], ["@click"]]),
    "s": dict(title="Scale", sub="Press S, move the mouse, then click",
              caption=["Click to confirm  -  Esc cancels"],
              seq=[["S"], ["@hover"], ["@click"]]),
    "undo": dict(title="Undo", sub="Mouse over the viewport, then press",
                 caption=["Windows / Linux"], seq=[["Ctrl", "Z"]]),
    "undo_mac": dict(title="Undo", sub="Mouse over the viewport, then press",
                     caption=["Mac"], seq=[["Cmd", "Z"]]),
    "tab": dict(title="Switch mode", sub="Tab goes between Object Mode and Edit Mode",
                seq=[["Tab"]]),
    "keys_123": dict(title="What to select", sub="Press each key in Edit Mode",
                     caption=["1 = vertices     2 = edges     3 = faces"],
                     seq=[["1"], ["2"], ["3"]]),
    "one_face": dict(title="Select one face", sub="Press 3, then click one face",
                     seq=[["3"], ["@click"]]),
    "face_move": dict(title="Move a face", sub="3, click a face, G, move, click",
                      seq=[["3"], ["@click"], ["G"], ["@hover"], ["@click"]]),
    "e": dict(title="Extrude", sub="Press E, pull the mouse out, then click",
              caption=["Click to confirm  -  Esc cancels"],
              seq=[["E"], ["@hover"], ["@click"]]),
    "wall_len": dict(title="Make it long", sub="Press S, X, type 4, then Enter",
                     seq=[["S"], ["X"], ["4"], ["Enter"]]),
    "wall_thin": dict(title="Make it thin", sub="Press S, Y, type 0.2, then Enter",
                      seq=[["S"], ["Y"], ["0.2"], ["Enter"]]),
    "wall_tall": dict(title="Make it taller", sub="Press S, Z, type 1.5, then Enter",
                      seq=[["S"], ["Z"], ["1.5"], ["Enter"]]),
    "wall_lift": dict(title="Lift it up", sub="Press G, Z, type 1.5, then Enter",
                      seq=[["G"], ["Z"], ["1.5"], ["Enter"]]),
}


def key_frames(spec):
    return KEY_FRAMES_PER * len(spec["seq"]) + 10


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _tw(text, size, bold=True):
    return _measure.textlength(text, font=font(size, bold)) / SS


def key_scene(spec, i):
    w, h = spec.get("size", (W, H))
    img = Image.new("RGB", (w * SS, h * SS), BG)
    d = ImageDraw.Draw(img)
    if spec.get("title"):
        d.text((S(14), S(10)), spec["title"], font=font(20, True), fill=WHITE)
        d.text((S(14), S(38)), spec.get("sub", ""), font=font(11), fill=GREY)
    seq = spec["seq"]

    # which group is being pressed right now, and how far down
    t = i - 4
    active, press, settled, local = -1, 0.0, False, 0
    if t >= 0:
        active, local = t // KEY_FRAMES_PER, t % KEY_FRAMES_PER
        if active >= len(seq):
            active, settled = len(seq), True
        else:
            press = ease(min(local / 3, 1)) if local < 8 else ease(max(1 - (local - 8) / 3, 0))
            settled = local >= 10

    cap = spec.get("cap", 56)
    fs = cap * 0.36

    def item_size(tok):
        if tok == "@hover":
            return cap * 1.25, cap * 0.95
        if tok == "@click":
            return cap * 0.62, cap * 0.95
        if tok.startswith("@"):
            return _tw(tok[1:], fs * 0.9) + cap * 0.6, cap * 0.7
        return max(cap, _tw(tok, fs) + cap * 0.5), cap

    plus_w, arrow_w = cap * 0.4, cap * 0.5
    total = 0
    for gi, group in enumerate(seq):
        for ti, tok in enumerate(group):
            total += item_size(tok)[0] + (plus_w if ti else 0)
        total += arrow_w if gi else 0
    sc = min(1.0, (w - 24) / total)
    cy = h * (0.5 if not spec.get("title") else 0.53)
    x = (w - total * sc) / 2

    for gi, group in enumerate(seq):
        if gi:
            d.text((S(x + arrow_w * sc / 2), S(cy)), "\u203a", font=font(cap * 0.6 * sc, True),
                   fill=GREY, anchor="mm")
            x += arrow_w * sc
        if gi < active or (gi == active and settled):
            state, p = "done", 0.0
        elif gi == active:
            state, p = "active", press
        else:
            state, p = "future", 0.0
        for ti, tok in enumerate(group):
            if ti:
                d.text((S(x + plus_w * sc / 2), S(cy)), "+", font=font(cap * 0.5 * sc, True),
                       fill=GREY, anchor="mm")
                x += plus_w * sc
            iw, ih = item_size(tok)
            iw, ih = iw * sc, ih * sc
            off = 5 * sc * p
            top = cy - ih / 2
            edge = {"done": GREEN, "active": ORANGE, "future": MOUSE_EDGE}[state]
            face = _mix((74, 74, 82), ORANGE, p) if state != "done" else (62, 78, 66)
            txt = (20, 20, 20) if p > 0.5 else WHITE
            if tok in ("@click", "@hover"):
                mw = cap * 0.62 * sc
                mx = x + (iw - mw) / 2
                if tok == "@hover" and state == "active":
                    mx += math.sin(local / KEY_FRAMES_PER * 2 * math.pi * 1.5) * cap * 0.22 * sc
                if tok == "@hover":
                    for side in (-1, 1):           # little arrows: "move around"
                        ax = x + iw / 2 + side * (mw / 2 + cap * 0.3 * sc)
                        col = ORANGE if state == "active" else (GREEN if state == "done" else GREY)
                        d.polygon([(S(ax), S(cy)),
                                   (S(ax - side * cap * 0.14 * sc), S(cy - cap * 0.12 * sc)),
                                   (S(ax - side * cap * 0.14 * sc), S(cy + cap * 0.12 * sc))], fill=col)
                body = [S(mx), S(top + off), S(mx + mw), S(top + ih + off)]
                d.rounded_rectangle(body, radius=S(mw * 0.45), fill=MOUSE, outline=edge, width=S(2))
                if tok == "@click" and state == "active":
                    d.pieslice([S(mx), S(top + off), S(mx + mw), S(top + off + mw)], 180, 270,
                               fill=_mix(MOUSE, BLUE, p))
                    d.rectangle([S(mx + 2), S(top + off + mw * 0.45), S(mx + mw / 2 - 1),
                                 S(top + off + ih * 0.42)], fill=_mix(MOUSE, BLUE, p))
                    d.rounded_rectangle(body, radius=S(mw * 0.45), outline=edge, width=S(2))
                d.line([S(mx + 2), S(top + off + ih * 0.42), S(mx + mw - 2), S(top + off + ih * 0.42)],
                       fill=edge, width=S(2))
                d.line([S(mx + mw / 2), S(top + off + 2), S(mx + mw / 2), S(top + off + ih * 0.42)],
                       fill=edge, width=S(2))
            else:
                # key base (the thick edge), then the face that moves down
                d.rounded_rectangle([S(x), S(top + 5 * sc), S(x + iw), S(top + ih)],
                                    radius=S(10 * sc), fill=(22, 22, 26), outline=edge, width=S(2))
                d.rounded_rectangle([S(x), S(top + off), S(x + iw), S(top + ih - 6 * sc + off)],
                                    radius=S(10 * sc), fill=face, outline=edge, width=S(2))
                label = tok[1:] if tok.startswith("@") else tok
                size = fs * sc * (0.9 if tok.startswith("@") else 1)
                d.text((S(x + iw / 2), S(top + (ih - 6 * sc) / 2 + off)), label,
                       font=font(size, True), fill=txt, anchor="mm")
            if state == "active" and p > 0.2:     # ripple around the pressed key
                r = (1 - p) * 10 * sc + 4
                d.rounded_rectangle([S(x - r), S(top - r), S(x + iw + r), S(top + ih + r)],
                                    radius=S(12 * sc + r), outline=_mix(BG, ORANGE, p), width=S(2))
            x += iw
    for n, line in enumerate(spec.get("caption", ())):
        d.text((S(w / 2), S(h - 30 + n * 16)), line, font=font(11), fill=GREY, anchor="mm")
    return img.resize((w, h), Image.LANCZOS)


ANIMS = {"orbit": orbit, "pan": pan, "zoom": zoom, "select": select}


def _write(name, frames, w, h, meta):
    cols = COLS
    rows = math.ceil(len(frames) / cols)
    frames[0].save(GIF_DIR / f"{name}.gif", save_all=True, append_images=frames[1:],
                   duration=int(1000 / FPS), loop=0, optimize=True)
    sheet = Image.new("RGB", (w * cols, h * rows), BG)
    for i, fr in enumerate(frames):
        sheet.paste(fr, ((i % cols) * w, (i // cols) * h))
    sheet.save(SHEET_DIR / f"{name}.png", optimize=True)
    meta[name] = {"frames": len(frames), "cols": cols, "rows": rows, "w": w, "h": h, "fps": FPS}
    print(f"{name}: {len(frames)} frames, sheet {cols}x{rows}, cell {w}x{h}, {FPS} fps")


def main():
    GIF_DIR.mkdir(parents=True, exist_ok=True)
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, fn in ANIMS.items():
        _write(name, [fn(i) for i in range(FRAMES)], W, H, meta)
    for name, spec in KEYANIMS.items():
        w, h = spec.get("size", (W, H))
        _write(name, [key_scene(spec, i) for i in range(key_frames(spec))], w, h, meta)
    (SHEET_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
