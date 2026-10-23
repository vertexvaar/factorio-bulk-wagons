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
BELT = 1.30  # where the vertical sides end and the slopes start
Z_LOW = 0.98
SILL = 0.80  # top of the underframe
BOGIE_Y = 2.0
END_Y = 3.2  # headstock
BAYS = (-1.3, 0.0, 1.3)


def materials(planet="nauvis"):
    return {
        "paint": rig.material("paint", (0.42, 0.43, 0.44), roughness=0.42, grime=0.35, scale=2.5, bump=0.1),
        "paint_in": rig.material("paint_in", (0.075, 0.07, 0.065), roughness=0.9, grime=0.5, scale=5, bump=0.3),
        "steel": rig.material("steel", (0.24, 0.24, 0.25), roughness=0.35, metallic=0.75, grime=0.3),
        "dark": rig.material("dark", (0.06, 0.06, 0.065), roughness=0.5, metallic=0.5, grime=0.2),
        "sill": rig.material("sill", (0.42, 0.27, 0.08), roughness=0.55, grime=0.4, scale=4),
        "rust": rig.material("rust", (0.28, 0.14, 0.06), roughness=0.85, grime=0.5, scale=8, bump=0.35),
        "rail": rig.material("rail", (0.72, 0.72, 0.70), roughness=0.3, metallic=0.85, grime=0.25),
        "rivet": rig.material("rivet", (0.30, 0.30, 0.31), roughness=0.3, metallic=0.8, grime=0.1),
        "dust": rig.material("dust", (0.16, 0.12, 0.09), roughness=1.0, grime=0.6, scale=12, bump=0.6),
        "lamp": rig.material("lamp", (1.0, 0.7, 0.3), emission=(1.0, 0.55, 0.15)),
    }


def rivet_row(name, start, end, count, m, radius=0.018, axis="x"):
    for k in range(count):
        t = k / (count - 1)
        p = tuple(start[i] + t * (end[i] - start[i]) for i in range(3))
        d = {"x": (0.012, 0, 0), "y": (0, 0.012, 0), "z": (0, 0, 0.012)}[axis]
        rig.cylinder(f"{name}_{k}", (p[0] - d[0], p[1] - d[1], p[2] - d[2]), (p[0] + d[0], p[1] + d[1], p[2] + d[2]),
                     radius, m["rivet"], verts=8)


