"""Make the hint animations:  python navgen.py <media_folder> [name ...]"""
import json
import os
import sys

import navgen_engine as E
from navgen_specs import SPECS


def build(spec, out):
    sh, rows = E.make_sheet(spec)
    q = sh.quantize(colors=160, method=E.Image.Quantize.MEDIANCUT, dither=E.Image.Dither.NONE)
    q.save(os.path.join(out, spec["name"] + ".png"), optimize=True)
    return spec["name"], {"frames": E.N, "cols": E.COLS, "rows": rows, "w": E.FW, "h": E.FH, "fps": 20}


if __name__ == "__main__":
    out = sys.argv[1]
    want = set(sys.argv[2:])
    meta_path = os.path.join(out, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    todo = [s for s in SPECS if not want or s["name"] in want]
    for spec in todo:
        name, m = build(spec, out)
        meta[name] = m
        print("made", name, flush=True)
        json.dump(meta, open(meta_path, "w"), indent=1)
    json.dump(meta, open(meta_path, "w"), indent=1)
