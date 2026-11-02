"""Builds the add-on zip. Run from the repo root:

    python scripts/build_release.py

  dist/navigation_guide_vX.Y.Z.zip   the add-on (Blender: Edit > Preferences >
                                     Get Extensions > Install from Disk)
"""
import re
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADDON = ROOT / "navigation_guide"
DIST = ROOT / "dist"


def addon_files():
    for p in sorted(ADDON.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            yield p, p.relative_to(ADDON).as_posix()


def add(zf, src, arcname, executable=False):
    info = zipfile.ZipInfo.from_file(src, arcname)
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if executable else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    with open(src, "rb") as f:
        zf.writestr(info, f.read())


def main():
    DIST.mkdir(exist_ok=True)
    version = re.search(r'^version\s*=\s*"([^"]+)"',
                        (ADDON / "blender_manifest.toml").read_text(encoding="utf-8"), re.M).group(1)

    addon_zip = DIST / f"navigation_guide_v{version}.zip"
    with zipfile.ZipFile(addon_zip, "w") as zf:
        for src, rel in addon_files():
            add(zf, src, rel)
    print("wrote", addon_zip)


if __name__ == "__main__":
    main()