def hopper(m):
    """Open hopper body: vertical upper band, sloped sides and ends down to three discharge bays."""
    outer = [
        (-HALF_W, -TOP_HALF_LEN, BODY_TOP), (HALF_W, -TOP_HALF_LEN, BODY_TOP),
        (HALF_W, TOP_HALF_LEN, BODY_TOP), (-HALF_W, TOP_HALF_LEN, BODY_TOP),
        (-HALF_W, -BELT_HALF_LEN, BELT), (HALF_W, -BELT_HALF_LEN, BELT),
        (HALF_W, BELT_HALF_LEN, BELT), (-HALF_W, BELT_HALF_LEN, BELT),
        (-LOW_HALF_W, -LOW_HALF_LEN, Z_LOW), (LOW_HALF_W, -LOW_HALF_LEN, Z_LOW),
        (LOW_HALF_W, LOW_HALF_LEN, Z_LOW), (-LOW_HALF_W, LOW_HALF_LEN, Z_LOW),
    ]
    faces = [
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
        (4, 8, 9, 5), (5, 9, 10, 6), (6, 10, 11, 7), (7, 11, 8, 4),
        (8, 11, 10, 9),
    ]
    shell = rig.mesh("hopper", outer, faces, [m["paint"], m["paint_in"]], mask=1)
    solid = shell.modifiers.new("solid", "SOLIDIFY")
    solid.thickness = 0.04
    solid.offset = -1
    solid.material_offset = 1
    solid.use_rim = True
    bevel = shell.modifiers.new("bevel", "BEVEL")
    bevel.width = 0.015
    bevel.segments = 2
    bevel.limit_method = "ANGLE"

    # heavy rolled top rim with rivets
    for sx in (-1, 1):
        rig.box(f"rim_side{sx}", (sx * (HALF_W + 0.02), 0, BODY_TOP - 0.03), (0.08, 2 * TOP_HALF_LEN + 0.08, 0.1), m["paint"], mask=True)
        rivet_row(f"rim_rivets{sx}", (sx * (HALF_W + 0.065), -TOP_HALF_LEN + 0.1, BODY_TOP - 0.03),
                  (sx * (HALF_W + 0.065), TOP_HALF_LEN - 0.1, BODY_TOP - 0.03), 22, m)
    for sy in (-1, 1):
        rig.box(f"rim_end{sy}", (0, sy * (TOP_HALF_LEN + 0.02), BODY_TOP - 0.03), (2 * HALF_W + 0.12, 0.08, 0.1), m["paint"], mask=True)

    # side stiffeners (U-channels) and two horizontal ribs on the upper band
    for sx in (-1, 1):
        for i in range(9):
            y = -2.2 + i * (4.4 / 8)
            rig.box(f"stiff{sx}_{i}", (sx * (HALF_W + 0.035), y, (BELT + BODY_TOP) / 2 - 0.04),
                    (0.07, 0.09, BODY_TOP - BELT - 0.06), m["paint"], mask=True)
        for z in (BELT + 0.22, BELT + 0.44):
            rig.box(f"rib{sx}{z}", (sx * (HALF_W + 0.012), 0, z), (0.025, 2 * BELT_HALF_LEN - 0.1, 0.035), m["paint"], mask=True)
        rig.box(f"ledge{sx}", (sx * (HALF_W + 0.04), 0, BELT + 0.02), (0.09, 2 * BELT_HALF_LEN, 0.06), m["paint"], mask=True)
        # braces down the sloped side panels
        for i in range(7):
            y = -1.8 + i * 0.6
            x_top, x_low = sx * (HALF_W + 0.01), sx * (LOW_HALF_W + 0.01)
            rig.cylinder(f"brace{sx}_{i}", (x_top, y, BELT), (x_low, y * 0.92, Z_LOW + 0.02), 0.03, m["paint"], verts=6)

    # end frames with round lightening holes, like the original's end posts
    for sy in (-1, 1):
        for sx in (-1, 1):
            y = sy * (BELT_HALF_LEN + 0.12)
            rig.box(f"end_post{sy}{sx}", (sx * 0.62, y, (SILL + BODY_TOP) / 2 - 0.1), (0.1, 0.12, BODY_TOP - SILL - 0.2), m["paint"], mask=True)
            rig.torus(f"end_hole{sy}{sx}", (sx * 0.62, y + sy * 0.065, 1.2), 0.07, 0.015, m["dark"], rotation=(math.pi / 2, 0, 0))
        rig.box(f"end_cross{sy}", (0, sy * (BELT_HALF_LEN + 0.12), 1.55), (1.3, 0.1, 0.1), m["paint"], mask=True)

    # inner stiffeners and leftover ore dust on the slopes
    for sx in (-1, 1):
        for i in range(5):
            y = -2.0 + i * 1.0
            rig.box(f"inner_stiff{sx}_{i}", (sx * (HALF_W - 0.06), y, (BELT + BODY_TOP) / 2), (0.05, 0.06, BODY_TOP - BELT - 0.1), m["steel"])
    for y in BAYS:
        dust = rig.mesh(f"dust{y}", [
            (-0.7, y - 0.45, Z_LOW + 0.2), (0.7, y - 0.45, Z_LOW + 0.2), (0.7, y + 0.45, Z_LOW + 0.2), (-0.7, y + 0.45, Z_LOW + 0.2),
            (0, y, Z_LOW + 0.08),
        ], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], m["dust"])

    # transverse dividers inside, giving three compartments with V-shaped floors
    for y in (-0.65, 0.65):
        rig.mesh(f"divider{y}", [
            (-HALF_W + 0.05, y - 0.38, Z_LOW + 0.05), (HALF_W - 0.05, y - 0.38, Z_LOW + 0.05),
            (HALF_W - 0.05, y, BODY_TOP - 0.15), (-HALF_W + 0.05, y, BODY_TOP - 0.15),
            (-HALF_W + 0.05, y + 0.38, Z_LOW + 0.05), (HALF_W - 0.05, y + 0.38, Z_LOW + 0.05),
        ], [(0, 1, 2, 3), (3, 2, 5, 4)], m["paint_in"])
        rig.box(f"divider_cap{y}", (0, y, BODY_TOP - 0.14), (2 * HALF_W - 0.08, 0.07, 0.05), m["steel"])

    # three discharge chutes with rusty curved gates underneath
    for y in BAYS:
        rig.mesh(f"chute{y}", [
            (-0.44, y - 0.4, Z_LOW + 0.02), (0.44, y - 0.4, Z_LOW + 0.02), (0.44, y + 0.4, Z_LOW + 0.02), (-0.44, y + 0.4, Z_LOW + 0.02),
            (-0.24, y - 0.28, 0.64), (0.24, y - 0.28, 0.64), (0.24, y + 0.28, 0.64), (-0.24, y + 0.28, 0.64),
        ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], m["paint"], bevel=0.01, mask=True)
        for sx in (-1, 1):
            gate = rig.cylinder(f"gate{y}{sx}", (sx * 0.32, y - 0.32, 0.6), (sx * 0.32, y + 0.32, 0.6), 0.17, m["rust"], verts=24)
            gate.scale = (0.55, 1, 1)
            rig.box(f"gate_arm{y}{sx}", (sx * 0.56, y, 0.72), (0.05, 0.12, 0.24), m["dark"])


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
            rig.box(f"lever{sx}{y}", (sx * 0.96, y + 0.2, 1.04), (0.08, 0.08, 0.16), m["steel"], bevel=0.01)
            rig.box(f"lever_arm{sx}{y}", (sx * 0.96, y + 0.2, 0.9), (0.035, 0.035, 0.24), m["steel"], bevel=0)
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
    # ladder up the front end
    for sx in (-0.2, 0.2):
        rig.cylinder(f"ladder{sx}", (sx, 2.9, SILL), (sx, 2.78, BODY_TOP + 0.15), 0.017, m["rail"])
    for k in range(7):
        t = (k + 1) / 8
        z = SILL + t * (BODY_TOP + 0.15 - SILL)
        y = 2.9 - t * 0.12
        rig.cylinder(f"rung{k}", (-0.2, y, z), (0.2, y, z), 0.013, m["rail"])
    rig.torus("brake_wheel", (0.5, -2.9, SILL + 0.4), 0.12, 0.016, m["dark"], rotation=(math.pi / 2, 0, 0))
    rig.cylinder("brake_spindle", (0.5, -2.78, SILL), (0.5, -2.9, SILL + 0.4), 0.015, m["dark"])


def build(planet="nauvis"):
    rig.reset()
    m = materials(planet)
    hopper(m)
    underframe(m)
    ends(m)
    rig.sun()
    rig.fill_light()
    rig.camera(8, 8, shift_y=1.0)


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    frames = [int(x) for x in a[1:]] or list(range(128))
    build()
    rig.render_frames(out, frames, lambda i: i / 256, samples=32)
