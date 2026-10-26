"""Bulk connector (0.4.0): the 1 x 2 housing the game draws over a loader's belt. At
the station end a hood swallows (or releases) the goods, low skirt walls guide the belt
out. The painted parts take the belt tier's colour (build_sprites.py tints them).

Run:  blender -b --factory-startup -P tools/blender/connector.py -- <out_dir>
Model: belt leaves to the north, the station is south. Renders color_000..003 and
mask_000..003 for the belt pointing north, east, south and west.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import rig  # noqa: E402


def build():
    rig.reset()
    kit.reset()
    p = kit.palette()
    rig.layer("base")
    # skirt walls along the belt, painted
    for sx in (-1, 1):
        rig.box(f"skirt{sx}", (sx * 0.44, 0.1, 0.1), (0.07, 1.7, 0.2), p["olive"], bevel=0.01, mask=True)
        kit.rivets((sx * 0.48, -0.6, 0.12), (sx * 0.48, 0.85, 0.12), 6, (sx, 0, 0))
        rig.box(f"skirt_foot{sx}", (sx * 0.44, 0.1, 0.01), (0.12, 1.72, 0.02), p["dark"], bevel=0)
    # hood at the station end with a dark mouth and rubber curtain
    rig.box("hood", (0, -0.62, 0.24), (0.98, 0.74, 0.48), p["olive"], bevel=0.03, mask=True)
    rig.box("hood_roof", (0, -0.62, 0.49), (1.0, 0.78, 0.04), p["olive"], bevel=0.01, mask=True)
    kit.hazard((0, -0.245, 0.4), (0.9, 0.02, 0.1), stripes=7)
    rig.box("mouth", (0, -0.24, 0.17), (0.72, 0.02, 0.26), p["dark"], bevel=0)
    for c in range(8):
        rig.box(f"curtain{c}", (-0.31 + c * 0.089, -0.225, 0.16), (0.08, 0.012, 0.24), p["rubber"], bevel=0)
    kit.rivets((-0.42, -0.98, 0.45), (0.42, -0.98, 0.45), 6, (0, -1, 0))
    kit.motor((0.3, -0.7, 0.58), axis="y", length=0.3, radius=0.07)
    # end roller at the outer end
    rig.cylinder("roller", (-0.38, 0.93, 0.08), (0.38, 0.93, 0.08), 0.05, p["chrome"], verts=12)
    rig.sun()
    rig.fill_light()
    rig.camera(3, 3, shift_y=0.2)


if __name__ == "__main__":
    out = rig.args()[0]
    build()
    rig.render_frames(out, [0, 1, 2, 3], lambda i: i / 4, passes=("color", "mask"), samples=32)
