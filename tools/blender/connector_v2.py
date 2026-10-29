"""Bulk connectors of 0.5.0: 1 x 1 housings that stand on the rim of a station and are
drawn over the loader's belt. The painted parts take the belt tier's colour
(build_sprites.py tints them).

- bunker: an inclined bucket elevator over two rim tiles. Its boot sits in the rim pit of
  the next tile (clockwise, east in the model), the casing climbs sideways to the head drum
  over the connector's tile, and a spout drops the goods onto the belt.
- silo: a belt conveyor in a casing over two rim tiles. Its tail hood takes the goods off
  the belt, the casing climbs sideways over the next tile (clockwise, east in the model)
  to the collector trough of the silo and discharges through the inlet there.

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

SILO_INLET = (0.0, 2.44)  # (y, z) of the mouth of the collector intake hopper the silo conveyor drops into


def _objects():
    import bpy
    return set(bpy.data.objects)


def elevator(p):
    """Inclined bucket elevator over two tiles: the boot sits in the rim pit of the next tile
    (clockwise, east in the model) and digs the goods out of the feeder below, the twin-leg
    casing climbs sideways to the head over the connector's own tile, and a spout drops the
    goods into the hood on the belt."""
    from mathutils import Vector
    by = -0.22  # casing axis, over the station half of the tiles
    boot = Vector((1.0, by, 0.16))
    head = Vector((-0.02, by, 1.62))
    # boot: a hopper sunk into the rim pit, with take-up screw and hazard band
    rig.box("boot", boot, (0.66, 0.46, 0.34), p["olive"], bevel=0.02, mask=True)
    rig.box("boot_cover", boot + Vector((0, 0, 0.18)), (0.7, 0.5, 0.04), p["steel"], bevel=0.008)
    kit.rivets(boot + Vector((-0.3, -0.24, 0.1)), boot + Vector((0.3, -0.24, 0.1)), 6, (0, -1, 0))
    kit.rivets(boot + Vector((-0.3, 0.24, 0.1)), boot + Vector((0.3, 0.24, 0.1)), 6, (0, 1, 0))
    kit.hazard(boot + Vector((0, 0.235, -0.06)), (0.6, 0.02, 0.1), stripes=5)
    rig.box("boot_take_up", boot + Vector((0.36, 0, 0.08)), (0.06, 0.24, 0.16), p["dark"], bevel=0.005)
    rig.cylinder("boot_screw", boot + Vector((0.39, 0, 0.08)), boot + Vector((0.39, 0, 0.3)), 0.014, p["chrome"], verts=8)
    # twin legs climbing from the boot to the head, flanged along the way
    start = boot + Vector((-0.12, 0, 0.18))
    end = head + Vector((0.14, 0, -0.12))
    for dy in (-0.11, 0.11):
        axis, length, rotation = beam(f"leg{dy}", start + Vector((0, dy, 0)), end + Vector((0, dy, 0)), (0.2, 0.18),
                                      p["olive"], bevel=0.008, mask=True)
    for k in range(7):
        c = start + axis * (0.12 + k * (length - 0.24) / 6)
        rig.box(f"flange{k}", c, (0.3, 0.48, 0.035), p["steel"], bevel=0.004, rotation=rotation)
    side = Vector((0, 0.205, 0))
    for k in range(2):  # inspection doors on the camera side
        c = start + axis * (0.45 + k * (length - 0.9)) + side
        rig.box(f"door{k}", c, (0.14, 0.012, 0.22), p["steel"], bevel=0.003, rotation=rotation)
        rig.box(f"door_handle{k}", c + Vector((0.04, 0.01, 0)), (0.02, 0.01, 0.06), p["chrome"], bevel=0, rotation=rotation)
    kit.rivets(start + axis * 0.2 + side + Vector((0.11, 0, 0)), end - axis * 0.2 + side + Vector((0.11, 0, 0)), 9, (0, 1, 0),
               radius=0.01)
    # trestle under the middle of the climb
    mid = start + axis * (length * 0.5)
    for dy in (-0.2, 0.2):
        rig.cylinder(f"post{dy}", (mid.x, mid.y + dy, 0.04), (mid.x, mid.y + dy, mid.z - 0.16), 0.03, p["steel"], verts=8)
        kit.footing(mid.x, mid.y + dy, size=(0.16, 0.16), height=0.05)
    rig.box("trestle_cap", (mid.x, mid.y, mid.z - 0.16), (0.14, 0.52, 0.06), p["steel"], bevel=0.004)
    rig.cylinder("trestle_brace", (mid.x, mid.y - 0.2, 0.15), (mid.x, mid.y + 0.2, mid.z - 0.24), 0.014, p["steel"], verts=6)
    # head: housing over the drum, bearings, gearbox and motor, warning lamp
    rig.box("head", head + Vector((0, 0.04, 0.1)), (0.5, 0.46, 0.38), p["olive"], bevel=0.02, mask=True)
    rig.box("head_hood", head + Vector((0, 0.04, 0.31)), (0.52, 0.48, 0.05), p["steel"], bevel=0.01)
    rig.cylinder("drum_axle", head + Vector((-0.32, 0.02, 0.08)), head + Vector((0.32, 0.02, 0.08)), 0.032, p["chrome"], verts=12)
    for sx in (-1, 1):
        rig.box(f"bearing{sx}", head + Vector((sx * 0.28, 0.02, 0.08)), (0.05, 0.13, 0.11), p["dark"], bevel=0.006)
    kit.rivets(head + Vector((-0.22, -0.195, 0.22)), head + Vector((0.22, -0.195, 0.22)), 5, (0, -1, 0), radius=0.012)
    kit.gearbox(tuple(head + Vector((-0.4, 0.02, 0.06))), size=(0.14, 0.2, 0.18))
    kit.motor(tuple(head + Vector((-0.4, 0.02, 0.27))), axis="y", length=0.22, radius=0.07)
    kit.lamp(tuple(head + Vector((0.18, 0.22, 0.36))), "amber", size=0.032)
    # spout from the head down onto the belt, ending in a hood with rubber curtains
    a, b = (0, by + 0.24, head.z), (0, 0.18, 0.5)
    dy, dz = b[1] - a[1], b[2] - a[2]
    length = math.hypot(dy, dz)
    tilt = math.atan2(-dy, dz)
    rig.box("spout", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), (0.28, 0.18, length), p["steel"], bevel=0.01,
            rotation=(tilt, 0, 0))
    # the hood covers the whole belt on the connector's tile, so no goods show beside the legs
    rig.box("hood", (0, -0.035, 0.2), (0.92, 0.89, 0.32), p["olive"], bevel=0.02, mask=True)
    rig.box("hood_roof", (0, -0.035, 0.375), (0.94, 0.91, 0.03), p["steel"], bevel=0.006)
    overhang(p, 0.41)
    kit.cable([(-0.4, by - 0.05, head.z + 0.3), (0.2, by - 0.16, 1.0), (boot.x - 0.2, by - 0.24, 0.36)], "red")


OVERHANG_END = 0.92  # how far the shroud reaches over the next belt tile (tile edge at 0.5)


def overhang(p, y0):
    """A low shroud from the hood front at y0 out over the start of the belt, like the
    mouth of an underground belt: the goods appear (or vanish) under it, not on open belt.
    Rubber curtains hang at its open end."""
    y1 = OVERHANG_END
    cy, ly = (y0 + y1) / 2, y1 - y0
    rig.box("shroud", (0, cy, 0.17), (0.92, ly, 0.26), p["olive"], bevel=0.015, mask=True)
    rig.box("shroud_roof", (0, cy, 0.31), (0.94, ly + 0.02, 0.03), p["steel"], bevel=0.005)
    for k in range(3):
        y = y0 + 0.06 + k * (ly - 0.12) / 2
        rig.box(f"shroud_band{k}", (0, y, 0.17), (0.96, 0.035, 0.28), p["steel"], bevel=0.004)
    for sx in (-1, 1):
        kit.rivets((sx * 0.465, y0 + 0.08, 0.24), (sx * 0.465, y1 - 0.08, 0.24), 4, (sx, 0, 0), radius=0.009)
    rig.box("shroud_mouth", (0, y1 + 0.005, 0.14), (0.82, 0.01, 0.2), p["dark"], bevel=0)
    for c in range(10):
        rig.box(f"curtain{c}", (-0.36 + c * 0.08, y1 + 0.012, 0.13), (0.072, 0.008, 0.2), p["rubber"], bevel=0)
    kit.hazard((0, y1 + 0.012, 0.27), (0.86, 0.01, 0.05), stripes=7)


def beam(name, a, b, section, mat, bevel=0.01, mask=False):
    """A box from a to b with the given cross section; returns its axis and length."""
    from mathutils import Vector
    a, b = Vector(a), Vector(b)
    d = b - a
    rotation = d.to_track_quat("Z", "Y").to_euler()
    rig.box(name, (a + b) / 2, (section[0], section[1], d.length), mat, bevel=bevel, mask=mask, rotation=rotation)
    return d.normalized(), d.length, rotation


def conveyor(p):
    """Steep belt conveyor over two tiles: the tail hood takes the goods off the belt on
    the connector's own tile, the casing climbs sideways over the next tile (east in the
    model) to the collector trough at the foot of the silo bin."""
    from mathutils import Vector
    top = Vector((1.0, SILO_INLET[0], SILO_INLET[1]))
    # tail hood: the belt runs in under it, the conveyor's tail drum takes the goods
    rig.box("tail", (0.02, 0.08, 0.24), (0.7, 0.6, 0.4), p["olive"], bevel=0.02, mask=True)
    rig.box("tail_roof", (0.02, 0.08, 0.455), (0.72, 0.62, 0.035), p["steel"], bevel=0.006)
    kit.hazard((0.02, 0.385, 0.38), (0.62, 0.01, 0.07), stripes=6)
    overhang(p, 0.38)
    kit.rivets((-0.3, -0.225, 0.38), (0.34, -0.225, 0.38), 7, (0, -1, 0), radius=0.013)
    rig.cylinder("tail_axle", (-0.36, 0.08, 0.24), (0.4, 0.08, 0.24), 0.03, p["chrome"], verts=10)
    kit.motor((-0.34, -0.08, 0.5), axis="x", length=0.18, radius=0.065)
    # casing: a heavy closed box girder climbing sideways to the collector intake
    start = Vector((0.22, -0.04, 0.4))
    end = top + Vector((-0.2, 0.0, 0.14))
    axis, length, rotation = beam("casing", start, end, (0.44, 0.34), p["olive"], mask=True)
    for k in range(9):
        c = start + axis * (0.1 + k * (length - 0.2) / 8)
        rig.box(f"rib{k}", c, (0.52, 0.42, 0.04), p["steel"], bevel=0.005, rotation=rotation)
    side = Vector((0, 0.175, 0))
    for k in range(3):  # inspection doors on the camera side
        c = start + axis * (0.5 + k * (length - 0.9) / 2) + side
        rig.box(f"door{k}", c, (0.14, 0.012, 0.24), p["steel"], bevel=0.003, rotation=rotation)
        rig.box(f"door_handle{k}", c + Vector((0.04, 0.01, 0)), (0.02, 0.01, 0.06), p["chrome"], bevel=0, rotation=rotation)
    kit.rivets(start + axis * 0.2 + side + Vector((0.16, 0, 0)), end - axis * 0.2 + side + Vector((0.16, 0, 0)), 11, (0, 1, 0),
               radius=0.011)
    # trestle on the second tile carrying the casing
    mid = start + axis * (length * 0.55)
    for dy in (-0.2, 0.2):
        rig.cylinder(f"post{dy}", (mid.x, mid.y + dy, 0.04), (mid.x, mid.y + dy, mid.z - 0.18), 0.032, p["steel"], verts=8)
        kit.footing(mid.x, mid.y + dy, size=(0.16, 0.16), height=0.05)
    rig.box("trestle_cap", (mid.x, mid.y, mid.z - 0.18), (0.14, 0.52, 0.06), p["steel"], bevel=0.004)
    rig.cylinder("trestle_brace", (mid.x, mid.y - 0.2, 0.15), (mid.x, mid.y + 0.2, mid.z - 0.26), 0.014, p["steel"], verts=6)
    rig.cylinder("stay", (0.38, 0.32, 0.02), (start.x + axis.x * 0.6, start.y + 0.14, start.z + axis.z * 0.6), 0.018,
                 p["steel"], verts=6)
    # head: drive drum housing over the intake, motor on the side, and a discharge hood
    # that drops down into the hopper mouth with a dark open throat
    rig.box("head", (top.x - 0.12, top.y, top.z + 0.32), (0.5, 0.46, 0.36), p["olive"], bevel=0.02, mask=True)
    rig.box("head_roof", (top.x - 0.12, top.y, top.z + 0.515), (0.52, 0.48, 0.035), p["steel"], bevel=0.006)
    rig.cylinder("head_axle", (top.x - 0.12, top.y - 0.29, top.z + 0.32), (top.x - 0.12, top.y + 0.29, top.z + 0.32), 0.035,
                 p["chrome"], verts=12)
    kit.gearbox((top.x - 0.12, top.y + 0.33, top.z + 0.26), size=(0.18, 0.12, 0.16))
    kit.motor((top.x - 0.32, top.y + 0.33, top.z + 0.3), axis="x", length=0.2, radius=0.06)
    rig.box("discharge", (top.x + 0.02, top.y, top.z + 0.08), (0.3, 0.32, 0.2), p["steel"], bevel=0.01)
    rig.box("discharge_throat", (top.x + 0.02, top.y, top.z - 0.02), (0.22, 0.24, 0.02), p["dark"], bevel=0)
    kit.rivets((top.x - 0.34, top.y + 0.235, top.z + 0.46), (top.x + 0.1, top.y + 0.235, top.z + 0.46), 5, (0, 1, 0),
               radius=0.012)
    kit.lamp((top.x - 0.3, top.y + 0.15, top.z + 0.54), "green", size=0.032)
    kit.cable([(-0.34, -0.08, 0.6), (0.3, 0.1, 1.2), (top.x - 0.32, top.y + 0.3, top.z + 0.3)], "red")


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
    rig.camera(4, 5, shift_y=1.2)


if __name__ == "__main__":
    a = rig.args()
    out, kind = a[0], a[1]
    build(kind)
    rig.render_frames(out, [0, 1, 2, 3], lambda i: i / 4, passes=("color", "mask"), samples=32)
