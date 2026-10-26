"""Unloading bunker (0.4.0): a riveted bunker under the track over a whole wagon slot.
Three hoppers under the rail bridge catch what falls through the wagon's flaps; walkable
gratings either side cover the feeders that carry the goods out to six outlet hatches
on each long side, where bulk connectors dock. Hydraulic arms open the wagon's flaps.

Run:  blender -b --factory-startup -P tools/blender/station_bunker.py -- <out_dir> [variants...]
Footprint for variant 1: 6 x 6 tiles, rail north-south through x in [-1, 1]. Variant 2
is the same model turned a quarter (rail east-west).

Renders per variant: base (everything on the ground, drawn under the rails), shadow,
idle (the moving parts at rest), extend_000..007 (flap openers rise, played once) and
work_000..007 (openers up, beacon turning). Each with a *_mask twin for the station
colour; top_static_000 is the idle top without its moving parts.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kit  # noqa: E402
import rig  # noqa: E402
import station_e1 as e1  # noqa: E402  (material helpers)

ANIM_FRAMES = 8
EXTEND_FRAMES = 8
DEPTH = -0.9
BAYS = (-1.95, 0.0, 1.95)  # compartment centres along the track
OPEN = 2.0  # half width of the open part (track and gratings)
EDGE = 3.0

openers = []  # (pivot, side)
beacon = []


def ground():
    """Holdout at ground level with a hole over the open part, so whatever lies below
    ground outside it stays hidden, as in the real ground."""
    import bpy
    mat = bpy.data.materials.new("ground_holdout")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    ho = nt.nodes.new("ShaderNodeHoldout")
    nt.links.new(ho.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    ox, oy, ix, iy, z = 6.0, 6.0, OPEN, 2.8, -0.001
    verts = [(-ox, -oy, z), (ox, -oy, z), (ox, oy, z), (-ox, oy, z), (-ix, -iy, z), (ix, -iy, z), (ix, iy, z), (-ix, iy, z)]
    faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = rig.mesh("ground", verts, faces, mat)
    obj.visible_shadow = False


def haze():
    """Dims everything below ground: the bunker's insides are only hinted at."""
    mat = e1._alpha_material("haze", lambda nt, coord: (None, 0.58))
    obj = rig.mesh("haze", [(-OPEN, -2.8, -0.08), (OPEN, -2.8, -0.08), (OPEN, 2.8, -0.08), (-OPEN, 2.8, -0.08)],
                   [(0, 1, 2, 3)], mat)
    obj.visible_shadow = False


def fringe():
    """A little gravel along the long sides, fading into the ground; none at the ends,
    where the next wagon slot's building follows."""
    def build(nt, coord):
        xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Object"], xyz.inputs[0])
        ax = e1._math(nt, "ABSOLUTE", xyz.outputs["X"])
        ay = e1._math(nt, "ABSOLUTE", xyz.outputs["Y"])
        out_x = e1._math(nt, "MAXIMUM", e1._math(nt, "SUBTRACT", ax, 2.95), 0.0)
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 3.5
        noise.inputs["Detail"].default_value = 6
        nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
        ragged = e1._math(nt, "ADD", out_x, e1._math(nt, "MULTIPLY", e1._math(nt, "SUBTRACT", noise.outputs["Fac"], 0.5), 0.3))
        fade = e1._math(nt, "SUBTRACT", 1.0, e1._math(nt, "DIVIDE", ragged, 0.35))
        fade.node.use_clamp = True
        beside = e1._math(nt, "MULTIPLY", e1._math(nt, "GREATER_THAN", ax, 2.95), e1._math(nt, "LESS_THAN", ay, 3.0))
        alpha = e1._math(nt, "MULTIPLY", fade, beside)
        stones = nt.nodes.new("ShaderNodeTexVoronoi")
        stones.inputs["Scale"].default_value = 26
        nt.links.new(coord.outputs["Object"], stones.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.16, 0.155, 0.15, 1)
        ramp.color_ramp.elements[1].position = 0.55
        ramp.color_ramp.elements[1].color = (0.035, 0.03, 0.025, 1)
        nt.links.new(stones.outputs["Distance"], ramp.inputs["Fac"])
        return ramp.outputs["Color"], alpha
    mat = e1._alpha_material("fringe", build)
    rig.mesh("fringe", [(-3.6, -3, 0.004), (3.6, -3, 0.004), (3.6, 3, 0.004), (-3.6, 3, 0.004)], [(0, 1, 2, 3)], mat)


