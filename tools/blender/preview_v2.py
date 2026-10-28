"""Preview of a 0.5.0 station with three connectors on each long side, for a design check.

Run:  blender -b --factory-startup -P tools/blender/preview_v2.py -- <out_dir> <bunker|silo> [samples]
Writes color_000, mask_000 and shadow_000; compose them with pack.composite.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import connector_v2  # noqa: E402
import rig  # noqa: E402

if __name__ == "__main__":
    a = rig.args()
    out, kind = a[0], a[1]
    samples = int(a[2]) if len(a) > 2 else 24
    if kind == "bunker":
        import station_bunker as station
        edge = 3.5
    else:
        import station_silo as station
        edge = 2.5
    station.build()
    for y in (-2.5, -0.5, 1.5):
        connector_v2.place(kind, (edge, y, 0), 1)
        connector_v2.place(kind, (-edge, y + 1, 0), 3)
    if kind == "bunker":
        rig.camera(10, 9, shift_y=0.6)
    else:
        rig.camera(9, 12.5, shift_y=3.0)
    rig.render_frames(out, [0], lambda i: 0, passes=("color", "mask", "shadow"), samples=samples)
