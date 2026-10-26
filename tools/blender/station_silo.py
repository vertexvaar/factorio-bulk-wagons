"""Loading silo (0.4.0): a riveted silo bin on a braced steel portal over a whole wagon
slot. Intake troughs along both long sides take the goods from the bulk connectors
(a hooded inlet per tile); a bucket elevator on each side lifts them into the bin, and
three bellows chutes, one per compartment, lower into the wagon to fill it.

Run:  blender -b --factory-startup -P tools/blender/station_silo.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 6 tiles, rail north-south through x in [-1, 1]. Variant 2
is the same model turned a quarter (rail east-west).

Renders per variant: base (ground parts), shadow, idle (top: bin and chutes up),
extend_000..007 (chutes lower onto the wagon, played once) and work_000..007
(elevator drives turning, chutes down). Each with a *_mask twin; top_static_000 is the
idle top without its moving parts.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import rig  # noqa: E402

ANIM_FRAMES = 8
EXTEND_FRAMES = 8
BAYS = (-1.95, 0.0, 1.95)
LEG_X, LEG_Y = 1.45, 2.6
PORTAL_Z = 3.0
BIN_BOTTOM, BIN_TOP = 3.45, 4.3
HW, HD = 2.25, 2.85
CHUTE_TOP, CHUTE_UP, CHUTE_DOWN = 3.1, 2.8, 2.05
ELEV_X = 2.3
SILO_R = 0.88
HEAD = BIN_TOP + 0.6  # elevator heads, just above the gallery

spinning = []
bellows = []


def frustum(name, center, r0, z0, r1, z1, mat, segments=32):
    """Cone section around a vertical axis: radius r0 at z0 to r1 at z1."""
    cx, cy = center
    verts, faces = [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        verts.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0))
        verts.append((cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    obj = rig.mesh(name, verts, faces, mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def portal(p):
    rig.layer("base")
    for x in (-LEG_X, LEG_X):
        for y in (-LEG_Y, 0.0, LEG_Y):
            kit.footing(x, y, (0.44, 0.44), 0.16)
            kit.ibeam((x, y, 0.18), (x, y, PORTAL_Z - 0.1), size=0.2)
            for k in range(4):  # impact guard facing the track
                rig.box(f"guard{x}{y}{k}", (x - math.copysign(0.13, x), y, 0.3 + k * 0.13), (0.02, 0.22, 0.11),
                        p["yellow"] if k % 2 == 0 else p["dark"], bevel=0)
        for (y0, y1) in ((-LEG_Y, 0.0), (0.0, LEG_Y)):
            rig.cylinder(f"xbrace_a{x}{y0}", (x, y0, 0.45), (x, y1, 2.3), 0.03, p["steel"], verts=6)
            rig.cylinder(f"xbrace_b{x}{y0}", (x, y1, 0.45), (x, y0, 2.3), 0.03, p["steel"], verts=6)
        kit.ibeam((x, -LEG_Y, 2.4), (x, LEG_Y, 2.4), size=0.1)
    kit.ladder((-LEG_X - 0.22, -1.2, 0.15), (-LEG_X - 0.22, -1.2, PORTAL_Z + 0.1), cage=True)
    kit.cabinet((-1.95, -2.6, 0.42), (0.45, 0.22, 0.66), facing="-y")
    kit.cable([(-1.85, -2.6, 0.76), (-1.6, -2.55, 1.3), (-1.5, -2.6, 2.9)], "red")
    kit.cable([(-2.0, -2.6, 0.76), (-1.62, -2.48, 1.2), (-1.52, -2.52, 2.9)], "green")


def intakes(p):
    """Intake troughs along the long sides: a hooded inlet per tile on the outer edge,
    a drag chain in the trough running to the elevator boot in the middle."""
    rig.layer("base")
    for sx in (-1, 1):
        x = sx * 2.72
        rig.box(f"trough{sx}", (x, 0, 0.16), (0.46, 5.9, 0.3), p["steel"], bevel=0.02)
        rig.box(f"trough_floor{sx}", (x, 0, 0.32), (0.36, 5.8, 0.02), p["dark"], bevel=0)
        for k in range(12):
            rig.box(f"chain{sx}{k}", (x, -2.75 + k * 0.5, 0.335), (0.3, 0.04, 0.02), p["chrome"], bevel=0)
        for k in range(6):
            y = -2.5 + k
            # inlet hood over the trough edge, open to the outside, rubber curtain strips
            rig.box(f"hood{sx}{k}", (sx * 2.82, y, 0.5), (0.3, 0.72, 0.05), p["red"], bevel=0.01, mask=True)
            kit.hazard((sx * 2.82, y, 0.535), (0.26, 0.64, 0.02), stripes=5, axis="y")
            for s in (-1, 1):
                rig.box(f"hood_side{sx}{k}{s}", (sx * 2.82, y + s * 0.35, 0.33), (0.3, 0.03, 0.34), p["red"], bevel=0.005,
                        mask=True)
            for c in range(7):
                rig.box(f"curtain{sx}{k}{c}", (sx * 2.96, y - 0.27 + c * 0.09, 0.32), (0.012, 0.08, 0.3), p["rubber"], bevel=0)
        kit.handrail([(sx * 2.45, -2.9, 0.33), (sx * 2.45, 2.9, 0.33)], height=0.35, posts_every=0.6)


def elevators(p):
    """A bucket elevator on each side, boot in the trough, head over the bin roof."""
    for sx in (-1, 1):
        x, y = sx * ELEV_X, 0.0
        rig.layer("base")
        rig.box(f"boot{sx}", (x, y, 0.5), (0.6, 0.62, 0.62), p["red"], bevel=0.02, mask=True)
        kit.rivets((x - 0.27, y - 0.32, 0.72), (x + 0.27, y - 0.32, 0.72), 6, (0, -1, 0))
        for dx in (-0.12, 0.12):
            rig.box(f"leg_low{sx}{dx}", (x + dx, y, 1.15), (0.2, 0.38, 0.8), p["olive"], bevel=0.01)
        rig.layer("top")
        for dx in (-0.12, 0.12):
            rig.box(f"leg_high{sx}{dx}", (x + dx, y, (1.55 + HEAD) / 2), (0.2, 0.38, HEAD - 1.55), p["olive"], bevel=0.01)
        for k in range(7):
            z = 1.7 + k * 0.45
            rig.box(f"flange{sx}{k}", (x, y, z), (0.52, 0.44, 0.04), p["steel"], bevel=0.005)
        rig.box(f"elev_head{sx}", (x, y, HEAD), (0.64, 0.52, 0.52), p["red"], bevel=0.02, mask=True)
        kit.rivets((x - 0.3, y - 0.27, HEAD + 0.2), (x + 0.3, y - 0.27, HEAD + 0.2), 6, (0, -1, 0))
        kit.motor((x, y - 0.48, HEAD + 0.12), axis="x", length=0.34, radius=0.12)
        big = rig.gear(f"elev_gear_big{sx}", (x - 0.12, y - 0.3, HEAD - 0.02), 0.17, 0.04, 16, p["brass"], axis="y")
        small = rig.gear(f"elev_gear_small{sx}", (x + 0.15, y - 0.3, HEAD + 0.16), 0.09, 0.04, 9, p["brass"], axis="y")
        spinning.append((big, 2 * math.pi / 16))
        spinning.append((small, -2 * math.pi / 9))
        kit.pipe([(x - sx * 0.32, y + 0.1, HEAD), (sx * 0.6, y + 0.1, HEAD), (sx * 0.2, y + 0.1, BIN_TOP + 0.55)], 0.09, p["steel"])
        kit.lamp((x - 0.2, y - 0.27, HEAD + 0.32), "amber")
    rig.layer("base")


def bin_and_chutes(p):
    rig.layer("top")
    for x in (-LEG_X, LEG_X):
        kit.ibeam((x, -LEG_Y - 0.2, PORTAL_Z), (x, LEG_Y + 0.2, PORTAL_Z), size=0.28)
    for y in (-LEG_Y, 0.0, LEG_Y):
        kit.ibeam((-LEG_X - 0.2, y, PORTAL_Z), (LEG_X + 0.2, y, PORTAL_Z), size=0.24)
    # deck around the bin foot, railed
    for sx in (-1, 1):
        kit.grating((sx * (LEG_X + 0.25), 0, PORTAL_Z + 0.17), (0.6, 2 * LEG_Y + 0.4))
    kit.handrail([(-LEG_X - 0.55, -LEG_Y - 0.2, PORTAL_Z + 0.19), (-LEG_X - 0.55, LEG_Y + 0.2, PORTAL_Z + 0.19)], height=0.5)
    kit.handrail([(LEG_X + 0.55, -LEG_Y - 0.2, PORTAL_Z + 0.19), (LEG_X + 0.55, LEG_Y + 0.2, PORTAL_Z + 0.19)], height=0.5)
    # three round silos in a row, one over each compartment, under a feed gallery
    for k, cy in enumerate(BAYS):
        rig.cylinder(f"silo{k}", (0, cy, BIN_BOTTOM), (0, cy, BIN_TOP), SILO_R, p["olive"], verts=40)
        for z in (BIN_BOTTOM + 0.35, BIN_BOTTOM + 0.8, BIN_TOP - 0.25):
            rig.torus(f"silo_ring{k}{z}", (0, cy, z), SILO_R + 0.01, 0.025, p["steel"])
        for a in range(8):
            ang = a * math.pi / 4
            x, y = (SILO_R + 0.02) * math.cos(ang), cy + (SILO_R + 0.02) * math.sin(ang)
            rig.box(f"silo_post{k}{a}", (x, y, (BIN_BOTTOM + BIN_TOP) / 2), (0.05, 0.05, BIN_TOP - BIN_BOTTOM), p["steel"], bevel=0.004)
        frustum(f"roof{k}", (0, cy), SILO_R + 0.04, BIN_TOP, 0.18, BIN_TOP + 0.32, p["plate"])
        frustum(f"cone{k}", (0, cy), SILO_R, BIN_BOTTOM, 0.22, PORTAL_Z + 0.32, p["olive"])
        for s in (-1, 1):  # level lamps facing the camera
            kit.lamp((s * 0.25, cy - SILO_R - 0.03, BIN_TOP - 0.45), "green" if s < 0 else "amber", size=0.035)
    rig.box("gallery", (0, 0, BIN_TOP + 0.47), (0.36, 2 * HD - 0.3, 0.22), p["olive"], bevel=0.02)
    for k in range(9):
        rig.box(f"gallery_rib{k}", (0, -HD + 0.3 + k * (2 * HD - 0.6) / 8, BIN_TOP + 0.47), (0.4, 0.04, 0.26), p["steel"], bevel=0.004)
    kit.grating((0.55, 0, BIN_TOP + 0.36), (0.45, 2 * HD))
    kit.handrail([(0.78, -HD, BIN_TOP + 0.38), (0.78, HD, BIN_TOP + 0.38)], height=0.35, posts_every=0.6)
    for cy in BAYS:
        rig.cylinder(f"drop{cy}", (0, cy, BIN_TOP + 0.34), (0, cy, BIN_TOP + 0.1), 0.1, p["steel"], verts=12)
    kit.fan((0, -1.0, BIN_TOP + 0.6), radius=0.12, axis="z")
    kit.fan((0, 1.0, BIN_TOP + 0.6), radius=0.12, axis="z")
    # slide gates under the cones, one per compartment, and their bellows chutes
    for k, cy in enumerate(BAYS):
        rig.box(f"gate{k}", (0, cy, PORTAL_Z + 0.24), (0.58, 0.58, 0.14), p["red"], bevel=0.015, mask=True)
        rig.cylinder(f"gate_ram{k}", (0.3, cy - 0.15, PORTAL_Z + 0.24), (0.8, cy - 0.15, PORTAL_Z + 0.24), 0.035, p["chrome"])
        rig.cylinder(f"gate_ram_body{k}", (0.8, cy - 0.15, PORTAL_Z + 0.24), (1.2, cy - 0.15, PORTAL_Z + 0.24), 0.06, p["yellow"])
        rig.cylinder(f"collar{k}", (0, cy, CHUTE_TOP - 0.05), (0, cy, CHUTE_TOP + 0.12), 0.21, p["dark"], verts=24)
        rings = 7
        for r in range(rings):
            frac = (r + 1) / rings
            z0 = CHUTE_TOP - frac * (CHUTE_TOP - CHUTE_UP)
            bellows.append((rig.torus(f"bellow{k}{r}", (0, cy, z0), 0.18, 0.04, p["rubber"]), frac))
        bellows.append((rig.cylinder(f"nozzle{k}", (0, cy, CHUTE_UP - 0.1), (0, cy, CHUTE_UP), 0.16, p["steel"], verts=24), 1.0))
        bellows.append((rig.torus(f"nozzle_lip{k}", (0, cy, CHUTE_UP - 0.1), 0.17, 0.022, p["yellow"]), 1.0))
    rig.layer("base")


def build():
    rig.reset()
    kit.reset()
    p = kit.palette()
    portal(p)
    intakes(p)
    elevators(p)
    bin_and_chutes(p)
    rig.layer("base")
    rig.sun()
    rig.fill_light()
    rig.camera(8.5, 12.5, shift_y=3.0)


def set_chutes(extension):
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
    set_chutes(0)
    spin(0)
    rig.mark_moving([obj for obj, _ in bellows] + [pivot for pivot, _ in spinning])
    rig.render_frames(d, [0], lambda i: orient, passes=("base", "base_mask", "shadow", "top", "top_mask", "top_static"),
                      samples=32)
    rig.rename(d, "top", "idle", 1)
    rig.render_frames(d, list(range(EXTEND_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: set_chutes((i + 1) / EXTEND_FRAMES))
    rig.rename(d, "top", "extend", EXTEND_FRAMES)
    rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: (set_chutes(1), spin(i)))
    rig.rename(d, "top", "work", ANIM_FRAMES)


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    variants = [int(x) for x in a[1:]] or [1, 2]
    build()
    for v in variants:
        render_variant(out, v)
