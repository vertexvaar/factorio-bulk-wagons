"""Loading silo (0.5.0): a riveted silo bin on a braced steel portal over a whole wagon
slot. Along both long sides a collector trough at the foot of the bin has an inlet per
tile, where the steep conveyors of the bulk connectors (connector_v2.py) discharge;
screws carry the goods up into the gallery over the bins, and three bellows chutes,
one per compartment, lower into the wagon to fill it.

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


def rim(p):
    """Concrete strips along the long sides where the connectors stand, an anchor plate
    per tile."""
    rig.layer("base")
    for sx in (-1, 1):
        x = sx * 2.5
        rig.box(f"rim{sx}", (x, 0, 0.03), (0.96, 5.96, 0.06), p["concrete"], bevel=0.01)
        kit.hazard((sx * 2.04, 0, 0.065), (0.04, 5.9, 0.01), stripes=30, axis="y")
        for k in range(6):
            y = -2.5 + k
            rig.box(f"anchor{sx}{k}", (x, y, 0.07), (0.7, 0.7, 0.02), p["steel"], bevel=0.004)
            kit.rivets((x - 0.3, y - 0.3, 0.08), (x + 0.3, y - 0.3, 0.08), 4, (0, 0, 1))
            kit.rivets((x - 0.3, y + 0.3, 0.08), (x + 0.3, y + 0.3, 0.08), 4, (0, 0, 1))


def collectors(p):
    """A collector trough on brackets along each side at the foot of the bin, with a
    hooded inlet per tile (open to the outside, where the connector's conveyor reaches in)
    and an inclined screw from its middle up into the gallery."""
    rig.layer("top")
    z = 3.2
    for sx in (-1, 1):
        x = sx * 2.2
        rig.box(f"trough{sx}", (x, 0, z), (0.4, 5.9, 0.26), p["red"], bevel=0.02, mask=True)
        rig.box(f"trough_lid{sx}", (x - sx * 0.04, 0, z + 0.145), (0.34, 5.92, 0.03), p["steel"], bevel=0.005)
        for y in (-2.6, -0.9, 0.9, 2.6):
            rig.box(f"bracket{sx}{y}", (sx * 1.8, y, z - 0.08), (0.5, 0.08, 0.08), p["steel"], bevel=0.004)
            rig.cylinder(f"strut{sx}{y}", (sx * 2.25, y, z - 0.13), (sx * 1.5, y, z - 0.75), 0.02, p["steel"], verts=6)
        for k in range(6):
            y = -2.5 + k
            # inlet: a dark opening in the trough's outer wall under a small hood
            rig.box(f"inlet{sx}{k}", (sx * 2.405, y, z + 0.02), (0.02, 0.32, 0.16), p["dark"], bevel=0)
            rig.box(f"inlet_hood{sx}{k}", (sx * 2.44, y, z + 0.14), (0.1, 0.4, 0.04), p["red"], bevel=0.005, mask=True)
            kit.rivets((sx * 2.41, y - 0.18, z - 0.09), (sx * 2.41, y + 0.18, z - 0.09), 3, (sx, 0, 0), radius=0.01)
        kit.motor((x, -2.75, z + 0.08), axis="y", length=0.2, radius=0.07)
        # screw up into the gallery
        kit.pipe([(x - sx * 0.1, 0.1, z + 0.1), (sx * 0.6, 0.1, HEAD - 0.2), (sx * 0.2, 0.1, BIN_TOP + 0.55)], 0.08, p["steel"])
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
    rim(p)
    collectors(p)
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
