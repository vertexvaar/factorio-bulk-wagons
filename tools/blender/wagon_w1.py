"""W1 'Cabred' hopper wagon, modelled after the Argentine ballast hopper.

Run:  blender -b --factory-startup -P tools/blender/wagon_w1.py -- <out_dir> [frames...]
Frames are 0..127, frame i shows orientation i/256 (back equals front).
The wheels are not modelled: Factorio draws its standard train wheels on top.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rig  # noqa: E402

# Wagon runs along Y, front (orientation 0) pointing north (+Y). Units are tiles.
TOP_HALF_LEN = 2.72  # hopper top edge
BELT_HALF_LEN = 2.46  # ends slope inwards below the top
LOW_HALF_LEN = 2.0
HALF_W = 0.98  # hopper half width
LOW_HALF_W = 0.46
BODY_TOP = 1.95
BELT = 1.45  # where the vertical sides end and the hopper funnels start
Z_LOW = 0.92  # bottom opening of the funnels
SILL = 0.80  # top of the underframe
BOGIE_Y = 2.0
END_Y = 3.2  # headstock
# three equal compartments, each a funnel down to its discharge flaps
EDGES = (-TOP_HALF_LEN, -TOP_HALF_LEN / 3, TOP_HALF_LEN / 3, TOP_HALF_LEN)
BAYS = tuple((EDGES[i] + EDGES[i + 1]) / 2 for i in range(3))
BAY_HALF = TOP_HALF_LEN / 3


def materials(planet="nauvis"):
    return {
        "paint": rig.material("paint", (0.42, 0.43, 0.44), roughness=0.42, grime=0.45, scale=2.5, bump=0.1, rust=0.85),
        "paint_worn": rig.material("paint_worn", (0.2, 0.19, 0.18), roughness=0.75, grime=0.55, scale=4, bump=0.3, rust=0.9),
        # funnel insides: goods sliding down have rubbed the paint off the lower slopes
        "paint_slope": rig.material("paint_slope", (0.2, 0.19, 0.18), roughness=0.75, grime=0.55, scale=4, bump=0.3, rust=0.7,
                                    scrape=(Z_LOW, BELT + 0.1, 0.8)),
        "paint_in": rig.material("paint_in", (0.075, 0.07, 0.065), roughness=0.9, grime=0.5, scale=5, bump=0.3),
        "steel": rig.material("steel", (0.24, 0.24, 0.25), roughness=0.35, metallic=0.75, grime=0.4, rust=0.35),
        "dark": rig.material("dark", (0.06, 0.06, 0.065), roughness=0.5, metallic=0.5, grime=0.3, rust=0.3),
        "sill": rig.material("sill", (0.42, 0.27, 0.08), roughness=0.55, grime=0.5, scale=4, rust=0.5),
        "rust": rig.material("rust", (0.28, 0.14, 0.06), roughness=0.85, grime=0.5, scale=8, bump=0.35),
        "rail": rig.material("rail", (0.72, 0.72, 0.70), roughness=0.3, metallic=0.85, grime=0.25),
        "rivet": rig.material("rivet", (0.30, 0.30, 0.31), roughness=0.3, metallic=0.8, grime=0.1),
        "dust": rig.material("dust", (0.16, 0.12, 0.09), roughness=1.0, grime=0.6, scale=12, bump=0.6),
        "heap": rig.material("heap", (0.62, 0.62, 0.62), roughness=1.0, grime=0.5, scale=20, bump=1.0),
        "lamp": rig.material("lamp", (1.0, 0.7, 0.3), emission=(1.0, 0.55, 0.15)),
    }


def rivet_row(name, start, end, count, m, radius=0.018, axis="x"):
    for k in range(count):
        t = k / (count - 1)
        p = tuple(start[i] + t * (end[i] - start[i]) for i in range(3))
        d = {"x": (0.012, 0, 0), "y": (0, 0.012, 0), "z": (0, 0, 0.012)}[axis]
        rig.cylinder(f"{name}_{k}", (p[0] - d[0], p[1] - d[1], p[2] - d[2]), (p[0] + d[0], p[1] + d[1], p[2] + d[2]),
                     radius, m["rivet"], verts=8)


def solid(obj, thickness=0.04, inner_offset=0):
    mod = obj.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = -1
    mod.material_offset = inner_offset
    mod.use_rim = True
    bevel = obj.modifiers.new("bevel", "BEVEL")
    bevel.width = 0.012
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    return obj


def hopper(m):
    """Open hopper: a vertical upper band, under it three funnels (one per compartment)
    narrowing down to discharge flaps. Painted inside and out, so the colour shows inside."""
    band = [
        (-HALF_W, -TOP_HALF_LEN, BODY_TOP), (HALF_W, -TOP_HALF_LEN, BODY_TOP),
        (HALF_W, TOP_HALF_LEN, BODY_TOP), (-HALF_W, TOP_HALF_LEN, BODY_TOP),
        (-HALF_W, -TOP_HALF_LEN, BELT), (HALF_W, -TOP_HALF_LEN, BELT),
        (HALF_W, TOP_HALF_LEN, BELT), (-HALF_W, TOP_HALF_LEN, BELT),
    ]
    # the inside uses a darker, worn coat of the same paint, so the colour shows without glaring
    solid(rig.mesh("band", band, [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], [m["paint"], m["paint_worn"]], mask=True),
          inner_offset=1)

    ox, oy = 0.2, 0.22  # half size of the bottom opening
    for k, y in enumerate(BAYS):
        y0, y1 = EDGES[k], EDGES[k + 1]
        funnel = rig.mesh(f"funnel{k}", [
            (-HALF_W, y0, BELT), (HALF_W, y0, BELT), (HALF_W, y1, BELT), (-HALF_W, y1, BELT),
            (-ox, y - oy, Z_LOW), (ox, y - oy, Z_LOW), (ox, y + oy, Z_LOW), (-ox, y + oy, Z_LOW),
        ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], [m["paint"], m["paint_slope"]], mask=True)
        solid(funnel, inner_offset=1)
        # discharge flaps closing the opening, hinged on the long edges
        for sx in (-1, 1):
            flap = rig.mesh(f"flap{k}{sx}", [
                (sx * (ox + 0.02), y - oy - 0.02, Z_LOW - 0.01), (sx * (ox + 0.02), y + oy + 0.02, Z_LOW - 0.01),
                (0, y + oy + 0.02, Z_LOW - 0.08), (0, y - oy - 0.02, Z_LOW - 0.08),
            ], [(0, 1, 2, 3)], m["rust"])
            solid(flap, 0.025)
            rig.cylinder(f"hinge{k}{sx}", (sx * (ox + 0.02), y - oy - 0.04, Z_LOW - 0.01),
                         (sx * (ox + 0.02), y + oy + 0.04, Z_LOW - 0.01), 0.022, m["dark"], verts=10)
            # flap lever outside the funnel
            rig.box(f"flap_lever{k}{sx}", (sx * (ox + 0.12), y, Z_LOW - 0.08), (0.2, 0.05, 0.04), m["dark"], bevel=0.005)
        rig.box(f"flap_seam{k}", (0, y, Z_LOW - 0.075), (0.03, 2 * oy + 0.04, 0.02), m["dark"], bevel=0)
        # ridge cap where two funnels meet, and ribs down the outside of the slopes
        if k > 0:
            rig.box(f"ridge{k}", (0, y0, BELT + 0.02), (2 * HALF_W, 0.06, 0.05), m["paint"], mask=True)
        for sx in (-1, 1):
            for t in (-0.5, 0.5):
                top = (sx * (HALF_W + 0.01), y + t * BAY_HALF, BELT)
                low = (sx * (ox + 0.04), y + t * oy, Z_LOW + 0.02)
                rig.cylinder(f"rib{k}{sx}{t}", top, low, 0.022, m["paint"], verts=6, mask=True)
        # cross bracing inside the top of each compartment, like the original
        rig.cylinder(f"tie{k}", (-HALF_W, y, BODY_TOP - 0.2), (HALF_W, y, BODY_TOP - 0.2), 0.022, m["steel"], verts=8)

    # heavy rolled top rim with rivets
    for sx in (-1, 1):
        rig.box(f"rim_side{sx}", (sx * (HALF_W + 0.02), 0, BODY_TOP - 0.03), (0.08, 2 * TOP_HALF_LEN + 0.08, 0.1), m["paint"], mask=True)
        rivet_row(f"rim_rivets{sx}", (sx * (HALF_W + 0.065), -TOP_HALF_LEN + 0.1, BODY_TOP - 0.03),
                  (sx * (HALF_W + 0.065), TOP_HALF_LEN - 0.1, BODY_TOP - 0.03), 26, m)
    for sy in (-1, 1):
        rig.box(f"rim_end{sy}", (0, sy * (TOP_HALF_LEN + 0.02), BODY_TOP - 0.03), (2 * HALF_W + 0.12, 0.08, 0.1), m["paint"], mask=True)

    # stiffeners (U-channels), a mid rib and the lower ledge on the band
    for sx in (-1, 1):
        for i in range(10):
            y = -TOP_HALF_LEN + 0.25 + i * (2 * TOP_HALF_LEN - 0.5) / 9
            rig.box(f"stiff{sx}_{i}", (sx * (HALF_W + 0.035), y, (BELT + BODY_TOP) / 2 - 0.03),
                    (0.07, 0.09, BODY_TOP - BELT - 0.04), m["paint"], mask=True)
        rig.box(f"midrib{sx}", (sx * (HALF_W + 0.012), 0, (BELT + BODY_TOP) / 2), (0.025, 2 * TOP_HALF_LEN - 0.1, 0.035), m["paint"], mask=True)
        rig.box(f"ledge{sx}", (sx * (HALF_W + 0.04), 0, BELT + 0.01), (0.09, 2 * TOP_HALF_LEN, 0.06), m["paint"], mask=True)
        rivet_row(f"ledge_rivets{sx}", (sx * (HALF_W + 0.09), -TOP_HALF_LEN + 0.1, BELT + 0.01),
                  (sx * (HALF_W + 0.09), TOP_HALF_LEN - 0.1, BELT + 0.01), 26, m, radius=0.014)

    # end frames with round lightening holes, like the original's end posts
    for sy in (-1, 1):
        y = sy * (TOP_HALF_LEN + 0.1)
        for sx in (-1, 1):
            rig.box(f"end_post{sy}{sx}", (sx * 0.62, y, (SILL + BODY_TOP) / 2 - 0.05), (0.1, 0.12, BODY_TOP - SILL - 0.1), m["paint"], mask=True)
            rig.torus(f"end_hole{sy}{sx}", (sx * 0.62, y + sy * 0.065, 1.2), 0.07, 0.015, m["dark"], rotation=(math.pi / 2, 0, 0))
        rig.box(f"end_cross{sy}", (0, y, 1.62), (1.3, 0.1, 0.1), m["paint"], mask=True)

    # railing along the top edges
    for sx in (-1, 1):
        x = sx * (HALF_W + 0.02)
        for i in range(8):
            y = -TOP_HALF_LEN + 0.15 + i * (2 * TOP_HALF_LEN - 0.3) / 7
            rig.cylinder(f"top_post{sx}{i}", (x, y, BODY_TOP + 0.02), (x, y, BODY_TOP + 0.32), 0.014, m["rail"], verts=8)
        rig.cylinder(f"top_rail{sx}", (x, -TOP_HALF_LEN + 0.15, BODY_TOP + 0.32), (x, TOP_HALF_LEN - 0.15, BODY_TOP + 0.32), 0.018, m["rail"])
        rig.cylinder(f"top_midrail{sx}", (x, -TOP_HALF_LEN + 0.15, BODY_TOP + 0.18), (x, TOP_HALF_LEN - 0.15, BODY_TOP + 0.18), 0.012, m["rail"])


def underframe(m):
    rig.box("centre_sill", (0, 0, SILL - 0.1), (0.3, 2 * END_Y, 0.2), m["dark"])
    for sx in (-1, 1):
        rig.box(f"side_sill{sx}", (sx * 0.9, 0, SILL - 0.07), (0.08, 2 * END_Y - 0.2, 0.15), m["sill"])
        rig.box(f"side_sill_lip{sx}", (sx * 0.86, 0, SILL), (0.16, 2 * END_Y - 0.2, 0.03), m["sill"])
        rivet_row(f"sill_rivets{sx}", (sx * 0.945, -2.8, SILL - 0.07), (sx * 0.945, 2.8, SILL - 0.07), 28, m, radius=0.014)
        for i in range(9):
            y = -2.3 + i * (4.6 / 8)
            rig.box(f"post{sx}_{i}", (sx * 0.86, y, (SILL + BELT) / 2), (0.07, 0.1, BELT - SILL), m["paint"], mask=True)
        # gate operating shaft with lever brackets and bearing blocks
        rig.cylinder(f"shaft{sx}", (sx * 0.96, -2.4, 1.04), (sx * 0.96, 2.4, 1.04), 0.028, m["steel"])
        for y in BAYS:
            rig.box(f"lever{sx}{y}", (sx * 0.96, y + 0.3, 1.04), (0.08, 0.08, 0.16), m["steel"], bevel=0.01)
            rig.box(f"lever_arm{sx}{y}", (sx * 0.96, y + 0.3, 0.9), (0.035, 0.035, 0.24), m["steel"], bevel=0)
            rig.box(f"bearing{sx}{y}", (sx * 0.93, y - 0.35, 1.04), (0.06, 0.08, 0.1), m["dark"])
    for sy in (-1, 1):
        rig.box(f"bolster{sy}", (0, sy * BOGIE_Y, SILL - 0.12), (1.85, 0.3, 0.16), m["dark"])
        rig.box(f"bolster_plate{sy}", (0, sy * BOGIE_Y, SILL - 0.03), (1.6, 0.36, 0.02), m["steel"])
    # brake cylinder and reservoir between the bogies
    rig.cylinder("brake_cyl", (0.3, -0.5, 0.62), (0.3, 0.1, 0.62), 0.11, m["dark"])
    rig.cylinder("reservoir", (-0.3, -0.2, 0.62), (-0.3, 0.6, 0.62), 0.1, m["steel"])


def ends(m):
    for sy in (-1, 1):
        rig.box(f"platform{sy}", (0, sy * (END_Y - 0.28), SILL - 0.02), (1.9, 0.56, 0.05), m["steel"])
        for k in range(5):
            rig.box(f"tread{sy}{k}", (0, sy * (END_Y - 0.5 + k * 0.1), SILL + 0.008), (1.8, 0.02, 0.01), m["dark"], bevel=0)
        rig.box(f"headstock{sy}", (0, sy * END_Y, SILL - 0.1), (1.94, 0.1, 0.24), m["sill"])
        rig.box(f"step_plate{sy}", (0, sy * (END_Y + 0.02), SILL - 0.25), (0.5, 0.04, 0.08), m["dark"])
        for sx in (-1, 1):
            rig.cylinder(f"buffer_case{sy}{sx}", (sx * 0.58, sy * END_Y, SILL - 0.1), (sx * 0.58, sy * (END_Y + 0.14), SILL - 0.1), 0.075, m["dark"])
            rig.cylinder(f"buffer_head{sy}{sx}", (sx * 0.58, sy * (END_Y + 0.14), SILL - 0.1), (sx * 0.58, sy * (END_Y + 0.18), SILL - 0.1), 0.11, m["steel"], verts=20)
            rig.tube_path(f"railing{sy}{sx}", [
                (sx * 0.92, sy * 2.62, SILL), (sx * 0.92, sy * 2.62, SILL + 0.62), (sx * 0.92, sy * (END_Y - 0.06), SILL + 0.62),
                (sx * 0.92, sy * (END_Y - 0.06), SILL),
            ], 0.02, m["rail"])
            rig.cylinder(f"railing_mid{sy}{sx}", (sx * 0.92, sy * 2.62, SILL + 0.32), (sx * 0.92, sy * (END_Y - 0.06), SILL + 0.32), 0.014, m["rail"])
            rig.box(f"lamp{sy}{sx}", (sx * 0.8, sy * (END_Y + 0.05), SILL + 0.04), (0.08, 0.04, 0.07), m["lamp"], bevel=0)
            rig.box(f"lamp_case{sy}{sx}", (sx * 0.8, sy * (END_Y + 0.02), SILL + 0.04), (0.11, 0.04, 0.1), m["dark"])
        rig.cylinder(f"railing_cross{sy}", (-0.92, sy * (END_Y - 0.06), SILL + 0.62), (0.92, sy * (END_Y - 0.06), SILL + 0.62), 0.02, m["rail"])
        rig.box(f"coupler{sy}", (0, sy * (END_Y + 0.12), SILL - 0.18), (0.18, 0.26, 0.12), m["dark"])
        rig.box(f"coupler_knuckle{sy}", (0, sy * (END_Y + 0.26), SILL - 0.18), (0.26, 0.08, 0.14), m["steel"])
    # ladders from both end platforms up to the top railing
    for sy in (-1, 1):
        for sx in (-0.2, 0.2):
            rig.cylinder(f"ladder{sy}{sx}", (sx, sy * 2.95, SILL), (sx, sy * (TOP_HALF_LEN + 0.12), BODY_TOP + 0.35), 0.017, m["rail"])
        for k in range(8):
            t = (k + 1) / 9
            z = SILL + t * (BODY_TOP + 0.35 - SILL)
            y = sy * (2.95 - t * (2.95 - TOP_HALF_LEN - 0.12))
            rig.cylinder(f"rung{sy}{k}", (-0.2, y, z), (0.2, y, z), 0.013, m["rail"])
    rig.torus("brake_wheel", (0.55, -2.9, SILL + 0.4), 0.12, 0.016, m["dark"], rotation=(math.pi / 2, 0, 0))
    rig.cylinder("brake_spindle", (0.55, -2.9, SILL), (0.55, -2.9, SILL + 0.4), 0.015, m["dark"])


def cargo(m):
    """Heaps of loose goods, one per compartment. Rendered as their own grey layer that the
    game tints in the colour of the loaded ore and shows while the wagon is not empty."""
    import bpy
    rocks = bpy.data.textures.new("rocks", "VORONOI")
    rocks.noise_scale = 0.07
    lumps = bpy.data.textures.new("lumps", "CLOUDS")
    lumps.noise_scale = 0.35
    n = 28
    hx, hy = HALF_W - 0.05, BAY_HALF - 0.08
    for y0 in BAYS:
        verts, faces = [], []
        for j in range(n + 1):
            for i in range(n + 1):
                u, v = i / n * 2 - 1, j / n * 2 - 1
                # mound: high in the middle, down to the walls
                r = max(abs(u) ** 1.6, abs(v) ** 1.6)
                z = BODY_TOP - 0.38 + 0.32 * (1 - r) ** 1.4
                verts.append((u * hx, y0 + v * hy, z))
        for j in range(n):
            for i in range(n):
                a = j * (n + 1) + i
                faces.append((a, a + 1, a + n + 2, a + n + 1))
        heap = rig.mesh(f"heap{y0}", verts, faces, m["heap"])
        for tex, strength in ((lumps, 0.08), (rocks, 0.06)):
            disp = heap.modifiers.new(tex.name, "DISPLACE")
            disp.texture = tex
            disp.strength = strength
            disp.direction = "Z"
        heap["load"] = True
        for poly in heap.data.polygons:
            poly.use_smooth = True


def build(planet="nauvis"):
    rig.reset()
    m = materials(planet)
    hopper(m)
    underframe(m)
    ends(m)
    cargo(m)
    rig.sun()
    rig.fill_light()
    rig.camera(8, 9, shift_y=1.3)


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    frames = [int(x) for x in a[1:]] or list(range(128))
    build()
    rig.render_frames(out, frames, lambda i: i / 256, passes=("color", "mask", "shadow", "load"), samples=32)
