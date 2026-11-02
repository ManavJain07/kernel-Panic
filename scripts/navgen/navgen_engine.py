"""Navigation Guide - hint animation maker.

Every hint animation is a sprite sheet (6 columns of 360x270 frames) plus an
entry in media/meta.json. A tiny 3D engine draws a mini viewport so each
animation shows the real effect: keys on top, the object changing below.

  python navgen.py <media_folder> [name ...]     (no names = make everything)

To add a new animation: add one entry to SPECS in navgen_specs.py (title,
subtitle, keys and a small scene function) and use its name as  "gif"  in
lessons.json.
"""
import json
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFont

SS = 2
FW, FH = 360, 270
N = 42                                   # frames per animation (20 fps = 2.1 s)
COLS = 6
BG = (30, 30, 34)


def _pick(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]


# First font found is used (Linux, macOS, Windows). Add your own path if needed.
BOLD = _pick(["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "C:/Windows/Fonts/arialbd.ttf"])
REG = _pick(["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/System/Library/Fonts/Supplemental/Arial.ttf",
             "C:/Windows/Fonts/arial.ttf"])
ORANGE, GREEN, BLUE = (255, 150, 40), (95, 200, 110), (70, 130, 230)
KEY_FILL, KEY_EDGE = (74, 74, 80), (190, 190, 196)
GREYTXT = (150, 150, 156)
VX, VY, VW, VH = 50, 118, 260, 114       # mini viewport rectangle
_fc = {}


def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, max(6, int(size * SS)))
    return _fc[k]


def sm(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def seg(f, a, b):
    return sm((f - a) / float(b - a)) if b > a else 1.0


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


class Canvas:
    def __init__(self, w=FW, h=FH, bg=BG):
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.im)

    def rr(self, x, y, w, h, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], r * SS,
                                 fill=fill, outline=outline, width=max(1, int(width * SS)))

    def text(self, x, y, s, path, size, fill, anchor="la"):
        self.d.text((x * SS, y * SS), s, font=font(path, size), fill=fill, anchor=anchor)

    def line(self, pts, fill, width=1):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=max(1, int(width * SS)))

    def poly(self, pts, fill, outline=None, width=1):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
        if outline:
            self.line(list(pts) + [pts[0]], outline, width)

    def circle(self, x, y, r, fill=None, outline=None, width=1):
        self.d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=fill,
                       outline=outline, width=max(1, int(width * SS)))

    def out(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


# =========================================================== key caps ======
def cap_width(label, sc=1.0):
    return max(34, len(label) * 8.4 + 20) * sc


def keycap(c, cx, cy, label, state, sc=1.0):
    w, h = cap_width(label, sc), 34 * sc
    x, y = cx - w / 2, cy - h / 2
    if state == "idle":
        fill, edge, tc = KEY_FILL, KEY_EDGE, (240, 240, 240)
    elif state == "press":
        fill, edge, tc = ORANGE, ORANGE, (20, 20, 20)
    elif state == "done":
        fill, edge, tc = (62, 80, 68), GREEN, (240, 240, 240)
    else:
        fill, edge, tc = (125, 95, 70), ORANGE, (240, 240, 240)
    if state in ("press", "glow"):
        c.rr(x - 5, y - 5, w + 10, h + 10, 11, outline=tuple(int(v * 0.55) for v in ORANGE), width=1.5)
    c.rr(x, y + 4, w, h, 7, fill=BG, outline=edge, width=1.5)
    c.rr(x, y, w, h, 7, fill=fill, outline=edge, width=1.5)
    c.text(cx, cy + 1, label, BOLD, 13 * sc, tc, "mm")


MOUSE_W = 26


def mouse(c, cx, cy, state, dx=0.0, button="L"):
    w, h = MOUSE_W, 40
    x, y = cx - w / 2 + dx, cy - h / 2
    edge = GREEN if state == "done" else (ORANGE if state in ("click", "glow") else KEY_EDGE)
    c.rr(x, y, w, h, 12, fill=KEY_FILL, outline=edge, width=1.5)
    if state == "click":
        box = [(x + 1.5) * SS, (y + 1.5) * SS, (x + w / 2 + 12) * SS, (y + 30) * SS]
        if button == "L":
            c.d.pieslice(box, 180, 270, fill=BLUE)
        else:
            box[0], box[2] = (x + w / 2 - 12) * SS, (x + w - 1.5) * SS
            c.d.pieslice(box, 270, 360, fill=BLUE)
    c.line([(x, y + 15), (x + w, y + 15)], edge, 1.3)
    c.line([(x + w / 2, y), (x + w / 2, y + 15)], edge, 1.3)


# =========================================================== 3D engine =====
LIGHT = (-0.40, -0.50, 0.80)
_ln = math.sqrt(sum(v * v for v in LIGHT))
LIGHT = tuple(v / _ln for v in LIGHT)
GREYC = (0.64, 0.64, 0.68)


def _norm(v):
    n = math.sqrt(sum(a * a for a in v)) or 1.0
    return tuple(a / n for a in v)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


class Cam:
    """Orthographic / perspective camera looking at a point."""

    def __init__(self, az=-45.0, el=30.0, persp=0.0, zoom=1.0, center=(0, 0, 0)):
        self.az, self.el, self.persp, self.zoom, self.center = az, el, persp, zoom, center
        a, e = math.radians(az), math.radians(el)
        self.eye = (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))
        self.fwd = tuple(-v for v in self.eye)
        self.right = (math.cos(a), math.sin(a), 0.0)
        self.up = _cross(self.right, self.fwd)
        self.U = 29.0 * zoom

    def depth(self, p):
        return _dot(_sub(p, self.center), self.fwd)

    def proj(self, p):
        q = _sub(p, self.center)
        x, y = _dot(q, self.right), _dot(q, self.up)
        k = 1.0
        if self.persp > 0:
            dz = _dot(q, self.fwd)
            k = 1 + self.persp * (10.0 / max(2.5, 10.0 + dz) - 1)
        return (VW / 2 + x * self.U * k, VH * 0.56 - y * self.U * k)


