"""B1 portal silo: a steel portal over the track carrying a silo bin, filled by a
bucket elevator at the belt port, emptying through a telescopic chute.

Run:  blender -b --factory-startup -P tools/blender/station_b1.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 2 tiles, rail north-south through x in [-1, 1], port east.

Passes per variant: base, shadow, idle top (chute retracted), then
  extend_000..extend_{EXTEND_FRAMES-1}: the chute lowering onto a wagon (played once),
  work_000..work_{ANIM_FRAMES-1}: loading loop (elevator drive spinning, chute down).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rig  # noqa: E402

ANIM_FRAMES = 8
EXTEND_FRAMES = 8
LEG_X, LEG_Y = 1.62, 0.78
PORTAL_Z = 3.0
BIN_BOTTOM, BIN_TOP = 3.45, 4.65
CHUTE_UP, CHUTE_DOWN = 2.85, 2.08  # lower edge of the telescopic chute
BIN_Y = 0.22  # the bin sits to the north so the chute stays visible in front of it
CHUTE_Y = -0.42

spinning = []  # (pivot, step per frame)
telescope = []  # (object, fraction of the travel it moves)


def materials():
    return {
        "steel": rig.material("steel", (0.30, 0.31, 0.32), roughness=0.4, metallic=0.7, grime=0.3),
        "bin": rig.material("bin", (0.38, 0.39, 0.40), roughness=0.45, metallic=0.5, grime=0.35, scale=2),
        "dark": rig.material("dark", (0.06, 0.06, 0.065), roughness=0.5, metallic=0.5, grime=0.2),
        "concrete": rig.material("concrete", (0.42, 0.40, 0.37), roughness=0.9, grime=0.4, scale=5, bump=0.4),
        "yellow": rig.material("yellow", (0.80, 0.58, 0.06), roughness=0.5, grime=0.35),
        "accent": rig.material("accent", (0.48, 0.17, 0.06), roughness=0.5, grime=0.35, scale=3),
        "roller": rig.material("roller", (0.55, 0.55, 0.55), roughness=0.3, metallic=0.9, grime=0.2),
        "motor": rig.material("motor", (0.20, 0.28, 0.36), roughness=0.45, metallic=0.3, grime=0.3),
        "brass": rig.material("brass", (0.62, 0.45, 0.16), roughness=0.3, metallic=0.9, grime=0.15),
        "lamp": rig.material("lamp", (1.0, 0.7, 0.3), emission=(1.0, 0.55, 0.15)),
        "green": rig.material("green", (0.3, 1.0, 0.4), emission=(0.2, 1.0, 0.3)),
    }


def footing(name, x, y, m, size=(0.42, 0.42)):
    rig.box(name, (x, y, 0.07), (size[0], size[1], 0.14), m["concrete"])
    for dx in (-1, 1):
        for dy in (-1, 1):
            rig.cylinder(f"{name}_bolt{dx}{dy}", (x + dx * size[0] * 0.32, y + dy * size[1] * 0.32, 0.12),
                         (x + dx * size[0] * 0.32, y + dy * size[1] * 0.32, 0.19), 0.022, m["dark"], verts=6)


def portal(m):
    rig.layer("base")
    for x in (-LEG_X, LEG_X):
        for y in (-LEG_Y, LEG_Y):
            footing(f"foot{x}{y}", x, y, m)
            # H-section legs: flanges and web
            for dy in (-0.07, 0.07):
                rig.box(f"leg{x}{y}{dy}", (x, y + dy, PORTAL_Z / 2 + 0.07), (0.2, 0.025, PORTAL_Z - 0.1), m["steel"])
            rig.box(f"web{x}{y}", (x, y, PORTAL_Z / 2 + 0.07), (0.03, 0.14, PORTAL_Z - 0.1), m["steel"])
        # side bracing between the two legs of a frame
        rig.cylinder(f"xbrace_a{x}", (x, -LEG_Y, 0.4), (x, LEG_Y, 2.2), 0.03, m["steel"], verts=6)
        rig.cylinder(f"xbrace_b{x}", (x, LEG_Y, 0.4), (x, -LEG_Y, 2.2), 0.03, m["steel"], verts=6)
        rig.box(f"tie{x}", (x, 0, 2.3), (0.08, 2 * LEG_Y, 0.08), m["steel"])
    # yellow/black impact guards at the foot of the legs facing the track
    for x in (-LEG_X, LEG_X):
        for y in (-LEG_Y, LEG_Y):
            for k in range(4):
                rig.box(f"guard{x}{y}{k}", (x - math.copysign(0.13, x), y, 0.25 + k * 0.12), (0.02, 0.22, 0.1),
                        m["yellow"] if k % 2 == 0 else m["dark"], bevel=0)


def bin_and_chute(m):
    rig.layer("top")
    # portal girders and walkway around the bin
    for y in (-LEG_Y, LEG_Y):
        rig.box(f"girder{y}", (0, y, PORTAL_Z), (2 * LEG_X + 0.3, 0.2, 0.3), m["steel"])
    for x in (-LEG_X, LEG_X):
        rig.box(f"girder_x{x}", (x, 0, PORTAL_Z), (0.2, 2 * LEG_Y + 0.2, 0.3), m["steel"])
    for x in (-1, 1):  # walkways left and right of the chute opening
        rig.box(f"walkway{x}", (x * (LEG_X - 0.15), 0, PORTAL_Z + 0.17), (0.9, 2 * LEG_Y + 0.4, 0.05), m["steel"])
        for k in range(4):
            rig.box(f"grate{x}{k}", (x * (LEG_X - 0.5 + k * 0.23), 0, PORTAL_Z + 0.2), (0.02, 2 * LEG_Y + 0.35, 0.01), m["dark"], bevel=0)
    rig.box("walkway_n", (0, LEG_Y - 0.05, PORTAL_Z + 0.17), (2 * LEG_X, 0.5, 0.05), m["steel"])
    corners = [(-LEG_X - 0.22, -LEG_Y - 0.17), (LEG_X + 0.22, -LEG_Y - 0.17), (LEG_X + 0.22, LEG_Y + 0.17), (-LEG_X - 0.22, LEG_Y + 0.17)]
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        rig.cylinder(f"handrail{i}", (a[0], a[1], PORTAL_Z + 0.65), (b[0], b[1], PORTAL_Z + 0.65), 0.018, m["yellow"])
        rig.cylinder(f"midrail{i}", (a[0], a[1], PORTAL_Z + 0.42), (b[0], b[1], PORTAL_Z + 0.42), 0.012, m["yellow"])
        for k in range(5):
            p = (a[0] + (b[0] - a[0]) * k / 4, a[1] + (b[1] - a[1]) * k / 4)
            rig.cylinder(f"stanchion{i}{k}", (p[0], p[1], PORTAL_Z + 0.2), (p[0], p[1], PORTAL_Z + 0.65), 0.016, m["yellow"])

    # silo bin: box with stiffeners, cone down into the chute
    hw, hd = 1.15, 0.72
    rig.box("bin", (0, BIN_Y, (BIN_BOTTOM + BIN_TOP) / 2), (2 * hw, 2 * hd, BIN_TOP - BIN_BOTTOM), m["bin"], bevel=0.02)
    for k in range(7):
        x = -hw + 0.1 + k * (2 * hw - 0.2) / 6
        for y in (-hd - 0.02, hd + 0.02):
            rig.box(f"bin_rib{k}{y}", (x, y + BIN_Y, (BIN_BOTTOM + BIN_TOP) / 2), (0.06, 0.04, BIN_TOP - BIN_BOTTOM), m["bin"])
    for z in (BIN_BOTTOM + 0.4, BIN_BOTTOM + 0.8):
        rig.box(f"bin_band{z}", (0, BIN_Y, z), (2 * hw + 0.04, 2 * hd + 0.04, 0.05), m["steel"])
    rig.box("bin_roof", (0, BIN_Y, BIN_TOP + 0.04), (2 * hw + 0.1, 2 * hd + 0.1, 0.08), m["steel"])
    rig.mesh("cone", [
        (-hw, BIN_Y - hd, BIN_BOTTOM), (hw, BIN_Y - hd, BIN_BOTTOM), (hw, BIN_Y + hd, BIN_BOTTOM), (-hw, BIN_Y + hd, BIN_BOTTOM),
        (-0.24, CHUTE_Y - 0.24, PORTAL_Z + 0.25), (0.24, CHUTE_Y - 0.24, PORTAL_Z + 0.25), (0.24, CHUTE_Y + 0.24, PORTAL_Z + 0.25),
        (-0.24, CHUTE_Y + 0.24, PORTAL_Z + 0.25),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], m["bin"], bevel=0.015)
    # fill level lamps on the south face and a dust filter on the roof
    for k in range(3):
        rig.box(f"level{k}", (-0.7 + k * 0.18, BIN_Y - hd - 0.045, BIN_TOP - 0.25), (0.08, 0.02, 0.08), m["green"] if k < 2 else m["lamp"], bevel=0)
    rig.cylinder("filter", (-0.6, 0.4, BIN_TOP + 0.08), (-0.6, 0.4, BIN_TOP + 0.55), 0.22, m["steel"], verts=20)
    rig.cylinder("filter_cap", (-0.6, 0.4, BIN_TOP + 0.55), (-0.6, 0.4, BIN_TOP + 0.6), 0.25, m["dark"], verts=20)
    rig.cylinder("vent", (0.5, 0.35, BIN_TOP + 0.08), (0.5, 0.35, BIN_TOP + 0.4), 0.07, m["steel"], verts=12)

    # telescopic chute: three nested segments, slide gate and hydraulic cylinder
    rig.box("slide_gate", (0, CHUTE_Y, PORTAL_Z + 0.2), (0.62, 0.62, 0.12), m["accent"])
    rig.cylinder("gate_ram", (0.32, CHUTE_Y - 0.2, PORTAL_Z + 0.2), (0.9, CHUTE_Y - 0.2, PORTAL_Z + 0.2), 0.04, m["roller"])
    rig.cylinder("gate_ram_body", (0.9, CHUTE_Y - 0.2, PORTAL_Z + 0.2), (1.3, CHUTE_Y - 0.2, PORTAL_Z + 0.2), 0.065, m["yellow"])
    for k, (r, frac) in enumerate(((0.26, 0.0), (0.22, 0.5), (0.18, 1.0))):
        seg = rig.cylinder(f"tele{k}", (0, CHUTE_Y, CHUTE_UP), (0, CHUTE_Y, CHUTE_UP + 0.38), r, m["roller"] if k else m["steel"], verts=24)
        ring = rig.torus(f"tele_ring{k}", (0, CHUTE_Y, CHUTE_UP + 0.36), r + 0.01, 0.025, m["dark"])
        telescope.append((seg, frac))
        telescope.append((ring, frac))
    skirt = rig.cylinder("skirt", (0, CHUTE_Y, CHUTE_UP - 0.06), (0, CHUTE_Y, CHUTE_UP), 0.24, m["dark"], verts=24)
    telescope.append((skirt, 1.0))
    # winch cables
    for x in (-0.3, 0.3):
        cable = rig.cylinder(f"cable{x}", (x, CHUTE_Y, CHUTE_UP), (x, CHUTE_Y, PORTAL_Z + 0.2), 0.008, m["dark"], verts=6)
        telescope.append((cable, 1.0))


def elevator(m):
    """Bucket elevator at the port lifting the goods to the top of the bin."""
    rig.layer("base")
    x, y = 2.5, -0.35
    footing("elev_foot", x, y, m, (0.62, 0.62))
    rig.box("elev_boot", (x, y, 0.4), (0.6, 0.6, 0.6), m["accent"])
    rig.mesh("elev_hopper", [
        (x - 0.3, y - 0.3, 0.7), (x + 0.45, y - 0.3, 0.7), (x + 0.45, y + 0.3, 0.7), (x - 0.3, y + 0.3, 0.7),
        (x - 0.2, y - 0.2, 0.5), (x + 0.45, y - 0.2, 0.5), (x + 0.45, y + 0.2, 0.5), (x - 0.2, y + 0.2, 0.5),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], m["yellow"], bevel=0.01)
    for dx in (-0.12, 0.12):
        rig.box(f"elev_casing{dx}", (x + dx, y, 2.6), (0.2, 0.36, 4.2), m["bin"])
    for k in range(9):
        rig.box(f"elev_flange{k}", (x, y, 0.75 + k * 0.5), (0.5, 0.42, 0.04), m["steel"])
    for k in range(16):
        rig.cylinder(f"elev_rung{k}", (x + 0.3, y - 0.14, 0.4 + k * 0.28), (x + 0.3, y + 0.14, 0.4 + k * 0.28), 0.012, m["yellow"])
    for dy in (-0.14, 0.14):
        rig.cylinder(f"elev_ladder{dy}", (x + 0.3, y + dy, 0.2), (x + 0.3, y + dy, 4.7), 0.016, m["yellow"])
    rig.layer("top")
    # head with drive motor and exposed gear pair, spout into the bin roof
    rig.box("elev_head", (x, y, 4.95), (0.62, 0.5, 0.5), m["accent"])
    rig.mesh("elev_spout", [
        (x - 0.3, y - 0.15, 5.0), (x - 0.3, y + 0.15, 5.0), (x - 0.3, y + 0.15, 4.8), (x - 0.3, y - 0.15, 4.8),
        (0.95, BIN_Y - 0.12, 4.75), (0.95, BIN_Y + 0.12, 4.75), (0.95, BIN_Y + 0.12, 4.6), (0.95, BIN_Y - 0.12, 4.6),
    ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], m["steel"], bevel=0.01)
    rig.cylinder("elev_motor", (x + 0.3, y - 0.42, 5.0), (x + 0.3, y - 0.42, 5.32), 0.15, m["motor"], verts=20)
    big = rig.gear("elev_gear_big", (x, y - 0.3, 4.95), 0.2, 0.04, 16, m["brass"], axis="y")
    small = rig.gear("elev_gear_small", (x + 0.3, y - 0.3, 5.15), 0.1, 0.04, 8, m["brass"], axis="y")
    spinning.append((big, 2 * math.pi / 16))
    spinning.append((small, -2 * math.pi / 8))
    rig.box("elev_lamp", (x - 0.2, y - 0.26, 5.22), (0.06, 0.02, 0.06), m["lamp"], bevel=0)


def build():
    rig.reset()
    m = materials()
    portal(m)
    elevator(m)
    bin_and_chute(m)
    rig.layer("base")
    rig.sun()
    rig.fill_light()
    rig.camera(9, 11, shift_y=2.5)


def set_chute(extension):
    """0 = retracted, 1 = resting on the wagon."""
    drop = (CHUTE_UP - CHUTE_DOWN) * extension
    for obj, frac in telescope:
        base = obj.get("z0")
        if base is None:
            obj["z0"] = base = obj.location.z
        obj.location.z = base - drop * frac


def spin(frame):
    for pivot, step in spinning:
        pivot.rotation_euler[2] = step * frame


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    variants = [int(x) for x in a[1:]] or [1, 2, 3, 4]
    build()
    for v in variants:
        d = os.path.join(out, f"v{v}")
        orient = (v - 1) / 4
        set_chute(0)
        spin(0)
        rig.render_frames(d, [0], lambda i: orient, passes=("base", "shadow", "top"), samples=32)
        os.replace(os.path.join(d, "top_000.png"), os.path.join(d, "idle_000.png"))
        rig.render_frames(d, list(range(EXTEND_FRAMES)), lambda i: orient, passes=("top",), samples=32,
                          pose=lambda i: set_chute((i + 1) / EXTEND_FRAMES))
        for i in range(EXTEND_FRAMES):
            os.replace(os.path.join(d, f"top_{i:03d}.png"), os.path.join(d, f"extend_{i:03d}.png"))
        rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("top",), samples=32,
                          pose=lambda i: (set_chute(1), spin(i)))
        for i in range(ANIM_FRAMES):
            os.replace(os.path.join(d, f"top_{i:03d}.png"), os.path.join(d, f"work_{i:03d}.png"))
