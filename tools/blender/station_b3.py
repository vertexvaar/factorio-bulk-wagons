"""B3 belt loader in the 2.1 style: a covered belt gallery on a truss climbs from the
boot at the belt port to a head house over the track; a ribbed telescopic spout
drops from the head house into the wagon compartment. A braced tower with a caged
ladder and a railed platform carries the head house.

Run:  blender -b --factory-startup -P tools/blender/station_b3.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 2 tiles, rail north-south through x in [-1, 1], port east
at (2.5, -0.5). Variants 2-4 are the same model turned by 90 degree steps clockwise.

Renders per variant: base, shadow, idle (spout up), extend_000..007 (spout lowers onto
the wagon, played once) and work_000..007 (belt running, drive turning, spout down).
Each comes with a *_mask twin for the station colour; top_static_000 is the idle top
without its moving parts, for the window preview.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import rig  # noqa: E402

ANIM_FRAMES = 8
EXTEND_FRAMES = 8
CLEAT_SPACING = 0.16
HEAD = (0.05, -0.3, 2.75)  # head pulley centre, above the rail
TAIL = (2.4, -0.3, 0.5)  # tail pulley in the boot at the port
BELT_W = 0.5
SPOUT_TOP, SPOUT_UP, SPOUT_DOWN = 2.4, 2.25, 2.0  # bellows spout: top fixed, lower edge raised/lowered

moving = []
spinning = []
bellows = []  # (object, fraction of the travel)
ore = []


def lerp(a, b, t):
    return tuple(a[i] + t * (b[i] - a[i]) for i in range(3))


def tower(p):
    """Braced tower west of the track: I-beam columns, cross bracing, caged ladder."""
    xs, ys, z_top = (-2.55, -1.35), (-0.72, 0.72), 2.6
    for x in xs:
        for y in ys:
            kit.footing(x, y)
            kit.ibeam((x, y, 0.15), (x, y, z_top), size=0.13)
    for z in (0.95, 1.8):
        for y in ys:
            kit.ibeam((xs[0], y, z), (xs[1], y, z), size=0.09)
        for x in xs:
            kit.ibeam((x, ys[0], z), (x, ys[1], z), size=0.09)
    for (z0, z1) in ((0.2, 0.95), (0.95, 1.8), (1.8, z_top)):
        for y in ys:
            rig.cylinder(f"xa{z0}{y}", (xs[0], y, z0), (xs[1], y, z1), 0.022, p["steel"], verts=6)
            rig.cylinder(f"xb{z0}{y}", (xs[0], y, z1), (xs[1], y, z0), 0.022, p["steel"], verts=6)
        for x in xs:
            rig.cylinder(f"ya{z0}{x}", (x, ys[0], z0), (x, ys[1], z1), 0.022, p["steel"], verts=6)
    kit.ladder((xs[0] - 0.14, 0.0, 0.1), (xs[0] - 0.14, 0.0, z_top), cage=True)
    kit.cabinet((-1.95, -0.6, 0.45), (0.45, 0.22, 0.7), facing="-y")
    kit.cable([(-1.8, -0.6, 0.82), (-1.4, -0.6, 1.2), (-1.38, -0.65, 2.5)], "red")
    kit.cable([(-1.9, -0.6, 0.82), (-1.36, -0.55, 1.3), (-1.36, -0.6, 2.5)], "blue")


def head_house(p):
    """Platform on the tower, head house over the rail, drive with open gears."""
    rig.layer("top")
    z = 2.6
    kit.plate((-1.55, 0, z + 0.03), (2.2, 1.7, 0.06), p["plate"], panels=4)
    kit.grating((-1.95, 0.35, z + 0.07), (1.2, 0.8))
    kit.handrail([(-2.65, -0.85, z + 0.06), (-2.65, 0.85, z + 0.06), (-0.5, 0.85, z + 0.06)])
    # beams stop short of the track so the spout stays in view; the head house hangs
    # from the gallery truss and two struts
    for y in (-0.72, 0.12):
        kit.ibeam((-2.6, y, z - 0.08), (-0.6, y, z - 0.08), size=0.16)
    for y in (-0.62, 0.02):
        rig.cylinder(f"strut{y}", (-0.6, y, z - 0.08), (-0.28, y, 2.75), 0.03, p["steel"], verts=8)
    # head house: riveted box around the head pulley
    hx, hy, hz = 0.05, -0.3, 2.85
    rig.box("head_house", (hx, hy, hz), (0.7, 0.8, 0.62), p["olive"], bevel=0.025)
    rig.box("head_roof", (hx, hy, hz + 0.33), (0.78, 0.88, 0.05), p["dark"], bevel=0.01)
    for (a, b, nrm) in (((hx - 0.33, hy - 0.41, hz + 0.27), (hx + 0.33, hy - 0.41, hz + 0.27), (0, -1, 0)),
                        ((hx - 0.33, hy - 0.41, hz - 0.27), (hx + 0.33, hy - 0.41, hz - 0.27), (0, -1, 0)),
                        ((hx - 0.36, hy - 0.37, hz - 0.27), (hx - 0.36, hy - 0.37, hz + 0.27), (-1, 0, 0))):
        kit.rivets(a, b, 7, nrm)
    rig.box("head_door", (hx - 0.1, hy - 0.41, hz - 0.05), (0.26, 0.015, 0.4), p["dark"], bevel=0.005)
    kit.hazard((hx, hy - 0.42, hz - 0.29), (0.68, 0.01, 0.06), stripes=6)
    kit.fan((hx + 0.12, hy, hz + 0.36), radius=0.14, axis="z")
    kit.lamp((hx + 0.3, hy - 0.38, hz + 0.4), "amber")
    # drive on the platform: motor, gearbox and an open gear pair
    kit.motor((-0.95, -0.55, z + 0.22), axis="x", length=0.42, radius=0.15)
    kit.gearbox((-0.55, -0.55, z + 0.22), (0.3, 0.36, 0.36))
    big = rig.gear("gear_big", (-0.55, -0.76, z + 0.32), 0.15, 0.04, 16, p["brass"], axis="y")
    small = rig.gear("gear_small", (-0.32, -0.76, z + 0.48), 0.08, 0.04, 9, p["brass"], axis="y")
    spinning.append((big, 2 * math.pi / 16))
    spinning.append((small, -2 * math.pi / 9))
    rig.cylinder("drive_shaft", (-0.4, -0.3, HEAD[2]), (hx - 0.36, -0.3, HEAD[2]), 0.035, p["chrome"])
    kit.pipe([(-1.3, 0.6, z + 0.07), (-1.3, 0.6, z + 0.5), (-0.4, 0.6, z + 0.5)], 0.035, p["blue"])
    # bellows spout under the head house
    rig.box("spout_collar", (hx, hy, SPOUT_TOP + 0.05), (0.42, 0.42, 0.1), p["dark"], bevel=0.01)
    rings = 7
    for k in range(rings):
        frac = (k + 1) / rings
        z0 = SPOUT_TOP - frac * (SPOUT_TOP - SPOUT_UP)
        ring = rig.torus(f"bellow{k}", (hx, hy, z0), 0.17, 0.035, p["rubber"])
        bellows.append((ring, frac))
    nozzle = rig.cylinder("spout_nozzle", (hx, hy, SPOUT_UP - 0.08), (hx, hy, SPOUT_UP), 0.15, p["steel"], verts=20)
    bellows.append((nozzle, 1.0))
    lip = rig.torus("spout_lip", (hx, hy, SPOUT_UP - 0.08), 0.16, 0.02, p["yellow"])
    bellows.append((lip, 1.0))


def gallery(p):
    """Inclined belt gallery: truss underneath, cover sheets, walkway with handrail."""
    rig.layer("top")
    dx, dz = HEAD[0] - TAIL[0], HEAD[2] - TAIL[2]
    length = math.hypot(dx, dz)
    angle = math.atan2(dz, -dx)
    mid = lerp(TAIL, HEAD, 0.5)
    kit.lattice((TAIL[0] - 0.1, TAIL[1], TAIL[2] - 0.22), (HEAD[0] + 0.3, HEAD[1], HEAD[2] - 0.22), 0.62, 0.22, 7)
    for s in (-1, 1):
        rig.box(f"stringer{s}", (mid[0], TAIL[1] + s * (BELT_W / 2 + 0.06), mid[2] - 0.02), (length, 0.05, 0.14), p["steel"],
                rotation=(0, angle, 0))
    rig.box("belt", (mid[0], TAIL[1], mid[2] + 0.06), (length, BELT_W, 0.03), p["rubber"], bevel=0, rotation=(0, angle, 0))
    n = int(length / 0.3)
    for k in range(1, n):
        q = lerp(TAIL, HEAD, k / n)
        rig.cylinder(f"idler{k}", (q[0], TAIL[1] - BELT_W / 2, q[2] + 0.02), (q[0], TAIL[1] + BELT_W / 2, q[2] + 0.02), 0.03, p["chrome"],
                     verts=10)
    # cover sheets on every other bay, the gaps show the running belt
    for k in range(0, n, 2):
        q = lerp(TAIL, HEAD, (k + 0.5) / n)
        rig.box(f"cover{k}", (q[0], TAIL[1], q[2] + 0.18), (length / n * 0.95, BELT_W + 0.14, 0.04), p["olive"], bevel=0.015,
                rotation=(0, angle, 0))
    # walkway with handrail on the south side
    wy = TAIL[1] - BELT_W / 2 - 0.3
    rig.box("walkway", (mid[0], wy, mid[2] - 0.08), (length, 0.26, 0.03), p["steel"], bevel=0.005, rotation=(0, angle, 0))
    kit.handrail([(TAIL[0], wy - 0.12, TAIL[2] - 0.06), (HEAD[0] + 0.35, wy - 0.12, HEAD[2] - 0.06)], height=0.4, posts_every=0.5)
    count = int(length / CLEAT_SPACING)
    for k in range(count):
        t = k / count
        q = lerp(TAIL, HEAD, t)
        cleat = rig.box(f"cleat{k}", (q[0], TAIL[1], q[2] + 0.085), (0.025, BELT_W - 0.06, 0.02), p["dark"], bevel=0,
                        rotation=(0, angle, 0))
        moving.append((cleat, t, length, 0.085))
        if k % 2 == 0:
            heap = rig.box(f"ore{k}", (q[0], TAIL[1], q[2] + 0.1), (0.08, 0.18, 0.04), p["concrete"], bevel=0.02, rotation=(0, angle, 0))
            moving.append((heap, t + 0.5 / count, length, 0.1))
            ore.append(heap)


def boot(p):
    """Boot at the belt port: receiving hopper, tail pulley, take-up with counterweight."""
    rig.layer("base")
    kit.footing(2.45, -0.3, (0.9, 0.8))
    rig.box("boot", (2.45, -0.3, 0.4), (0.78, 0.66, 0.5), p["olive"], bevel=0.02)
    kit.rivets((2.08, -0.64, 0.6), (2.82, -0.64, 0.6), 7, (0, -1, 0))
    kit.rivets((2.08, -0.64, 0.2), (2.82, -0.64, 0.2), 7, (0, -1, 0))
    rig.mesh("boot_hopper", [
        (2.1, -0.65, 0.66), (2.95, -0.65, 0.66), (2.95, 0.05, 0.66), (2.1, 0.05, 0.66),
        (2.2, -0.5, 0.86), (2.95, -0.5, 0.86), (2.95, -0.1, 0.86), (2.2, -0.1, 0.86),
    ], [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], p["yellow"], bevel=0.01)
    rig.cylinder("tail_pulley", (2.45, -0.62, 0.5), (2.45, 0.02, 0.5), 0.1, p["chrome"])
    # gravity take-up tower with counterweight north of the boot
    for y in (0.35, 0.75):
        kit.ibeam((2.3, y, 0.1), (2.3, y, 1.1), size=0.08)
        kit.ibeam((2.65, y, 0.1), (2.65, y, 1.1), size=0.08)
    rig.box("counterweight", (2.47, 0.55, 0.7), (0.3, 0.32, 0.32), p["concrete"], bevel=0.02)
    kit.hazard((2.47, 0.38, 0.7), (0.3, 0.01, 0.3), stripes=4)
    # A-frame under the gallery
    q = lerp(TAIL, HEAD, 0.42)
    for y in (-0.72, 0.12):
        kit.footing(1.5, y, (0.3, 0.3))
        kit.ibeam((1.5, y, 0.14), (q[0], TAIL[1] + (y + 0.3) * 0.45, q[2] - 0.32), size=0.1)


def build():
    rig.reset()
    kit.reset()
    p = kit.palette()
    rig.layer("base")
    tower(p)
    boot(p)
    gallery(p)
    head_house(p)
    rig.layer("base")
    rig.sun()
    rig.fill_light()
    rig.camera(9, 10, shift_y=1.8)


def set_spout(extension):
    drop = (SPOUT_UP - SPOUT_DOWN) * extension
    for obj, frac in bellows:
        z0 = obj.get("z0")
        if z0 is None:
            obj["z0"] = z0 = obj.location.z
        obj.location.z = z0 - drop * frac


def pose(frame):
    t = frame / ANIM_FRAMES
    for obj, start, length, dz in moving:
        q = lerp(TAIL, HEAD, (start + t * 2 * CLEAT_SPACING / length) % 1.0)
        obj.location = (q[0], obj.location[1], q[2] + dz)
    for pivot, step in spinning:
        pivot.rotation_euler[2] = step * frame


def render_variant(out, v):
    d = os.path.join(out, f"v{v}")
    orient = (v - 1) / 4
    for o in ore:
        o.hide_render = True
    set_spout(0)
    pose(0)
    rig.mark_moving([obj for obj, _ in bellows] + [pivot for pivot, _ in spinning] + [m[0] for m in moving])
    rig.render_frames(d, [0], lambda i: orient, passes=("base", "base_mask", "shadow", "top", "top_mask", "top_static"),
                      samples=32)
    rig.rename(d, "top", "idle", 1)
    rig.render_frames(d, list(range(EXTEND_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: set_spout((i + 1) / EXTEND_FRAMES))
    rig.rename(d, "top", "extend", EXTEND_FRAMES)
    for o in ore:
        o.hide_render = False
    rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: (set_spout(1), pose(i)))
    rig.rename(d, "top", "work", ANIM_FRAMES)


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    variants = [int(x) for x in a[1:]] or [1, 2, 3, 4]
    build()
    for v in variants:
        render_variant(out, v)
