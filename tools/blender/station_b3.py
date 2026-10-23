"""B3 belt loader: an inclined belt conveyor on a lattice tower, discharging through
a hood and chute into the wagon compartment below.

Run:  blender -b --factory-startup -P tools/blender/station_b3.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 2 tiles, rail runs north-south through x in [-1, 1],
belt port at the east end (x = 2.5, y = -0.5). Variants 2-4 are the same model turned
by 90 degree steps clockwise.

Passes per variant: back (behind/below trains), top (overhead and in front of trains,
animated: ANIM_FRAMES frames of running belt and spinning gears) and shadow.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rig  # noqa: E402

ANIM_FRAMES = 8
CLEAT_SPACING = 0.16
HEAD = (0.05, -0.3, 2.85)  # head pulley centre, above the rail
TAIL = (2.45, -0.3, 0.42)  # tail pulley in the boot at the port
BELT_W = 0.56

animated = []  # (object, kind, data) moved per frame
ore = []  # only shown in the working animation


def materials():
    return {
        "steel": rig.material("steel", (0.30, 0.31, 0.32), roughness=0.4, metallic=0.7, grime=0.3),
        "dark": rig.material("dark", (0.06, 0.06, 0.065), roughness=0.5, metallic=0.5, grime=0.2),
        "concrete": rig.material("concrete", (0.42, 0.40, 0.37), roughness=0.9, grime=0.4, scale=5, bump=0.4),
        "yellow": rig.material("yellow", (0.80, 0.58, 0.06), roughness=0.5, grime=0.35),
        "hood": rig.material("hood", (0.48, 0.17, 0.06), roughness=0.5, grime=0.35, scale=3),
        "rubber": rig.material("rubber", (0.035, 0.035, 0.035), roughness=0.85, grime=0.2, bump=0.3),
        "roller": rig.material("roller", (0.55, 0.55, 0.55), roughness=0.3, metallic=0.9, grime=0.2),
        "motor": rig.material("motor", (0.20, 0.28, 0.36), roughness=0.45, metallic=0.3, grime=0.3),
        "brass": rig.material("brass", (0.62, 0.45, 0.16), roughness=0.3, metallic=0.9, grime=0.15),
        "lamp": rig.material("lamp", (1.0, 0.7, 0.3), emission=(1.0, 0.55, 0.15)),
    }


def lerp(a, b, t):
    return tuple(a[i] + t * (b[i] - a[i]) for i in range(3))


def footing(name, x, y, m, size=(0.36, 0.36)):
    rig.box(name, (x, y, 0.06), (size[0], size[1], 0.12), m["concrete"])
    for dx in (-1, 1):
        for dy in (-1, 1):
            rig.cylinder(f"{name}_bolt{dx}{dy}", (x + dx * size[0] * 0.32, y + dy * size[1] * 0.32, 0.1),
                         (x + dx * size[0] * 0.32, y + dy * size[1] * 0.32, 0.16), 0.02, m["dark"], verts=6)


def tower(m):
    """Lattice tower west of the track carrying the head of the conveyor."""
    xs, ys, z_top = (-2.6, -1.35), (-0.75, 0.75), 2.95
    for x in xs:
        for y in ys:
            footing(f"foot{x}{y}", x, y, m)
            rig.box(f"leg{x}{y}", (x, y, z_top / 2 + 0.06), (0.12, 0.12, z_top - 0.1), m["steel"])
    for z in (0.9, 1.9):
        for y in ys:
            rig.box(f"brace_x{z}{y}", ((xs[0] + xs[1]) / 2, y, z), (xs[1] - xs[0], 0.07, 0.07), m["steel"])
        for x in xs:
            rig.box(f"brace_y{z}{x}", (x, 0, z), (0.07, ys[1] - ys[0], 0.07), m["steel"])
    for (z0, z1) in ((0.12, 0.9), (0.9, 1.9), (1.9, z_top)):
        for y in ys:
            rig.cylinder(f"diag{z0}{y}", (xs[0], y, z0), (xs[1], y, z1), 0.025, m["steel"], verts=6)
        for x in xs:
            rig.cylinder(f"diagy{z0}{x}", (x, ys[0], z1), (x, ys[1], z0), 0.025, m["steel"], verts=6)
    # ladder up the west face
    for y in (-0.2, 0.2):
        rig.cylinder(f"ladder{y}", (xs[0] - 0.12, y, 0.1), (xs[0] - 0.12, y, z_top), 0.016, m["yellow"])
    for k in range(12):
        z = 0.25 + k * 0.23
        rig.cylinder(f"rung{k}", (xs[0] - 0.12, -0.2, z), (xs[0] - 0.12, 0.2, z), 0.012, m["yellow"])
    # control cabinet at the foot with a status lamp
    rig.box("cabinet", (-1.95, -0.62, 0.4), (0.45, 0.28, 0.7), m["motor"])
    rig.box("cabinet_door", (-1.95, -0.77, 0.42), (0.38, 0.02, 0.6), m["steel"])
    rig.box("cabinet_lamp", (-1.8, -0.79, 0.68), (0.05, 0.02, 0.05), m["lamp"], bevel=0)


def platform_and_drive(m):
    """Platform on top of the tower with railing, motor, gearbox and exposed gears."""
    rig.layer("top")
    z = 2.95
    rig.box("platform", (-1.6, 0, z + 0.04), (2.0, 1.75, 0.08), m["steel"])
    for k in range(9):
        rig.box(f"grating{k}", (-2.5 + k * 0.22, 0, z + 0.085), (0.02, 1.7, 0.01), m["dark"], bevel=0)
    for (p, q) in (((-2.6, -0.85), (-2.6, 0.85)), ((-2.6, 0.85), (-0.7, 0.85))):
        rig.tube_path(f"railing{p}", [(p[0], p[1], z + 0.08), (p[0], p[1], z + 0.55), (q[0], q[1], z + 0.55), (q[0], q[1], z + 0.08)],
                      0.018, m["yellow"])
    # cross beams over the track to the head
    for y in (-0.72, 0.12):
        rig.box(f"beam{y}", (-0.55, y, z - 0.02), (2.1, 0.12, 0.16), m["steel"])
    # electric motor + gearbox driving the head pulley through a gear pair
    rig.cylinder("motor", (-1.9, -0.45, z + 0.32), (-1.2, -0.45, z + 0.32), 0.2, m["motor"], verts=24)
    for k in range(8):
        a = 2 * math.pi * k / 8
        rig.box(f"motor_fin{k}", (-1.55, -0.45 + math.cos(a) * 0.2, z + 0.32 + math.sin(a) * 0.2), (0.6, 0.03, 0.03), m["motor"], bevel=0,
                rotation=(a, 0, 0))
    rig.box("gearbox", (-0.95, -0.45, z + 0.3), (0.4, 0.36, 0.4), m["yellow"])
    small = rig.gear("gear_small", (-0.95, -0.66, z + 0.42), 0.12, 0.05, 10, m["brass"], axis="y")
    big = rig.gear("gear_big", (-0.95, -0.66, z + 0.12), 0.2, 0.05, 16, m["brass"], axis="y")
    animated.append((small, "spin", 2 * math.pi / 10))
    animated.append((big, "spin", -2 * math.pi / 16))
    rig.cylinder("drive_shaft", (-0.95, -0.3, HEAD[2]), (HEAD[0], -0.3, HEAD[2]), 0.035, m["roller"])
    rig.box("warning_light", (-0.7, 0.8, z + 0.65), (0.06, 0.06, 0.06), m["lamp"], bevel=0)
    rig.cylinder("warning_post", (-0.7, 0.8, z + 0.08), (-0.7, 0.8, z + 0.62), 0.015, m["steel"])


def conveyor(m):
    """Inclined trough conveyor from the boot at the port up to the head over the rail."""
    rig.layer("top")
    dx, dz = HEAD[0] - TAIL[0], HEAD[2] - TAIL[2]
    length = math.hypot(dx, dz)
    angle = math.atan2(dz, -dx)  # rise towards -x
    mid = lerp(TAIL, HEAD, 0.5)
    # side stringers
    for s in (-1, 1):
        rig.box(f"stringer{s}", (mid[0], TAIL[1] + s * (BELT_W / 2 + 0.06), mid[2] - 0.02), (length + 0.2, 0.06, 0.16), m["steel"],
                rotation=(0, angle, 0))
        # cover hoods over the belt every few segments
    # belt surface (top run)
    rig.box("belt", (mid[0], TAIL[1], mid[2] + 0.07), (length, BELT_W, 0.03), m["rubber"], bevel=0, rotation=(0, angle, 0))
    # idler rollers under the belt
    n = int(length / 0.35)
    for k in range(1, n):
        p = lerp(TAIL, HEAD, k / n)
        rig.cylinder(f"idler{k}", (p[0], TAIL[1] - BELT_W / 2, p[2] + 0.03), (p[0], TAIL[1] + BELT_W / 2, p[2] + 0.03), 0.035, m["roller"],
                     verts=12)
    # cleats on the belt, moved along the belt per frame
    count = int(length / CLEAT_SPACING)
    for k in range(count):
        t = k / count
        p = lerp(TAIL, HEAD, t)
        cleat = rig.box(f"cleat{k}", (p[0], TAIL[1], p[2] + 0.095), (0.025, BELT_W - 0.06, 0.02), m["dark"], bevel=0,
                        rotation=(0, angle, 0))
        animated.append((cleat, "slide", (t, length, 0.095)))
    # ore on the belt: little heaps every other cleat
    for k in range(0, count, 2):
        t = (k + 0.5) / count
        p = lerp(TAIL, HEAD, t)
        heap = rig.box(f"ore{k}", (p[0], TAIL[1], p[2] + 0.11), (0.08, 0.18, 0.04), m["concrete"], bevel=0.02,
                       rotation=(0, angle, 0))
        animated.append((heap, "slide", (t, length, 0.11)))
        ore.append(heap)
    # head pulley with hood and chute into the wagon
    rig.cylinder("head_pulley", (HEAD[0], TAIL[1] - BELT_W / 2, HEAD[2]), (HEAD[0], TAIL[1] + BELT_W / 2, HEAD[2]), 0.12, m["roller"])
    rig.mesh("hood", [
        (-0.42, -0.72, 2.55), (0.42, -0.72, 2.55), (0.42, 0.12, 2.55), (-0.42, 0.12, 2.55),
        (-0.3, -0.72, 3.18), (0.32, -0.72, 3.18), (0.32, 0.12, 3.18), (-0.3, 0.12, 3.18),
    ], [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], m["hood"], bevel=0.015)
    rig.mesh("chute", [
        (-0.36, -0.66, 2.55), (0.36, -0.66, 2.55), (0.36, 0.06, 2.55), (-0.36, 0.06, 2.55),
        (-0.2, -0.48, 2.12), (0.2, -0.48, 2.12), (0.2, -0.12, 2.12), (-0.2, -0.12, 2.12),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], m["hood"], bevel=0.01)
    rig.box("chute_lip", (0, -0.3, 2.1), (0.44, 0.4, 0.04), m["dark"])
    # hazard stripes on the hood
    for k in range(6):
        rig.box(f"stripe{k}", (-0.3 + k * 0.12, -0.735, 2.62), (0.05, 0.01, 0.1), m["yellow"], bevel=0, rotation=(0, 0.6, 0))


def boot_and_support(m):
    rig.layer("base")
    # boot housing with the tail pulley, fed by the belt arriving from the east
    rig.box("boot", (2.45, -0.3, 0.28), (0.8, BELT_W + 0.2, 0.5), m["steel"])
    rig.mesh("boot_funnel", [
        (2.15, -0.7, 0.53), (2.95, -0.7, 0.53), (2.95, 0.1, 0.53), (2.15, 0.1, 0.53),
        (2.25, -0.55, 0.72), (2.95, -0.55, 0.72), (2.95, -0.05, 0.72), (2.25, -0.05, 0.72),
    ], [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["yellow"], bevel=0.01)
    footing("boot_foot", 2.45, 0.55, m, (0.5, 0.4))
    rig.box("takeup", (2.45, 0.55, 0.35), (0.22, 0.22, 0.45), m["dark"])
    # A-frame supporting the incline east of the track
    p = lerp(TAIL, HEAD, 0.45)
    for y in (-0.75, 0.15):
        footing(f"aframe_foot{y}", 1.5, y, m, (0.3, 0.3))
        rig.cylinder(f"aframe{y}", (1.5, y, 0.12), (p[0], TAIL[1] + (y + 0.3) * 0.5, p[2] - 0.08), 0.045, m["steel"], verts=8)
    rig.cylinder("aframe_tie", (1.5, -0.75, 0.6), (1.5, 0.15, 0.6), 0.03, m["steel"], verts=8)


def build():
    rig.reset()
    m = materials()
    rig.layer("base")
    tower(m)
    boot_and_support(m)
    conveyor(m)
    platform_and_drive(m)
    rig.layer("base")
    rig.sun()
    rig.fill_light()
    rig.camera(9, 10, shift_y=1.8)


def pose(frame):
    t = frame / ANIM_FRAMES
    for obj, kind, data in animated:
        if kind == "spin":
            obj.rotation_euler[2] = data * frame
        elif kind == "slide":
            start, length, dz = data
            p = lerp(TAIL, HEAD, (start + t * 2 * CLEAT_SPACING / length) % 1.0)
            obj.location = (p[0], obj.location[1], p[2] + dz)


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
        rig.render_frames(d, [0], lambda i: orient, passes=("base", "shadow", "top"), samples=32, pose=pose)
        os.replace(os.path.join(d, "top_000.png"), os.path.join(d, "idle_000.png"))
        for o in ore:
            o.hide_render = False
        rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("top",), samples=32, pose=pose)
