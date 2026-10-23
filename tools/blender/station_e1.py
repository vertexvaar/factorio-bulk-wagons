"""E1 unloading pit in the 2.1 style: a riveted, rusty pit under the track with
walkable gratings either side, an extraction belt that climbs out at the belt port,
a drive house and a hydraulic power unit that works the wagon's discharge flaps.

Run:  blender -b --factory-startup -P tools/blender/station_e1.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 2 tiles, rail north-south through x in [-1, 1], port east
at (2.5, -0.5). The whole pit is one ground sprite, drawn below the rails in game.

Renders per variant: idle_000 (still), extend_000..007 (flap openers rise to the wagon,
played once when a wagon arrives) and work_000..007 (belt running, drive turning,
beacon rotating, openers up).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import rig  # noqa: E402

ANIM_FRAMES = 8
EXTEND_FRAMES = 8
DEPTH = -0.75
BELT_Y = -0.5
BELT_W = 0.5
CLEAT_SPACING = 0.2
BELT_START, BELT_FLAT_END, BELT_END = -2.6, 1.7, 2.6  # x positions; the belt ramps up after BELT_FLAT_END

moving = []  # (object, start offset along the belt path, height above the belt)
spinning = []  # (pivot, step per frame)
beacon = []
openers = []  # (pivot, side)
ore = []


def belt_point(u):
    """Point on the belt path, u in [0, 1): flat along the bottom, then up the ramp."""
    flat = BELT_FLAT_END - BELT_START
    ramp = math.hypot(BELT_END - BELT_FLAT_END, -DEPTH - 0.12)
    d = u * (flat + ramp)
    if d <= flat:
        return (BELT_START + d, BELT_Y, DEPTH + 0.2)
    t = (d - flat) / ramp
    return (BELT_FLAT_END + t * (BELT_END - BELT_FLAT_END), BELT_Y, DEPTH + 0.2 + t * (-DEPTH - 0.12))


def pit(p):
    # concrete curbs with riveted steel cover plates and hazard edges
    for sx in (-1, 1):
        x0, x1 = sx * 1.02, sx * 2.98
        cx, w = (x0 + x1) / 2, abs(x1 - x0)
        for sy in (-1, 1):
            rig.box(f"curb{sx}{sy}", (cx, sy * 0.9, -0.06), (w, 0.2, 0.24), p["concrete"], bevel=0.02)
            kit.plate((cx, sy * 0.9, 0.065), (w, 0.2, 0.02), p["plate"], panels=4)
            kit.hazard((cx, sy * 0.985, 0.03), (w - 0.1, 0.03, 0.05), stripes=int(w / 0.18))
        rig.box(f"end_wall{sx}", (sx * 2.9, 0, -0.06), (0.2, 1.6, 0.24), p["concrete"], bevel=0.02)
        kit.plate((sx * 2.9, 0, 0.065), (0.2, 1.6, 0.02), p["plate"])
    # funnel walls: riveted steel sloping down to the belt trough
    rig.mesh("funnel", [
        (-2.8, -0.8, 0), (2.8, -0.8, 0), (2.8, 0.8, 0), (-2.8, 0.8, 0),
        (-2.7, BELT_Y - 0.3, DEPTH), (BELT_FLAT_END, BELT_Y - 0.3, DEPTH), (BELT_FLAT_END, BELT_Y + 0.3, DEPTH),
        (-2.7, BELT_Y + 0.3, DEPTH),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0), (4, 7, 6, 5)], p["plate"])
    for k in range(10):
        x = -2.6 + k * 0.48
        for (y0, y1) in ((0.8, BELT_Y + 0.3), (-0.8, BELT_Y - 0.3)):
            rig.cylinder(f"funnel_rib{k}{y0}", (x, y0, -0.01), (x, y1, DEPTH + 0.01), 0.025, p["steel"], verts=6)
    # rail bridge: I-beams carrying the track over the open pit
    for x in (-0.55, 0.55):
        kit.ibeam((x, -1.0, -0.14), (x, 1.0, -0.14), size=0.24)
    for y in (-0.7, 0.0, 0.7):
        kit.ibeam((-1.0, y, -0.38), (1.0, y, -0.38), size=0.16)
    # walkable gratings on I-beams over the side bays
    for sx in (-1, 1):
        cx = sx * 1.95
        kit.grating((cx, 0, 0.02), (1.82, 1.58), bar_every=0.09)
        for y in (-0.45, 0.45):
            kit.ibeam((cx - 0.9, y, -0.06), (cx + 0.9, y, -0.06), size=0.1)
    # vibrating feeders under the gratings, on springs
    for x in (-2.0, -1.35, 1.35):
        rig.box(f"feeder{x}", (x, BELT_Y + 0.05, DEPTH + 0.45), (0.45, 0.5, 0.16), p["olive"], bevel=0.02)
        for dx in (-0.16, 0.16):
            for dy in (-0.18, 0.18):
                rig.cylinder(f"spring{x}{dx}{dy}", (x + dx, BELT_Y + 0.05 + dy, DEPTH + 0.3),
                             (x + dx, BELT_Y + 0.05 + dy, DEPTH + 0.37), 0.03, p["chrome"], verts=8)
        kit.motor((x, BELT_Y + 0.38, DEPTH + 0.48), axis="x", length=0.22, radius=0.07)
    # ore residue
    for x in (-2.0, -0.6, 0.7):
        rig.box(f"heap{x}", (x, BELT_Y + 0.32, DEPTH + 0.08), (0.7, 0.25, 0.12), p["concrete"], bevel=0.05)


def extraction_belt(p):
    flat_len = BELT_FLAT_END - BELT_START
    rig.box("belt_flat", ((BELT_START + BELT_FLAT_END) / 2, BELT_Y, DEPTH + 0.17), (flat_len, BELT_W, 0.04), p["rubber"], bevel=0)
    ramp_len = math.hypot(BELT_END - BELT_FLAT_END, -DEPTH - 0.12)
    ramp_angle = math.atan2(-DEPTH - 0.12, BELT_END - BELT_FLAT_END)
    ramp_mid = ((BELT_FLAT_END + BELT_END) / 2, BELT_Y, (DEPTH + 0.17 - 0.1) / 2 + 0.06)
    rig.box("belt_ramp", ramp_mid, (ramp_len, BELT_W, 0.04), p["rubber"], bevel=0, rotation=(0, -ramp_angle, 0))
    for s in (-1, 1):
        rig.box(f"skirt_flat{s}", ((BELT_START + BELT_FLAT_END) / 2, BELT_Y + s * (BELT_W / 2 + 0.04), DEPTH + 0.25),
                (flat_len, 0.05, 0.16), p["steel"])
        rig.box(f"skirt_ramp{s}", (ramp_mid[0], BELT_Y + s * (BELT_W / 2 + 0.04), ramp_mid[2] + 0.08), (ramp_len, 0.05, 0.16),
                p["steel"], rotation=(0, -ramp_angle, 0))
        kit.rivets((BELT_START, BELT_Y + s * (BELT_W / 2 + 0.07), DEPTH + 0.3),
                   (BELT_FLAT_END, BELT_Y + s * (BELT_W / 2 + 0.07), DEPTH + 0.3), 30, (0, s, 0))
    count = int((flat_len + ramp_len) / CLEAT_SPACING)
    for k in range(count):
        u = k / count
        cleat = rig.box(f"cleat{k}", belt_point(u), (0.025, BELT_W - 0.06, 0.02), p["dark"], bevel=0)
        moving.append((cleat, u, 0.0))
        if k % 2 == 0:
            heap = rig.box(f"ore{k}", belt_point(u), (0.1, 0.22, 0.05), p["concrete"], bevel=0.02)
            moving.append((heap, u + 0.5 / count, 0.03))
            ore.append(heap)


def drive_house(p):
    """Drive at the port end, north of the belt exit: motor, gearbox, open gears, cabinet."""
    rig.box("drive_slab", (2.55, 0.42, 0.06), (0.8, 0.95, 0.12), p["concrete"], bevel=0.02)
    kit.plate((2.55, 0.42, 0.13), (0.78, 0.92, 0.02), p["plate"])
    kit.motor((2.32, 0.55, 0.32), axis="x", length=0.36, radius=0.13)
    kit.gearbox((2.72, 0.55, 0.3), (0.3, 0.32, 0.32))
    big = rig.gear("drive_gear", (2.72, 0.33, 0.33), 0.13, 0.035, 14, p["brass"], axis="y")
    spinning.append((big, 2 * math.pi / 14))
    small = rig.gear("drive_pinion", (2.55, 0.33, 0.42), 0.07, 0.035, 8, p["brass"], axis="y")
    spinning.append((small, -2 * math.pi / 8))
    rig.box("guard", (2.64, 0.28, 0.38), (0.36, 0.02, 0.3), p["yellow"], bevel=0.01)
    kit.cabinet((2.62, 0.87, 0.42), (0.5, 0.16, 0.55), facing="-y")
    kit.cable([(2.4, 0.86, 0.66), (2.3, 0.7, 0.62), (2.32, 0.6, 0.47)], "red")
    kit.cable([(2.5, 0.86, 0.68), (2.45, 0.62, 0.6), (2.6, 0.55, 0.48)], "blue")
    # warning beacon
    rig.cylinder("beacon_post", (2.92, -0.1, 0.12), (2.92, -0.1, 0.62), 0.025, p["steel"])
    rig.cylinder("beacon_glass", (2.92, -0.1, 0.62), (2.92, -0.1, 0.74), 0.06, p["amber_lamp"], verts=16)
    pivot = rig.gear("beacon_reflector", (2.92, -0.1, 0.68), 0.035, 0.1, 2, p["chrome"], axis="z")
    beacon.append(pivot)
    # belt exit housing over the ramp top
    rig.box("exit_hood", (2.6, BELT_Y, 0.22), (0.42, BELT_W + 0.16, 0.12), p["olive"], bevel=0.02)
    kit.rivets((2.4, BELT_Y - 0.33, 0.25), (2.8, BELT_Y - 0.33, 0.25), 5, (0, -1, 0))


def hydraulics(p):
    """Hydraulic power unit at the far end, hoses along the pit to the flap openers."""
    rig.box("hpu_slab", (-2.55, 0.42, 0.06), (0.8, 0.95, 0.12), p["concrete"], bevel=0.02)
    rig.cylinder("hpu_tank", (-2.8, 0.42, 0.28), (-2.3, 0.42, 0.28), 0.17, p["red"], verts=24)
    for x in (-2.75, -2.35):
        rig.box(f"hpu_saddle{x}", (x, 0.42, 0.17), (0.06, 0.34, 0.1), p["dark"])
    kit.motor((-2.55, 0.8, 0.26), axis="x", length=0.3, radius=0.1)
    kit.pipe([(-2.55, 0.42, 0.45), (-2.55, 0.42, 0.55), (-2.2, 0.42, 0.55), (-2.2, 0.85, 0.55)], 0.03, p["steel"])
    rig.cylinder("hpu_gauge", (-2.45, 0.24, 0.42), (-2.45, 0.22, 0.42), 0.04, p["glass"], verts=16)
    kit.lamp((-2.85, 0.85, 0.5), "green")
    kit.hose([(-2.2, 0.85, 0.55), (-1.6, 0.9, 0.2), (-1.2, 0.85, 0.22)], 0.03, p["rubber"], ribs_per_tile=18)
    # under the rail bridge to the far side
    kit.hose([(-2.2, 0.85, 0.55), (-1.4, 0.95, 0.1), (-0.9, 0.95, -0.45), (0.9, 0.95, -0.45), (1.2, 0.85, 0.22)], 0.03, p["rubber"],
             ribs_per_tile=18)
    # flap openers: yellow hydraulic arms either side of the track that swing up
    # against the wagon's flap levers while it unloads
    for sx in (-1, 1):
        for y in (-0.35, 0.35):
            rig.box(f"opener_base{sx}{y}", (sx * 1.15, y, 0.08), (0.16, 0.16, 0.1), p["dark"])
            hinge = kit.pivot(f"opener{sx}{y}", (sx * 1.15, y, 0.14))
            kit.attach(hinge,
                       rig.cylinder(f"opener_body{sx}{y}", (0, 0, 0), (0, 0, 0.32), 0.045, p["yellow"]),
                       rig.cylinder(f"opener_rod{sx}{y}", (0, 0, 0.32), (0, 0, 0.5), 0.022, p["chrome"]),
                       rig.box(f"opener_head{sx}{y}", (0, 0, 0.52), (0.1, 0.1, 0.04), p["dark"]))
            openers.append((hinge, sx))


def build():
    rig.reset()
    kit.reset()
    p = kit.palette()
    rig.layer("base")
    pit(p)
    extraction_belt(p)
    drive_house(p)
    hydraulics(p)
    rig.sun()
    rig.fill_light()
    rig.camera(8, 8, shift_y=0.2)


def set_openers(raised):
    """0 = folded flat outwards, 1 = standing up against the wagon."""
    for hinge, sx in openers:
        hinge.rotation_euler = (0, sx * (1 - raised) * 1.35, 0)


def pose(frame):
    t = frame / ANIM_FRAMES
    total = (BELT_FLAT_END - BELT_START) + math.hypot(BELT_END - BELT_FLAT_END, -DEPTH - 0.12)
    for obj, start, dz in moving:
        q = belt_point((start + t * 2 * CLEAT_SPACING / total) % 1.0)
        obj.location = (q[0], q[1], q[2] + dz)
    for pivot, step in spinning:
        pivot.rotation_euler[2] = step * frame
    for pivot in beacon:
        pivot.rotation_euler[2] = 2 * math.pi * t


def render_variant(out, v):
    d = os.path.join(out, f"v{v}")
    orient = (v - 1) / 4
    for o in ore:
        o.hide_render = True
    set_openers(0)
    rig.render_frames(d, [0], lambda i: orient, passes=("color",), samples=32, pose=pose)
    os.replace(os.path.join(d, "color_000.png"), os.path.join(d, "idle_000.png"))
    rig.render_frames(d, list(range(EXTEND_FRAMES)), lambda i: orient, passes=("color",), samples=32,
                      pose=lambda i: (pose(0), set_openers((i + 1) / EXTEND_FRAMES)))
    for i in range(EXTEND_FRAMES):
        os.replace(os.path.join(d, f"color_{i:03d}.png"), os.path.join(d, f"extend_{i:03d}.png"))
    for o in ore:
        o.hide_render = False
    rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("color",), samples=32,
                      pose=lambda i: (pose(i), set_openers(1)))
    for i in range(ANIM_FRAMES):
        os.replace(os.path.join(d, f"color_{i:03d}.png"), os.path.join(d, f"work_{i:03d}.png"))


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    variants = [int(x) for x in a[1:]] or [1, 2, 3, 4]
    build()
    for v in variants:
        render_variant(out, v)