def rim(p):
    """Concrete rims along the long sides with riveted cover plates, six outlet hatches
    each on the outer edge (one per tile, where connectors dock), sills at the ends."""
    for sx in (-1, 1):
        cx = sx * (OPEN + EDGE) / 2
        rig.box(f"rim{sx}", (cx, 0, -0.12), (EDGE - OPEN, 6.0, 0.24), p["concrete"], bevel=0.01)
        kit.plate((sx * 2.3, 0, 0.012), (0.6, 5.96, 0.02), p["olive"], panels=6)
        kit.hazard((sx * (OPEN + 0.03), 0, 0.02), (0.05, 5.9, 0.03), stripes=30, axis="y")
        for k in range(6):
            y = -2.5 + k
            # outlet hatch: a sloped hood over the feeder end, open to the outside
            hx = sx * 2.78
            rig.box(f"outlet{sx}{k}", (hx, y, 0.14), (0.4, 0.74, 0.26), p["yellow"], bevel=0.02)
            rig.box(f"outlet_mouth{sx}{k}", (sx * 2.985, y, 0.12), (0.02, 0.56, 0.16), p["dark"], bevel=0)
            rig.box(f"outlet_lid{sx}{k}", (hx - sx * 0.05, y, 0.29), (0.32, 0.7, 0.04), p["olive"], bevel=0.01, mask=True)
            kit.rivets((hx - sx * 0.12, y - 0.3, 0.315), (hx - sx * 0.12, y + 0.3, 0.315), 5, (0, 0, 1))
            if k % 2 == 0:
                kit.motor((sx * 2.33, y + 0.5, 0.14), axis="x", length=0.26, radius=0.08)
    for sy in (-1, 1):
        rig.box(f"sill{sy}", (0, sy * 2.9, -0.1), (2 * OPEN, 0.2, 0.2), p["concrete"], bevel=0.01)
        kit.ibeam((-OPEN, sy * 2.8, -0.03), (OPEN, sy * 2.8, -0.03), size=0.06)


def hoppers(p):
    """Three steel hoppers under the track, one per compartment, and the feeders that
    run under the gratings to the outlets."""
    for k, cy in enumerate(BAYS):
        y0, y1 = cy - 0.95, cy + 0.95
        rig.mesh(f"hopper{k}", [
            (-OPEN, y0, 0), (OPEN, y0, 0), (OPEN, y1, 0), (-OPEN, y1, 0),
            (-0.35, cy - 0.3, DEPTH), (0.35, cy - 0.3, DEPTH), (0.35, cy + 0.3, DEPTH), (-0.35, cy + 0.3, DEPTH),
        ], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0), (4, 7, 6, 5)], p["plate"])
        for t in (-0.5, 0.0, 0.5):
            for sx in (-1, 1):
                rig.cylinder(f"hopper_rib{k}{t}{sx}", (sx * OPEN, cy + t * 1.6, -0.01), (sx * 0.35, cy + t * 0.5, DEPTH + 0.01),
                             0.022, p["steel"], verts=6)
        # feeder troughs from the hopper outlet out under each grating
        for sx in (-1, 1):
            rig.box(f"feeder{k}{sx}", (sx * 1.45, cy, DEPTH + 0.35), (1.6, 0.42, 0.18), p["olive"], bevel=0.02)
            rig.cylinder(f"screw{k}{sx}", (sx * 0.5, cy, DEPTH + 0.47), (sx * 2.2, cy, DEPTH + 0.47), 0.06, p["chrome"], verts=10)
            kit.motor((sx * 2.0, cy + 0.3, DEPTH + 0.45), axis="x", length=0.24, radius=0.07)
        rig.box(f"residue{k}", (0, cy, DEPTH + 0.06), (0.6, 0.5, 0.1), p["concrete"], bevel=0.04)


def bridge_and_gratings(p):
    """Rail bridge over the hoppers, walkable gratings on I-beams over the side bays."""
    for x in (-0.55, 0.55):
        kit.ibeam((x, -3.0, -0.14), (x, 3.0, -0.14), size=0.24)
    for y in (-2.9, -0.97, 0.97, 2.9):
        kit.ibeam((-OPEN, y, -0.36), (OPEN, y, -0.36), size=0.16)
    for sx in (-1, 1):
        cx = sx * 1.5
        kit.grating((cx, 0, 0.02), (0.96, 5.8), bar_every=0.09)
        for y in (-1.95, 0.0, 1.95):
            kit.ibeam((cx, y - 0.95, -0.06), (cx, y + 0.95, -0.06), size=0.08)


