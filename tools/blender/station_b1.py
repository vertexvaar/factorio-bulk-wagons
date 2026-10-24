"""B1 portal silo in the 2.1 style: a riveted silo bin on a braced steel portal over
the track, filled by a bucket elevator at the belt port and emptied through a slide
gate and a bellows chute that lowers onto the wagon.

Run:  blender -b --factory-startup -P tools/blender/station_b1.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 2 tiles, rail north-south through x in [-1, 1], port east.

Renders per variant: base, shadow, idle (chute up), extend_000..007 (chute lowers onto
the wagon, played once) and work_000..007 (elevator drive turning, chute down).
Each comes with a *_mask twin for the station colour.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import rig  # noqa: E402

ANIM_FRAMES = 8
EXTEND_FRAMES = 8
LEG_X, LEG_Y = 1.62, 0.78
PORTAL_Z = 3.0
BIN_BOTTOM, BIN_TOP = 3.5, 4.7
BIN_Y = 0.22  # the bin sits to the north so the chute stays visible in front of it
HW, HD = 1.15, 0.72
CHUTE_Y = -0.42
CHUTE_TOP, CHUTE_UP, CHUTE_DOWN = 3.0, 2.75, 2.06

spinning = []
bellows = []


def portal(p):
    rig.layer("base")
    for x in (-LEG_X, LEG_X):
        for y in (-LEG_Y, LEG_Y):
            kit.footing(x, y, (0.46, 0.46), 0.16)
            kit.ibeam((x, y, 0.18), (x, y, PORTAL_Z - 0.1), size=0.2)
            for k in range(4):  # impact guard facing the track
                rig.box(f"guard{x}{y}{k}", (x - math.copysign(0.14, x), y, 0.3 + k * 0.13), (0.02, 0.24, 0.11),
                        p["yellow"] if k % 2 == 0 else p["dark"], bevel=0)
        rig.cylinder(f"xbrace_a{x}", (x, -LEG_Y, 0.45), (x, LEG_Y, 2.3), 0.03, p["steel"], verts=6)
        rig.cylinder(f"xbrace_b{x}", (x, LEG_Y, 0.45), (x, -LEG_Y, 2.3), 0.03, p["steel"], verts=6)
        kit.ibeam((x, -LEG_Y, 2.4), (x, LEG_Y, 2.4), size=0.1)
    kit.ladder((-LEG_X - 0.2, 0.25, 0.15), (-LEG_X - 0.2, 0.25, PORTAL_Z + 0.1), cage=True)
    kit.cabinet((-2.3, -0.55, 0.42), (0.45, 0.22, 0.66), facing="-y")
    kit.cable([(-2.2, -0.55, 0.76), (-1.9, -0.6, 1.3), (-1.75, -0.7, 2.9)], "red")
    kit.cable([(-2.35, -0.55, 0.76), (-1.95, -0.5, 1.2), (-1.78, -0.62, 2.9)], "green")


def bin_and_chute(p):
    rig.layer("top")
    for y in (-LEG_Y, LEG_Y):
        kit.ibeam((-LEG_X - 0.15, y, PORTAL_Z), (LEG_X + 0.15, y, PORTAL_Z), size=0.28)
    for x in (-LEG_X, LEG_X):
        kit.ibeam((x, -LEG_Y - 0.1, PORTAL_Z), (x, LEG_Y + 0.1, PORTAL_Z), size=0.24)
    # walkways left and right of the chute opening, railed all round
    for sx in (-1, 1):
        kit.grating((sx * (LEG_X - 0.12), 0, PORTAL_Z + 0.17), (0.75, 2 * LEG_Y + 0.35))
    kit.grating((0, LEG_Y - 0.02, PORTAL_Z + 0.17), (2 * LEG_X - 0.9, 0.42))
    x0, x1, y0, y1 = -LEG_X - 0.5, LEG_X + 0.5, -LEG_Y - 0.17, LEG_Y + 0.17
    kit.handrail([(x0, y0, PORTAL_Z + 0.19), (x1, y0, PORTAL_Z + 0.19), (x1, y1, PORTAL_Z + 0.19), (x0, y1, PORTAL_Z + 0.19),
                  (x0, y0, PORTAL_Z + 0.19)], height=0.5)
    # the bin: riveted plate walls, ring stiffeners, roof
    zc = (BIN_BOTTOM + BIN_TOP) / 2
    h = BIN_TOP - BIN_BOTTOM
    kit.plate((0, BIN_Y - HD, zc), (2 * HW, 0.05, h), p["olive"], axis="y")
    kit.plate((0, BIN_Y + HD, zc), (2 * HW, 0.05, h), p["olive"], axis="y")
    kit.plate((-HW, BIN_Y, zc), (0.05, 2 * HD, h), p["olive"], axis="x")
    kit.plate((HW, BIN_Y, zc), (0.05, 2 * HD, h), p["olive"], axis="x")
    for z in (BIN_BOTTOM + 0.35, BIN_BOTTOM + 0.8):
        for y in (BIN_Y - HD - 0.05, BIN_Y + HD + 0.05):
            kit.ibeam((-HW - 0.05, y, z), (HW + 0.05, y, z), size=0.07)
    for k in range(5):
        x = -HW + 0.25 + k * (2 * HW - 0.5) / 4
        rig.box(f"bin_post{k}", (x, BIN_Y - HD - 0.04, zc), (0.06, 0.05, h), p["steel"], bevel=0.005)
    kit.plate((0, BIN_Y, BIN_TOP + 0.03), (2 * HW + 0.08, 2 * HD + 0.08, 0.06), p["plate"], panels=3)
    kit.handrail([(-HW, BIN_Y - HD, BIN_TOP + 0.06), (HW, BIN_Y - HD, BIN_TOP + 0.06)], height=0.35, posts_every=0.5)
    # cone down to the slide gate
    rig.mesh("cone", [
        (-HW, BIN_Y - HD, BIN_BOTTOM), (HW, BIN_Y - HD, BIN_BOTTOM), (HW, BIN_Y + HD, BIN_BOTTOM), (-HW, BIN_Y + HD, BIN_BOTTOM),
        (-0.24, CHUTE_Y - 0.24, PORTAL_Z + 0.3), (0.24, CHUTE_Y - 0.24, PORTAL_Z + 0.3), (0.24, CHUTE_Y + 0.24, PORTAL_Z + 0.3),
        (-0.24, CHUTE_Y + 0.24, PORTAL_Z + 0.3),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], p["olive"], bevel=0.015)
    for k in range(5):
        t = (k + 1) / 6
        a = (-HW + t * 2 * HW, BIN_Y - HD, BIN_BOTTOM)
        b = (-0.24 + t * 0.48, CHUTE_Y - 0.24, PORTAL_Z + 0.3)
        rig.cylinder(f"cone_rib{k}", a, b, 0.02, p["steel"], verts=6)
    # roof equipment: dust filter, fan, vent, level lamps
    rig.cylinder("filter", (-0.6, BIN_Y + 0.2, BIN_TOP + 0.06), (-0.6, BIN_Y + 0.2, BIN_TOP + 0.6), 0.22, p["olive"], verts=24)
    rig.cylinder("filter_cap", (-0.6, BIN_Y + 0.2, BIN_TOP + 0.6), (-0.6, BIN_Y + 0.2, BIN_TOP + 0.66), 0.25, p["dark"], verts=24)
    kit.bolts_around((-0.6, BIN_Y + 0.2, BIN_TOP + 0.66), (0, 0, 1), 0.2, 10)
    kit.fan((0.45, BIN_Y + 0.2, BIN_TOP + 0.08), radius=0.18, axis="z")
    kit.pipe([(0.9, BIN_Y + 0.45, BIN_TOP + 0.06), (0.9, BIN_Y + 0.45, BIN_TOP + 0.4), (0.6, BIN_Y + 0.45, BIN_TOP + 0.4)], 0.04,
             p["steel"])
    for k, col in enumerate(("green", "green", "amber")):
        kit.lamp((-0.85 + k * 0.16, BIN_Y - HD - 0.06, BIN_TOP - 0.18), col, size=0.04)
    # slide gate with hydraulic ram, then the bellows chute
    rig.box("slide_gate", (0, CHUTE_Y, PORTAL_Z + 0.22), (0.62, 0.62, 0.14), p["red"], bevel=0.015)
    kit.rivets((-0.28, CHUTE_Y - 0.32, PORTAL_Z + 0.26), (0.28, CHUTE_Y - 0.32, PORTAL_Z + 0.26), 6, (0, -1, 0))
    rig.cylinder("gate_ram", (0.32, CHUTE_Y - 0.18, PORTAL_Z + 0.22), (0.85, CHUTE_Y - 0.18, PORTAL_Z + 0.22), 0.035, p["chrome"])
    rig.cylinder("gate_ram_body", (0.85, CHUTE_Y - 0.18, PORTAL_Z + 0.22), (1.3, CHUTE_Y - 0.18, PORTAL_Z + 0.22), 0.065, p["yellow"])
    kit.hose([(1.3, CHUTE_Y - 0.18, PORTAL_Z + 0.22), (1.5, CHUTE_Y + 0.1, PORTAL_Z + 0.35), (1.45, CHUTE_Y + 0.5, PORTAL_Z + 0.25)],
             0.025, p["rubber"], ribs_per_tile=20)
    rig.cylinder("chute_collar", (0, CHUTE_Y, CHUTE_TOP - 0.05), (0, CHUTE_Y, CHUTE_TOP + 0.12), 0.22, p["dark"], verts=24)
    rings = 8
    for k in range(rings):
        frac = (k + 1) / rings
        z0 = CHUTE_TOP - frac * (CHUTE_TOP - CHUTE_UP)
        bellows.append((rig.torus(f"bellow{k}", (0, CHUTE_Y, z0), 0.19, 0.04, p["rubber"]), frac))
    bellows.append((rig.cylinder("nozzle", (0, CHUTE_Y, CHUTE_UP - 0.1), (0, CHUTE_Y, CHUTE_UP), 0.17, p["steel"], verts=24), 1.0))
    bellows.append((rig.torus("nozzle_lip", (0, CHUTE_Y, CHUTE_UP - 0.1), 0.18, 0.022, p["yellow"]), 1.0))
    for x in (-0.3, 0.3):  # winch cables
        bellows.append((rig.cylinder(f"cable{x}", (x, CHUTE_Y, CHUTE_UP), (x, CHUTE_Y, CHUTE_TOP), 0.008, p["dark"], verts=6), 1.0))


def elevator(p):
    """Bucket elevator at the port lifting the goods to the bin roof."""
    rig.layer("base")
    x, y = 2.5, -0.35
    kit.footing(x, y, (0.7, 0.7), 0.16)
    rig.box("elev_boot", (x, y, 0.45), (0.62, 0.62, 0.6), p["red"], bevel=0.02)
    kit.rivets((x - 0.28, y - 0.32, 0.7), (x + 0.28, y - 0.32, 0.7), 6, (0, -1, 0))
    rig.mesh("elev_hopper", [
        (x - 0.3, y - 0.3, 0.75), (x + 0.45, y - 0.3, 0.75), (x + 0.45, y + 0.3, 0.75), (x - 0.3, y + 0.3, 0.75),
        (x - 0.2, y - 0.2, 0.56), (x + 0.45, y - 0.2, 0.56), (x + 0.45, y + 0.2, 0.56), (x - 0.2, y + 0.2, 0.56),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], p["yellow"], bevel=0.01)
    for dx in (-0.12, 0.12):
        rig.box(f"elev_leg{dx}", (x + dx, y, 2.75), (0.2, 0.38, 4.0), p["olive"], bevel=0.01)
    for k in range(9):
        z = 0.85 + k * 0.48
        rig.box(f"elev_flange{k}", (x, y, z), (0.52, 0.44, 0.04), p["steel"], bevel=0.005)
        kit.rivets((x - 0.22, y - 0.225, z), (x + 0.22, y - 0.225, z), 4, (0, -1, 0))
    rig.box("elev_door", (x - 0.12, y - 0.2, 1.3), (0.16, 0.02, 0.3), p["dark"], bevel=0.004)
    kit.ladder((x + 0.32, y, 0.15), (x + 0.32, y, 4.75), cage=True)
    rig.layer("top")
    rig.box("elev_head", (x, y, 5.0), (0.64, 0.52, 0.52), p["red"], bevel=0.02)
    kit.rivets((x - 0.3, y - 0.27, 5.2), (x + 0.3, y - 0.27, 5.2), 6, (0, -1, 0))
    kit.motor((x + 0.12, y - 0.48, 5.14), axis="x", length=0.34, radius=0.12)
    big = rig.gear("elev_gear_big", (x - 0.12, y - 0.3, 4.98), 0.17, 0.04, 16, p["brass"], axis="y")
    small = rig.gear("elev_gear_small", (x + 0.15, y - 0.3, 5.16), 0.09, 0.04, 9, p["brass"], axis="y")
    spinning.append((big, 2 * math.pi / 16))
    spinning.append((small, -2 * math.pi / 9))
    kit.pipe([(x - 0.32, y + 0.1, 5.0), (1.6, BIN_Y + 0.1, 4.95), (1.0, BIN_Y + 0.1, BIN_TOP + 0.08)], 0.09, p["steel"])
    kit.lamp((x - 0.2, y - 0.27, 5.32), "amber")


def build():
    rig.reset()
    kit.reset()
    p = kit.palette()
    portal(p)
    elevator(p)
    bin_and_chute(p)
    rig.layer("base")
    rig.sun()
    rig.fill_light()
    rig.camera(9, 11, shift_y=2.5)


def set_chute(extension):
    """0 = retracted, 1 = resting on the wagon."""
    drop = (CHUTE_UP - CHUTE_DOWN) * extension
    for obj, frac in bellows:
        z0 = obj.get("z0")
        if z0 is None:
            obj["z0"] = z0 = obj.location.z
        obj.location.z = z0 - drop * frac


def spin(frame):
    for pivot, step in spinning:
        pivot.rotation_euler[2] = step * frame


def render_variant(out, v):
    d = os.path.join(out, f"v{v}")
    orient = (v - 1) / 4
    set_chute(0)
    spin(0)
    rig.render_frames(d, [0], lambda i: orient, passes=("base", "base_mask", "shadow", "top", "top_mask"), samples=32)
    rig.rename(d, "top", "idle", 1)
    rig.render_frames(d, list(range(EXTEND_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: set_chute((i + 1) / EXTEND_FRAMES))
    rig.rename(d, "top", "extend", EXTEND_FRAMES)
    rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: (set_chute(1), spin(i)))
    rig.rename(d, "top", "work", ANIM_FRAMES)


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    variants = [int(x) for x in a[1:]] or [1, 2, 3, 4]
    build()
    for v in variants:
        render_variant(out, v)