# ---- meshes: a face is (points, centre, tint) ------------------------------
def _face(pts, centre, tint=None):
    return (pts, centre, tint)


def m_cube(s=0.5):
    V = [(-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s), (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)]
    idx = ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1))
    return [_face([V[i] for i in f], (0, 0, 0)) for f in idx]


def m_bevel(b, s=0.5):
    """Cube with chamfered edges (Blender bevel, 1 segment)."""
    def p(v, keep):
        return tuple(v[i] if i == keep else math.copysign(s - b, v[i]) for i in range(3))
    verts = [(sx * s, sy * s, sz * s) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    faces = []
    for a in range(3):
        for sign in (-1, 1):
            q = [v for v in verts if v[a] == sign * s]
            q.sort(key=lambda v: math.atan2(v[(a + 2) % 3], v[(a + 1) % 3]))
            faces.append(_face([p(v, a) for v in q], (0, 0, 0)))
    for a in range(3):
        for b_ in range(a + 1, 3):
            c = 3 - a - b_
            for sa in (-1, 1):
                for sb in (-1, 1):
                    v1 = [0, 0, 0]; v2 = [0, 0, 0]
                    v1[a] = v2[a] = sa * s; v1[b_] = v2[b_] = sb * s
                    v1[c], v2[c] = -s, s
                    faces.append(_face([p(v1, a), p(v1, b_), p(v2, b_), p(v2, a)], (0, 0, 0)))
    for v in verts:
        faces.append(_face([p(v, 0), p(v, 1), p(v, 2)], (0, 0, 0)))
    return faces


def m_sphere(seg=12, rings=8, r=0.5, scale=(1, 1, 1), off=(0, 0, 0), tint=None):
    def pt(i, j):
        phi = -math.pi / 2 + math.pi * i / rings
        th = 2 * math.pi * (j % seg) / seg
        return (off[0] + r * scale[0] * math.cos(phi) * math.cos(th),
                off[1] + r * scale[1] * math.cos(phi) * math.sin(th),
                off[2] + r * scale[2] * math.sin(phi))
    faces = []
    for i in range(rings):
        for j in range(seg):
            q = [pt(i, j), pt(i, j + 1), pt(i + 1, j + 1), pt(i + 1, j)]
            q = [q[0], q[1], q[2], q[3]]
            uniq = []
            for v in q:
                if not uniq or max(abs(v[k] - uniq[-1][k]) for k in range(3)) > 1e-9:
                    uniq.append(v)
            if len(uniq) >= 3:
                faces.append(_face(uniq, off, tint))
    return faces


def m_cyl(seg=14, h=1.0, r=0.5):
    top = [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), h / 2) for i in range(seg)]
    bot = [(x, y, -h / 2) for x, y, _z in top]
    faces = [_face(top, (0, 0, 0)), _face(bot[::-1], (0, 0, 0))]
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(_face([bot[i], bot[j], top[j], top[i]], (0, 0, 0)))
    return faces


