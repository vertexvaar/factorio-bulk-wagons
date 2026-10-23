"""E1 unloading pit: a concrete pit under the track with walkable gratings either
side, a hopper funnel and an extraction belt that climbs out at the belt port.

Run:  blender -b --factory-startup -P tools/blender/station_e1.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 2 tiles, rail north-south through x in [-1, 1], port east.
The whole pit is one ground sprite, drawn below the rails in game.

Passes per variant: idle_000 (still) and work_000..work_{ANIM_FRAMES-1} (belt running,
drive gear turning, warning beacon rotating).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rig  # noqa: E402

ANIM_FRAMES = 8
DEPTH = -0.7
BELT_Y = -0.35
BELT_W = 0.5
CLEAT_SPACING = 0.2
BELT_START, BELT_FLAT_END, BELT_END = -2.6, 1.6, 2.75  # x positions; the belt ramps up after BELT_FLAT_END

moving = []  # (object, start offset along the belt path, height above the belt)
spinning = []  # (pivot, step per frame)
beacon = []  # (pivot)
ore = []


def materials():
    return {
        "steel": rig.material("steel", (0.30, 0.31, 0.32), roughness=0.4, metallic=0.7, grime=0.3),
        "dark": rig.material("dark", (0.05, 0.05, 0.055), roughness=0.6, metallic=0.4, grime=0.3),
        "concrete": rig.material("concrete", (0.45, 0.43, 0.40), roughness=0.9, grime=0.45, scale=4, bump=0.4),
        "pit": rig.material("pit", (0.16, 0.15, 0.14), roughness=0.95, grime=0.5, scale=4, bump=0.5),
        "grate": rig.material("grate", (0.38, 0.39, 0.40), roughness=0.35, metallic=0.85, grime=0.25),
        "yellow": rig.material("yellow", (0.80, 0.58, 0.06), roughness=0.5, grime=0.35),
        "rubber": rig.material("rubber", (0.035, 0.035, 0.035), roughness=0.85, grime=0.2, bump=0.3),
        "roller": rig.material("roller", (0.55, 0.55, 0.55), roughness=0.3, metallic=0.9, grime=0.2),
        "motor": rig.material("motor", (0.20, 0.28, 0.36), roughness=0.45, metallic=0.3, grime=0.3),
        "brass": rig.material("brass", (0.62, 0.45, 0.16), roughness=0.3, metallic=0.9, grime=0.15),
        "ore": rig.material("ore", (0.32, 0.29, 0.26), roughness=1.0, grime=0.5, scale=14, bump=0.8),
        "beacon": rig.material("beacon", (1.0, 0.6, 0.1), emission=(1.0, 0.55, 0.1)),
    }


def belt_point(u):
    """Point on the belt path, u in [0, 1): flat along the bottom, then up the ramp."""
    flat = BELT_FLAT_END - BELT_START
    ramp = math.hypot(BELT_END - BELT_FLAT_END, -DEPTH - 0.15)
    d = u * (flat + ramp)
    if d <= flat:
        return (BELT_START + d, BELT_Y, DEPTH + 0.18)
    t = (d - flat) / ramp
    return (BELT_FLAT_END + t * (BELT_END - BELT_FLAT_END), BELT_Y, DEPTH + 0.18 + t * (-DEPTH - 0.15))


def pit(m):
    # concrete frame around the two side bays; the rail zone in the middle stays open
    for sx in (-1, 1):
        x0, x1 = sx * 1.0, sx * 3.0
        cx, w = (x0 + x1) / 2, abs(x1 - x0)
        rig.box(f"rim_n{sx}", (cx, 0.92, -0.05), (w, 0.16, 0.2), m["concrete"])
        rig.box(f"rim_s{sx}", (cx, -0.92, -0.05), (w, 0.16, 0.2), m["concrete"])
        rig.box(f"rim_end{sx}", (sx * 2.92, 0, -0.05), (0.16, 2.0, 0.2), m["concrete"])
        # yellow/black edge marking on the rims
        for k in range(int(w / 0.25)):
            x = min(x0, x1) + 0.12 + k * 0.25
            for y in (0.92, -0.92):
                rig.box(f"mark{sx}{k}{y}", (x, y, 0.055), (0.12, 0.15, 0.01), m["yellow"] if k % 2 else m["dark"], bevel=0)
    # funnel walls sloping down to the belt trough
    rig.mesh("funnel", [
        (-2.84, -0.84, 0), (2.84, -0.84, 0), (2.84, 0.84, 0), (-2.84, 0.84, 0),
        (-2.7, BELT_Y - 0.3, DEPTH), (BELT_FLAT_END, BELT_Y - 0.3, DEPTH), (BELT_FLAT_END, BELT_Y + 0.3, DEPTH), (-2.7, BELT_Y + 0.3, DEPTH),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0), (4, 7, 6, 5)], m["pit"])
    # rail bridge: two I-beams carrying the track over the pit, with cross girders
    for x in (-0.55, 0.55):
        rig.box(f"rail_beam{x}", (x, 0, -0.12), (0.14, 2.0, 0.22), m["steel"])
        rig.box(f"rail_beam_flange{x}", (x, 0, -0.02), (0.26, 2.0, 0.04), m["steel"])
    for y in (-0.7, 0.0, 0.7):
        rig.box(f"cross_girder{y}", (0, y, -0.3), (2.0, 0.1, 0.12), m["dark"])
    # walkable gratings over the side bays
    for sx in (-1, 1):
        cx = sx * 1.95
        rig.box(f"grate_frame{sx}", (cx, 0, -0.01), (1.85, 1.66, 0.03), m["grate"], bevel=0)
    for sx in (-1, 1):
        for k in range(15):
            x = sx * (1.08 + k * 0.125)
            rig.box(f"grate_bar{sx}{k}", (x, 0, 0.0), (0.025, 1.64, 0.05), m["grate"], bevel=0)
        for k in range(5):
            y = -0.7 + k * 0.35
            rig.box(f"grate_tie{sx}{k}", (sx * 1.95, y, 0.0), (1.85, 0.02, 0.045), m["grate"], bevel=0)
    # remove the solid frame plate under the bars so the funnel shows through
    for o in [o for o in rig.root().children if o.name.startswith("grate_frame")]:
        o.hide_render = True
    # ore residue at the bottom
    for x in (-2.0, -0.6, 0.7):
        rig.box(f"heap{x}", (x, BELT_Y + 0.25, DEPTH + 0.08), (0.7, 0.25, 0.12), m["ore"], bevel=0.05)


def extraction_belt(m):
    flat_len = BELT_FLAT_END - BELT_START
    rig.box("belt_flat", ((BELT_START + BELT_FLAT_END) / 2, BELT_Y, DEPTH + 0.15), (flat_len, BELT_W, 0.04), m["rubber"], bevel=0)
    ramp_mid = ((BELT_FLAT_END + BELT_END) / 2, BELT_Y, (DEPTH + 0.15 - 0.03) / 2 + 0.06)
    ramp_len = math.hypot(BELT_END - BELT_FLAT_END, -DEPTH - 0.15)
    ramp_angle = math.atan2(-DEPTH - 0.15, BELT_END - BELT_FLAT_END)
    rig.box("belt_ramp", ramp_mid, (ramp_len, BELT_W, 0.04), m["rubber"], bevel=0, rotation=(0, -ramp_angle, 0))
    for s in (-1, 1):
        rig.box(f"skirt_flat{s}", ((BELT_START + BELT_FLAT_END) / 2, BELT_Y + s * (BELT_W / 2 + 0.04), DEPTH + 0.22), (flat_len, 0.05, 0.16),
                m["steel"])
        rig.box(f"skirt_ramp{s}", (ramp_mid[0], BELT_Y + s * (BELT_W / 2 + 0.04), ramp_mid[2] + 0.07), (ramp_len, 0.05, 0.16), m["steel"],
                rotation=(0, -ramp_angle, 0))
    count = int((flat_len + ramp_len) / CLEAT_SPACING)
    for k in range(count):
        u = k / count
        p = belt_point(u)
        cleat = rig.box(f"cleat{k}", p, (0.025, BELT_W - 0.06, 0.02), m["dark"], bevel=0)
        moving.append((cleat, u, 0.0))
        if k % 2 == 0:
            heap = rig.box(f"ore{k}", p, (0.1, 0.22, 0.05), m["ore"], bevel=0.02)
            moving.append((heap, u + 0.5 / count, 0.03))
            ore.append(heap)
    # drive at the port end: motor, gearbox and an open gear pair
    rig.box("drive_base", (2.55, 0.45, 0.1), (0.7, 0.6, 0.2), m["concrete"])
    rig.cylinder("drive_motor", (2.3, 0.45, 0.42), (2.85, 0.45, 0.42), 0.17, m["motor"], verts=24)
    rig.box("drive_gearbox", (2.55, 0.1, 0.35), (0.42, 0.25, 0.5), m["yellow"])
    big = rig.gear("drive_gear", (2.55, -0.05, 0.38), 0.16, 0.04, 14, m["brass"], axis="y")
    spinning.append((big, 2 * math.pi / 14))
    # warning beacon on a post
    rig.cylinder("beacon_post", (2.85, 0.85, 0.0), (2.85, 0.85, 0.6), 0.025, m["steel"])
    rig.cylinder("beacon_glass", (2.85, 0.85, 0.6), (2.85, 0.85, 0.72), 0.06, m["beacon"], verts=16)
    pivot = rig.gear("beacon_reflector", (2.85, 0.85, 0.66), 0.035, 0.1, 2, m["roller"], axis="z")
    beacon.append(pivot)


def build():
    rig.reset()
    m = materials()
    rig.layer("base")
    pit(m)
    extraction_belt(m)
    rig.sun()
    rig.fill_light()
    rig.camera(8, 5, shift_y=0.3)


def pose(frame):
    t = frame / ANIM_FRAMES
    total = (BELT_FLAT_END - BELT_START) + math.hypot(BELT_END - BELT_FLAT_END, -DEPTH - 0.15)
    for obj, start, dz in moving:
        p = belt_point((start + t * 2 * CLEAT_SPACING / total) % 1.0)
        obj.location = (p[0], p[1], p[2] + dz)
    for pivot, step in spinning:
        pivot.rotation_euler[2] = step * frame
    for pivot in beacon:
        pivot.rotation_euler[2] = 2 * math.pi * t


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    variants = [int(x) for x in a[1:]] or [1, 2, 3, 4]
    build()
    for v in variants:
        d = os.path.join(out, f"v{v}")
        orient = (v - 1) / 4
        for o in ore:
            o.hide_render = True
        rig.render_frames(d, [0], lambda i: orient, passes=("color",), samples=32, pose=pose)
        os.replace(os.path.join(d, "color_000.png"), os.path.join(d, "idle_000.png"))
        for o in ore:
            o.hide_render = False
        rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("color",), samples=32, pose=pose)
        for i in range(ANIM_FRAMES):
            os.replace(os.path.join(d, f"color_{i:03d}.png"), os.path.join(d, f"work_{i:03d}.png"))
