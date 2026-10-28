"""Bulk connectors of 0.5.0: 1 x 1 housings that stand on the rim of a station and are
drawn over the loader's belt. The painted parts take the belt tier's colour
(build_sprites.py tints them).

- bunker: a bucket elevator. Its boot sits in the pit opening of the bunker rim, the
  casing rises to a head drum, and a spout drops the goods onto the belt.
- silo: a steep belt conveyor in a casing. Its tail hood takes the goods off the belt,
  the casing climbs to the collector trough at the foot of the silo bin and discharges
  through the inlet there.

Run:  blender -b --factory-startup -P tools/blender/connector_v2.py -- <out_dir> <bunker|silo>
Model: the station lies south of the tile (y < -0.5), the belt leaves to the north.
Renders color_000..003 and mask_000..003 for the belt pointing north, east, south and
west, like connector.py.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import rig  # noqa: E402

SILO_INLET = (-0.12, 3.32)  # (y, z) of the collector inlet the silo conveyor reaches


def _objects():
    import bpy
    return set(bpy.data.objects)


def elevator(p):
    """Bucket elevator: boot in the rim pit, twin-leg casing, head drum, spout to the belt."""
    by = -0.27  # casing axis, over the station half of the tile
    head_z = 1.62
    # boot: a hopper sunk into the rim, the buckets dig the goods out of the feeder below
    rig.box("boot", (0, by, 0.16), (0.62, 0.38, 0.3), p["olive"], bevel=0.02, mask=True)
    rig.box("boot_cover", (0, by, 0.32), (0.66, 0.42, 0.04), p["steel"], bevel=0.008)
    kit.rivets((-0.28, by - 0.2, 0.25), (0.28, by - 0.2, 0.25), 6, (0, -1, 0))
    kit.rivets((-0.28, by + 0.2, 0.25), (0.28, by + 0.2, 0.25), 6, (0, 1, 0))
    kit.hazard((0, by + 0.195, 0.1), (0.56, 0.02, 0.1), stripes=5)
    rig.box("boot_take_up", (0.34, by, 0.24), (0.06, 0.2, 0.14), p["dark"], bevel=0.005)
    rig.cylinder("boot_screw", (0.37, by, 0.24), (0.37, by, 0.42), 0.012, p["chrome"], verts=8)
    # twin legs (up and down run of the buckets), flanged every few sections
    for dx in (-0.1, 0.1):
        rig.box(f"leg{dx}", (dx, by, (0.34 + head_z) / 2), (0.15, 0.22, head_z - 0.34), p["olive"], bevel=0.008, mask=True)
    for k in range(5):
        z = 0.5 + k * 0.25
        rig.box(f"flange{k}", (0, by, z), (0.38, 0.27, 0.03), p["steel"], bevel=0.004)
        kit.rivets((-0.17, by - 0.14, z), (0.17, by - 0.14, z), 4, (0, -1, 0), radius=0.01)
    # inspection door with handle on the camera side of the up leg
    rig.box("door", (0.1, by + 0.115, 0.95), (0.12, 0.012, 0.2), p["steel"], bevel=0.004)
    rig.box("door_handle", (0.13, by + 0.125, 0.95), (0.02, 0.01, 0.06), p["chrome"], bevel=0)
    # head: housing over the drum, drum bearings, motor and gearbox on the side
    rig.box("head", (0, by + 0.04, head_z + 0.1), (0.44, 0.4, 0.34), p["olive"], bevel=0.02, mask=True)
    rig.box("head_hood", (0, by + 0.04, head_z + 0.29), (0.46, 0.42, 0.05), p["steel"], bevel=0.01)
    rig.cylinder("drum_axle", (-0.29, by + 0.02, head_z + 0.08), (0.29, by + 0.02, head_z + 0.08), 0.03, p["chrome"], verts=12)
    for sx in (-1, 1):
        rig.box(f"bearing{sx}", (sx * 0.25, by + 0.02, head_z + 0.08), (0.05, 0.12, 0.1), p["dark"], bevel=0.006)
    kit.rivets((-0.2, by - 0.165, head_z + 0.22), (0.2, by - 0.165, head_z + 0.22), 5, (0, -1, 0), radius=0.012)
    kit.gearbox((0.36, by + 0.02, head_z + 0.06), size=(0.14, 0.18, 0.18))
    kit.motor((0.36, by + 0.02, head_z + 0.25), axis="y", length=0.2, radius=0.065)
    kit.lamp((-0.16, by + 0.18, head_z + 0.34), "amber", size=0.03)
    # spout from the head down onto the belt, ending in a hood with rubber curtains
    a, b = (0, by + 0.2, head_z), (0, 0.18, 0.5)
    dy, dz = b[1] - a[1], b[2] - a[2]
    length = math.hypot(dy, dz)
    tilt = math.atan2(-dy, dz)
    rig.box("spout", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), (0.24, 0.16, length), p["steel"], bevel=0.01,
            rotation=(tilt, 0, 0))
    rig.box("hood", (0, 0.22, 0.27), (0.6, 0.36, 0.3), p["olive"], bevel=0.02, mask=True)
    rig.box("hood_roof", (0, 0.22, 0.43), (0.62, 0.38, 0.03), p["steel"], bevel=0.006)
    rig.box("hood_mouth", (0, 0.405, 0.2), (0.48, 0.01, 0.2), p["dark"], bevel=0)
    for c in range(6):
        rig.box(f"curtain{c}", (-0.2 + c * 0.08, 0.412, 0.19), (0.07, 0.008, 0.2), p["rubber"], bevel=0)
    kit.rivets((-0.27, 0.41, 0.38), (0.27, 0.41, 0.38), 6, (0, 1, 0), radius=0.01)
    # stay from the head to the hood, and a cable to the motor
    rig.cylinder("stay", (-0.24, by + 0.2, head_z - 0.05), (-0.26, 0.2, 0.42), 0.014, p["steel"], verts=6)
    kit.cable([(0.36, by - 0.05, head_z + 0.3), (0.32, by - 0.12, 1.0), (0.3, by - 0.14, 0.34)], "red")


def conveyor(p):
    """Steep belt conveyor: tail hood over the belt, casing up to the silo's collector."""
    top_y, top_z = SILO_INLET
    # tail hood: the belt runs in under it, the conveyor's tail drum takes the goods
    rig.box("tail", (0, 0.12, 0.2), (0.62, 0.5, 0.32), p["olive"], bevel=0.02, mask=True)
    rig.box("tail_roof", (0, 0.12, 0.37), (0.64, 0.52, 0.03), p["steel"], bevel=0.006)
    rig.box("tail_mouth", (0, 0.375, 0.16), (0.5, 0.01, 0.2), p["dark"], bevel=0)
    for c in range(6):
        rig.box(f"skirt{c}", (-0.21 + c * 0.084, 0.382, 0.15), (0.075, 0.008, 0.18), p["rubber"], bevel=0)
    kit.hazard((0, 0.385, 0.31), (0.56, 0.01, 0.06), stripes=5)
    kit.rivets((-0.28, -0.13, 0.3), (0.28, -0.13, 0.3), 6, (0, -1, 0), radius=0.012)
    rig.cylinder("tail_axle", (-0.34, 0.12, 0.2), (0.34, 0.12, 0.2), 0.025, p["chrome"], verts=10)
    # casing: a closed box girder climbing steeply to the collector inlet
    a, b = (0, 0.02, 0.3), (0, top_y + 0.08, top_z - 0.05)
    dy, dz = b[1] - a[1], b[2] - a[2]
    length = math.hypot(dy, dz)
    tilt = math.atan2(-dy, dz)
    mid = (0, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
    rig.box("casing", mid, (0.3, 0.2, length), p["olive"], bevel=0.01, mask=True, rotation=(tilt, 0, 0))
    up = (0, -math.sin(tilt), math.cos(tilt))
    for k in range(9):
        t = 0.08 + k * (length - 0.16) / 8
        c = (0, a[1] + up[1] * t, a[2] + up[2] * t)
        rig.box(f"rib{k}", c, (0.36, 0.25, 0.03), p["steel"], bevel=0.004, rotation=(tilt, 0, 0))
    for k in range(3):  # inspection doors on the camera side
        t = 0.6 + k * 0.85
        c = (0.08, a[1] + up[1] * t + 0.105, a[2] + up[2] * t)
        rig.box(f"door{k}", c, (0.1, 0.01, 0.18), p["steel"], bevel=0.003, rotation=(tilt, 0, 0))
    # A-frame stays down to the rim, braced against the casing
    for sx in (-1, 1):
        rig.cylinder(f"stay{sx}", (sx * 0.3, 0.32, 0.02), (sx * 0.16, 0.0, 1.7), 0.02, p["steel"], verts=6)
        kit.footing(sx * 0.3, 0.32, size=(0.12, 0.12), height=0.05)
    rig.cylinder("stay_tie", (-0.24, 0.17, 0.85), (0.24, 0.17, 0.85), 0.013, p["steel"], verts=6)
    # head: drive drum, motor, and the snout that reaches into the collector inlet
    rig.box("head", (0, top_y + 0.1, top_z + 0.08), (0.4, 0.34, 0.3), p["olive"], bevel=0.02, mask=True)
    rig.box("snout", (0, top_y - 0.14, top_z - 0.02), (0.3, 0.22, 0.16), p["steel"], bevel=0.01)
    kit.motor((0.3, top_y + 0.1, top_z + 0.08), axis="x", length=0.18, radius=0.06)
    kit.rivets((-0.17, top_y + 0.275, top_z + 0.18), (0.17, top_y + 0.275, top_z + 0.18), 4, (0, 1, 0), radius=0.01)
    kit.lamp((-0.13, top_y + 0.2, top_z + 0.26), "green", size=0.028)
    kit.cable([(0.3, top_y + 0.2, top_z + 0.04), (0.24, 0.0, 1.8), (0.25, 0.2, 0.36)], "red")


BUILDERS = {"bunker": elevator, "silo": conveyor}


def place(kind, location, turn):
    """Builds a connector at location, turned by turn quarter turns clockwise (as seen
    from above): 0 has the station south. For scene previews."""
    p = kit.palette()
    before = _objects()
    BUILDERS[kind](p)
    holder = kit.pivot(kit._n(f"connector_{kind}"), location)
    holder.rotation_euler = (0, 0, -turn * math.pi / 2)
    for obj in _objects() - before:
        if obj != holder and (obj.parent is None or obj.parent == rig.root()):
            obj.parent = holder
    return holder


def build(kind):
    rig.reset()
    kit.reset()
    p = kit.palette()
    rig.layer("base")
    BUILDERS[kind](p)
    rig.sun()
    rig.fill_light()
    if kind == "bunker":
        rig.camera(3, 3.5, shift_y=0.6)
    else:
        rig.camera(3, 6, shift_y=1.9)


if __name__ == "__main__":
    a = rig.args()
    out, kind = a[0], a[1]
    build(kind)
    rig.render_frames(out, [0, 1, 2, 3], lambda i: i / 4, passes=("color", "mask"), samples=32)