def m_cone(seg=14, h=1.0, r=0.5):
    base = [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), -h / 2) for i in range(seg)]
    apex = (0, 0, h / 2)
    faces = [_face(base[::-1], (0, 0, 0))]
    for i in range(seg):
        faces.append(_face([base[i], base[(i + 1) % seg], apex], (0, 0, 0)))
    return faces


def m_plane(s=1.0):
    return [_face([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], (0, 0, -9))]


def m_torus(seg=16, ring=8, R=0.36, r=0.14):
    def pt(i, j):
        u, v = 2 * math.pi * i / seg, 2 * math.pi * j / ring
        return ((R + r * math.cos(v)) * math.cos(u), (R + r * math.cos(v)) * math.sin(u), r * math.sin(v))
    faces = []
    for i in range(seg):
        for j in range(ring):
            u, v = 2 * math.pi * (i + .5) / seg, 2 * math.pi * (j + .5) / ring
            c = (R * math.cos(u), R * math.sin(u), 0)
            faces.append(_face([pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)], c))
    return faces


def m_monkey(seg=12, rings=8):
    f = m_sphere(seg, rings, 0.5, (1, 0.9, 0.82))
    f += m_sphere(max(6, seg // 2), max(4, rings // 2), 0.17, (0.5, 1, 1), (0.52, 0.02, 0.1))
    f += m_sphere(max(6, seg // 2), max(4, rings // 2), 0.17, (0.5, 1, 1), (-0.52, 0.02, 0.1))
    f += m_sphere(max(6, seg // 2), max(4, rings // 2), 0.22, (1, 0.9, 0.8), (0, -0.40, -0.14))
    f += m_sphere(6, 4, 0.07, (1, 0.6, 1), (0.17, -0.40, 0.14), (0.1, 0.1, 0.12))
    f += m_sphere(6, 4, 0.07, (1, 0.6, 1), (-0.17, -0.40, 0.14), (0.1, 0.1, 0.12))
    return f


_mesh_cache = {}


def mesh_for(o):
    k = (o["kind"], o.get("detail"), round(o.get("bevel", 0), 3))
    if k not in _mesh_cache:
        det = o.get("detail") or (12, 8)
        kind = o["kind"]
        if kind == "cube":
            _mesh_cache[k] = m_bevel(o["bevel"]) if o.get("bevel", 0) > 0.001 else m_cube()
        elif kind == "sphere":
            _mesh_cache[k] = m_sphere(*det)
        elif kind == "cylinder":
            _mesh_cache[k] = m_cyl()
        elif kind == "cone":
            _mesh_cache[k] = m_cone()
        elif kind == "plane":
            _mesh_cache[k] = m_plane()
        elif kind == "torus":
            _mesh_cache[k] = m_torus()
        elif kind == "monkey":
            _mesh_cache[k] = m_monkey(*det)
    return _mesh_cache[k]


def ob(kind, pos=(0, 0, 0), scale=1.0, rz=0.0, color=GREYC, sel=False, detail=None, smooth=False,
       wire=False, xray=False, bevel=0.0, metal=0.0, rough=0.5, hl=False, label=None, vis=True):
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    return dict(kind=kind, pos=pos, scale=scale, rz=rz, color=color, sel=sel, detail=detail, smooth=smooth,
                wire=wire, xray=xray, bevel=bevel, metal=metal, rough=rough, hl=hl, label=label, vis=vis)


def xf(o, p):
    x, y, z = p[0] * o["scale"][0], p[1] * o["scale"][1], p[2] * o["scale"][2]
    c, s = math.cos(o["rz"]), math.sin(o["rz"])
    return (x * c - y * s + o["pos"][0], x * s + y * c + o["pos"][1], z + o["pos"][2])


def shade(col, n, o):
    d = max(0.0, _dot(n, LIGHT))
    k = 0.34 + 0.66 * d
    m = o["metal"]
    if m > 0:                                   # metal: dark body, bright reflections
        refl = 0.18 + 0.82 * max(0.0, min(1.0, n[2] * 0.5 + 0.5 + 0.35 * d))
        k = lerp(k, refl * 1.15, m)
        col = lerp3(col, (0.72, 0.74, 0.8), m * 0.7)
    return tuple(max(0, min(255, int(255 * c * k))) for c in col)


def _ekey(a, b):
    ra = tuple(round(v, 3) for v in a)
    rb = tuple(round(v, 3) for v in b)
    return (ra, rb) if ra <= rb else (rb, ra)


# ============================================================ viewport =====
def draw_grid(vp, cam):
    for i in range(-7, 8):
        vp.line([cam.proj((i, -7, -0.5)), cam.proj((i, 7, -0.5))], (76, 76, 82), 1)
        vp.line([cam.proj((-7, i, -0.5)), cam.proj((7, i, -0.5))], (76, 76, 82), 1)
    vp.line([cam.proj((-7, 0, -0.5)), cam.proj((7, 0, -0.5))], (176, 64, 64), 1.6)
    vp.line([cam.proj((0, -7, -0.5)), cam.proj((0, 7, -0.5))], (110, 168, 64), 1.6)


def _face_data(o, cam):
    """Transformed faces of one object: (depth, screen_polygon, colour, visible)."""
    faces = mesh_for(o)
    out = []
    for pts3, ctr, tint in faces:
        pts = [xf(o, p) for p in pts3]
        c = xf(o, ctr)
        cen = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
        n = [0.0, 0.0, 0.0]
        for i in range(1, len(pts) - 1):
            cr = _cross(_sub(pts[i], pts[0]), _sub(pts[i + 1], pts[0]))
            n = [n[k] + cr[k] for k in range(3)]
        n = _norm(n)
        if _dot(n, _sub(cen, c)) < 0:
            n = tuple(-v for v in n)
        sn = _norm(_sub(cen, c)) if o["smooth"] else n
        if o["kind"] == "plane":
            n = sn = (0, 0, 1)
        visible = o["kind"] == "plane" or _dot(n, cam.eye) > 0
        col = shade(tint if tint else o["color"], sn, o)
        out.append((cam.depth(cen), [cam.proj(p) for p in pts], col, visible))
    out.sort(key=lambda t: -t[0])
    return out


def draw_objects(vp, ov, cam, objs):
    """Objects far to near. Each: silhouette stroke first, then its faces."""
    live = [o for o in objs if o["vis"] and o["kind"] not in ("text", "light") and min(o["scale"]) > 0.001]
    live.sort(key=lambda o: -cam.depth(o["pos"]))
    for o in live:
        data = _face_data(o, cam)
        if o["wire"]:
            continue
        if o["xray"]:
            for _d, q, col, _v in data:
                ov.poly(q, col + (95,))
            continue
        sil = ORANGE if o["sel"] else (34, 34, 40)
        width = 3.4 if o["sel"] else 2.2
        for _d, q, col, visible in data:
            if visible:
                vp.poly(q, sil, sil, width)
        flat = o["kind"] in ("cube", "cylinder", "cone", "plane") or (o["detail"] is not None and o["detail"][0] <= 9 and not o["smooth"])
        for _d, q, col, visible in data:
            if visible:
                vp.poly(q, col, (46, 46, 52) if flat else None, 0.8)
    return live


def draw_edges(vp, cam, live):
    """Wireframe / X-ray: every edge."""
    for o in live:
        if not (o["wire"] or o["xray"]):
            continue
        col = (240, 160, 60) if o["sel"] else (190, 190, 198)
        seen = set()
        for pts3, _c, _t in mesh_for(o):
            for i in range(len(pts3)):
                k = _ekey(pts3[i], pts3[(i + 1) % len(pts3)])
                if k in seen:
                    continue
                seen.add(k)
                vp.line([cam.proj(xf(o, k[0])), cam.proj(xf(o, k[1]))], col, 1.0)


def draw_ui_text(vp, cam, o):
    if o["kind"] == "text":
        px, py = cam.proj(o["pos"])
        ex = o.get("extrude", 0)
        size = 30 * o["scale"][0]
        dx = cam.proj((o["pos"][0], o["pos"][1] + 0.05, o["pos"][2]))
        ox, oy = dx[0] - px, dx[1] - py
        n = max(1, int(ex * 22))
        for i in range(n, -1, -1):
            col = tuple(int(c * (0.45 + 0.55 * (1 - i / max(n, 1)))) for c in o["color"][:3]) if i else None
            if i:
                col = tuple(int(255 * c * (0.35 + 0.4 * (1 - i / n))) for c in o["color"])
            else:
                col = tuple(int(255 * c) for c in o["color"])
            vp.text(px + ox * i, py + oy * i, o["label"], BOLD, size, col, "mm")
        if o["sel"]:
            w = len(o["label"]) * size * 0.62
            vp.rr(px - w / 2 - 4, py - size * 0.75, w + 8, size * 1.5, 3, outline=ORANGE, width=1.6)
    elif o["kind"] == "light" and o["vis"]:
        px, py = cam.proj(o["pos"])
        r = 7 * o["scale"][0]
        for k in range(8):
            a = k * math.pi / 4
            vp.line([(px + math.cos(a) * (r + 3), py + math.sin(a) * (r + 3)),
                     (px + math.cos(a) * (r + 8), py + math.sin(a) * (r + 8))], (255, 220, 90), 1.6)
        vp.circle(px, py, r, (255, 235, 120), (255, 200, 60), 1.5)
        a = cam.proj((o["pos"][0] * .4, o["pos"][1] * .4, 0))
        vp.line([(px, py + r + 8), (a[0], a[1] - 4)], (255, 220, 90), 1)


def highlight(vp, cam, o):
    """Specular dot for shiny spheres."""
    if o["kind"] != "sphere" or not o["hl"]:
        return
    px, py = cam.proj(o["pos"])
    s = o["scale"][0] * cam.U * 0.5
    rough = o["rough"]
    r = 2 + 9 * rough
    a = int(255 * (1 - 0.7 * rough))
    d = Image.new("RGBA", (int(r * 4 * SS), int(r * 4 * SS)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(d)
    for k in range(6):
        rr = r * (1 - k / 6.0) * SS
        dd.ellipse([2 * r * SS - rr, 2 * r * SS - rr, 2 * r * SS + rr, 2 * r * SS + rr],
                   fill=(255, 255, 255, int(a * (k + 1) / 6.0)))
    vp.im.paste(d, (int((px - s * 0.35 - 2 * r) * SS), int((py - s * 0.4 - 2 * r) * SS)), d)


def banner(vp, text):
    w = len(text) * 5.1 + 14
    vp.rr(6, 6, w, 17, 4, fill=(30, 30, 34), outline=(95, 95, 104), width=1)
    vp.text(13, 14.5, text, REG, 8.5, (225, 225, 230), "lm")


def cursor(vp, x, y):
    pts = [(x, y), (x, y + 13), (x + 3.5, y + 10), (x + 6.5, y + 16), (x + 9, y + 15), (x + 6, y + 9), (x + 11, y + 9)]
    vp.poly(pts, (245, 245, 245), (20, 20, 20), 1)


def slider(vp, label, value):
    x, y, w = VW - 168, VH - 24, 160
    vp.rr(x, y, w, 17, 4, fill=(40, 40, 46), outline=(95, 95, 104), width=1)
    vp.rr(x + 1, y + 1, max(3, (w - 2) * value), 15, 3, fill=(70, 120, 200))
    vp.text(x + 8, y + 8.5, label, REG, 8.5, (240, 240, 240), "lm")
    vp.text(x + w - 8, y + 8.5, f"{value:.1f}", REG, 8.5, (240, 240, 240), "rm")


def timeline(vp, head, keys):
    y, h = VH - 20, 20
    vp.rr(0, y, VW, h, 0, fill=(42, 42, 48))
    for i in range(0, 11):
        x = 10 + (VW - 20) * i / 10
        vp.line([(x, y), (x, y + 5)], (110, 110, 116), 1)
    for k in keys:
        x = 10 + (VW - 20) * k
        vp.poly([(x, y + 6), (x + 4.5, y + 11), (x, y + 16), (x - 4.5, y + 11)], (255, 200, 60), (120, 90, 20), 1)
    x = 10 + (VW - 20) * head
    vp.line([(x, y), (x, y + h)], (70, 140, 240), 2)
    vp.rr(x - 9, y + 1, 18, 8, 2, fill=(70, 140, 240))


def tag(vp, cam, pos, text, col=(235, 235, 240)):
    px, py = cam.proj(pos)
    w = len(text) * 5.2 + 10
    vp.rr(px - w / 2, py - 8, w, 15, 3, fill=(28, 28, 32), outline=(95, 95, 104), width=1)
    vp.text(px, py - 0.5, text, REG, 8.5, col, "mm")


def render_scene(sc, t, f):
    """sc: dict(cam=Cam, objs=[...], lines=[], dots=[], polys=[], banner=, cursor=3D point, ui=[...])"""
    vp = Canvas(VW, VH, (58, 58, 62))
    ov = ImageDraw.Draw(Image.new("RGBA", (1, 1)))        # replaced below
    ovim = Image.new("RGBA", (VW * SS, VH * SS), (0, 0, 0, 0))
    ovd = ImageDraw.Draw(ovim)

    class OV:                                              # polygons with alpha
        @staticmethod
        def poly(q, rgba):
            ovd.polygon([(x * SS, y * SS) for x, y in q], fill=rgba)
    cam = sc["cam"]
    draw_grid(vp, cam)
    outlines = draw_objects(vp, OV, cam, sc["objs"])
    for pts, rgba in sc.get("polys", []):
        OV.poly([cam.proj(p) for p in pts], rgba)
    vp.im = Image.alpha_composite(vp.im.convert("RGBA"), ovim).convert("RGB")
    vp.d = ImageDraw.Draw(vp.im)
    draw_edges(vp, cam, outlines)
    for o in sc["objs"]:
        highlight(vp, cam, o)
        draw_ui_text(vp, cam, o)
        if o.get("label") and o["kind"] not in ("text", "light") and o["vis"]:
            tag(vp, cam, (o["pos"][0], o["pos"][1], o["pos"][2] + 0.95 * max(o["scale"])), o["label"])
    for pts, col, w in sc.get("lines", []):
        vp.line([cam.proj(p) for p in pts], col, w)
    for p, col, r in sc.get("dots", []):
        x, y = cam.proj(p)
        vp.circle(x, y, r, col, (20, 20, 20), 0.8)
    for kind, args in sc.get("ui", []):
        if kind == "slider":
            slider(vp, *args)
        elif kind == "timeline":
            timeline(vp, *args)
        elif kind == "frame":
            cam_frame(vp, *args)
        elif kind == "image":
            render_card(vp, *args)
        elif kind == "tag":
            tag(vp, cam, *args)
    if sc.get("cursor") is not None:
        x, y = cam.proj(sc["cursor"])
        cursor(vp, x + 2, y + 1)
    if sc.get("banner"):
        banner(vp, sc["banner"])
    return vp


def cam_frame(vp, amt):
    """Dark mask with a bright 16:9 frame, like looking through the camera."""
    if amt <= 0.01:
        return
    fw, fh = 168 * amt + 260 * (1 - amt), 94.5 * amt + 114 * (1 - amt)
    x, y = (VW - fw) / 2, (VH - fh) / 2 - 2
    a = int(150 * amt)
    mask = Image.new("RGBA", (VW * SS, VH * SS), (0, 0, 0, 0))
    md = ImageDraw.Draw(mask)
    for r in ((0, 0, VW, y), (0, y + fh, VW, VH), (0, y, x, y + fh), (x + fw, y, VW, y + fh)):
        x0, y0, x1, y1 = max(0, r[0]), max(0, r[1]), min(VW, r[2]), min(VH, r[3])
        if x1 > x0 and y1 > y0:
            md.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=(0, 0, 0, a))
    vp.im.paste(mask, (0, 0), mask)
    vp.d = ImageDraw.Draw(vp.im)
    vp.rr(x, y, fw, fh, 1, outline=(240, 240, 240), width=1.5)
    vp.text(x + 4, y + 4, "Camera", REG, 8, (240, 240, 240))


def render_card(vp, p):
    """F12 result: a progress bar, then the finished picture."""
    if p <= 0.01:
        return
    w, h = 190, 100
    x, y = (VW - w) / 2, (VH - h) / 2 - 3
    vp.rr(x - 3, y - 3, w + 6, h + 6, 4, fill=(24, 24, 28), outline=(130, 130, 140), width=1.2)
    if p < 0.55:
        vp.rr(x + 20, y + h / 2 - 5, w - 40, 10, 3, fill=(50, 50, 56))
        vp.rr(x + 20, y + h / 2 - 5, max(3, (w - 40) * p / 0.55), 10, 3, fill=BLUE)
        vp.text(x + w / 2, y + h / 2 - 16, "Rendering...", REG, 9, (220, 220, 225), "mm")
        return
    for i in range(int(h)):
        c = lerp3((50, 70, 110), (150, 180, 215), i / h)
        vp.line([(x, y + i), (x + w, y + i)], tuple(int(v) for v in c), 1)
    cx, cy, s = x + w / 2, y + h * 0.6, 26
    vp.poly([(cx, cy - s), (cx + s * .87, cy - s * .5), (cx, cy), (cx - s * .87, cy - s * .5)], (225, 225, 230))
    vp.poly([(cx - s * .87, cy - s * .5), (cx, cy), (cx, cy + s), (cx - s * .87, cy + s * .5)], (150, 150, 160))
    vp.poly([(cx + s * .87, cy - s * .5), (cx, cy), (cx, cy + s), (cx + s * .87, cy + s * .5)], (105, 105, 115))
    vp.line([(x, y + h * 0.82), (x + w, y + h * 0.82)], (60, 90, 60), 3)


# ============================================================ one frame ====
def frame_image(spec, f):
    c = Canvas()
    c.text(14, 10, spec["title"], BOLD, 17, (240, 240, 240))
    c.text(14, 36, spec["sub"], REG, 9.5, GREYTXT)
    tokens = spec["keys"]
    st = [3 + 5 * i for i in range(len(tokens))]
    last = tokens[-1]
    e0 = st[-1] + 1 if last == "MOUSE" else st[-1] + 4
    e1 = e0 + 16
    reset = f >= N - 5
    t = seg(f, e0, e1) * (1 - seg(f, N - 5, N - 1))

    def part_state(i, kind):
        s0 = st[i]
        if reset or f < s0:
            return "idle"
        if kind == "mouse":
            tk = tokens[i]
            if tk == "MOUSE":
                if f >= e1 - 3 and f <= e1:
                    return "click"
                return "done" if f > e1 else "glow"
            return "click" if f <= s0 + 3 else "done"
        if f == s0:
            return "glow"
        return "press" if f <= s0 + 3 else "done"

    # layout
    groups = []
    for tk in tokens:
        parts = tk.split("+")
        groups.append(parts)
    widths = []
    for parts in groups:
        w = 0
        for pt in parts:
            w += MOUSE_W if pt in ("MOUSE", "CLICK", "RCLICK") else cap_width(pt)
        widths.append(w + 14 * (len(parts) - 1))
    total = sum(widths) + 24 * (len(groups) - 1)
    sc = min(1.0, 320.0 / total)
    total *= sc
    x = FW / 2 - total / 2
    y = 78
    for gi, parts in enumerate(groups):
        gw = widths[gi] * sc
        cx = x
        for pi, pt in enumerate(parts):
            if pt in ("MOUSE", "CLICK", "RCLICK"):
                wig = math.sin(seg(f, st[gi], e1) * math.pi * 2) * 4 if (pt == "MOUSE" and not reset and st[gi] <= f <= e1) else 0
                mouse(c, cx + MOUSE_W / 2, y, part_state(gi, "mouse") if pt != "RCLICK" else part_state(gi, "mouse"),
                      wig, "R" if pt == "RCLICK" else "L")
                cx += MOUSE_W
            else:
                w = cap_width(pt, sc)
                keycap(c, cx + w / 2, y, pt, part_state(gi, "key"), sc)
                cx += w
            if pi < len(parts) - 1:
                c.text(cx + 7 * sc, y, "+", BOLD, 14, (150, 150, 156), "mm")
                cx += 14 * sc
        x += gw
        if gi < len(groups) - 1:
            ax = x + 12 * sc
            c.line([(ax - 3, y - 5), (ax + 3, y), (ax - 3, y + 5)], (150, 150, 156), 2)
            x += 24 * sc
    vp = render_scene(spec["scene"](t, f), t, f)
    c.im.paste(vp.im, (VX * SS, VY * SS))
    c.rr(VX, VY, VW, VH, 2, outline=(95, 95, 104), width=1)
    if spec.get("caption"):
        c.text(FW / 2, 250, spec["caption"], REG, 9.5, GREYTXT, "mm")
    return c.out()


def make_sheet(spec):
    rows = (N + COLS - 1) // COLS
    sh = Image.new("RGB", (COLS * FW, rows * FH), BG)
    for f in range(N):
        sh.paste(frame_image(spec, f), ((f % COLS) * FW, (f // COLS) * FH))
    return sh, rows


def build(spec, out):
    sh, rows = make_sheet(spec)
    q = sh.quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q.save(os.path.join(out, spec["name"] + ".png"), optimize=True)
    return spec["name"], {"frames": N, "cols": COLS, "rows": rows, "w": FW, "h": FH, "fps": 20}