def machinery(p):
    """Hydraulic power unit and cabinet on the rims, warning beacon, flap openers."""
    rig.cylinder("hpu_tank", (-2.45, 2.15, 0.2), (-2.45, 2.65, 0.2), 0.15, p["red"], verts=24)
    rig.box("hpu_frame", (-2.45, 2.4, 0.06), (0.4, 0.62, 0.06), p["dark"])
    kit.lamp((-2.25, 2.7, 0.33), "green")
    kit.cabinet((2.35, 2.55, 0.32), (0.34, 0.18, 0.5), facing="-x")
    kit.cable([(2.3, 2.45, 0.5), (2.2, 2.2, 0.2), (2.1, 1.9, 0.05)], "red")
    kit.hose([(-2.45, 2.1, 0.2), (-2.1, 1.6, 0.05), (-1.25, 1.95, 0.1)], 0.025, p["rubber"], ribs_per_tile=18)
    rig.cylinder("beacon_post", (2.45, -2.6, 0.02), (2.45, -2.6, 0.62), 0.025, p["steel"])
    rig.layer("top")
    rig.cylinder("beacon_glass", (2.45, -2.6, 0.62), (2.45, -2.6, 0.74), 0.06, p["amber_lamp"], verts=16)
    beacon.append(rig.gear("beacon_reflector", (2.45, -2.6, 0.68), 0.035, 0.1, 2, p["chrome"], axis="z"))
    # flap openers: yellow arms either side of the track, one per compartment and side,
    # that swing up against the wagon's flap levers while it unloads
    for sx in (-1, 1):
        for cy in BAYS:
            rig.box(f"opener_base{sx}{cy}", (sx * 1.15, cy, 0.08), (0.16, 0.16, 0.1), p["dark"])
            hinge = kit.pivot(f"opener{sx}{cy}", (sx * 1.15, cy, 0.14))
            kit.attach(hinge,
                       rig.cylinder(f"opener_body{sx}{cy}", (0, 0, 0), (0, 0, 0.32), 0.045, p["yellow"]),
                       rig.cylinder(f"opener_rod{sx}{cy}", (0, 0, 0.32), (0, 0, 0.5), 0.022, p["chrome"]),
                       rig.box(f"opener_head{sx}{cy}", (0, 0, 0.52), (0.1, 0.1, 0.04), p["dark"]))
            openers.append((hinge, sx))
    rig.layer("base")


def build():
    rig.reset()
    kit.reset()
    p = kit.palette()
    rig.layer("base")
    ground()
    fringe()
    haze()
    rim(p)
    hoppers(p)
    bridge_and_gratings(p)
    machinery(p)
    rig.sun()
    rig.fill_light()
    rig.camera(8, 8, shift_y=0.3)


def set_openers(raised):
    """0 = folded flat outwards, 1 = standing up against the wagon."""
    for hinge, sx in openers:
        hinge.rotation_euler = (0, sx * (1 - raised) * 1.35, 0)


def turn_beacon(frame):
    for pivot in beacon:
        pivot.rotation_euler[2] = 2 * math.pi * frame / ANIM_FRAMES


def render_variant(out, v):
    d = os.path.join(out, f"v{v}")
    orient = (v - 1) / 4
    set_openers(0)
    turn_beacon(0)
    rig.mark_moving([hinge for hinge, _ in openers] + beacon)
    rig.render_frames(d, [0], lambda i: orient, passes=("base", "base_mask", "shadow", "top", "top_mask", "top_static"),
                      samples=32)
    rig.rename(d, "top", "idle", 1)
    rig.render_frames(d, list(range(EXTEND_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: set_openers((i + 1) / EXTEND_FRAMES))
    rig.rename(d, "top", "extend", EXTEND_FRAMES)
    rig.render_frames(d, list(range(ANIM_FRAMES)), lambda i: orient, passes=("top", "top_mask"), samples=32,
                      pose=lambda i: (set_openers(1), turn_beacon(i)))
    rig.rename(d, "top", "work", ANIM_FRAMES)


if __name__ == "__main__":
    a = rig.args()
    out = a[0]
    variants = [int(x) for x in a[1:]] or [1, 2]
    build()
    for v in variants:
        render_variant(out, v)
