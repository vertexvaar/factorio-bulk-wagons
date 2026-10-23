"""Kit-bash parts for the dense, worn industrial look of the Factorio 2.1 buildings:
riveted plates, I-beams, pipes with flanges, ribbed hoses, motors, gearboxes,
cabinets, handrails, ladders, gratings, cable runs and lamps.

All sizes are in tiles. Parts are built from rig primitives, so they get the
layer/mask tags and bevels like everything else.
"""
import math

from mathutils import Vector

import rig

PALETTE = None


def palette():
    """Shared materials, created once per scene."""
    global PALETTE
    if PALETTE is None:
        PALETTE = {
            "steel": rig.material("k_steel", (0.30, 0.30, 0.31), roughness=0.4, metallic=0.75, grime=0.45, rust=0.55),
            "dark": rig.material("k_dark", (0.07, 0.07, 0.075), roughness=0.5, metallic=0.5, grime=0.3, rust=0.35),
            "plate": rig.material("k_plate", (0.36, 0.37, 0.36), roughness=0.45, metallic=0.5, grime=0.5, scale=3, rust=0.7),
            "olive": rig.material("k_olive", (0.36, 0.40, 0.20), roughness=0.5, grime=0.5, scale=3, rust=0.75),
            "blue": rig.material("k_blue", (0.20, 0.30, 0.42), roughness=0.5, grime=0.5, scale=3, rust=0.7),
            "red": rig.material("k_red", (0.45, 0.13, 0.08), roughness=0.5, grime=0.5, scale=3, rust=0.7),
            "yellow": rig.material("k_yellow", (0.80, 0.58, 0.06), roughness=0.5, grime=0.5, rust=0.6),
            "copper": rig.material("k_copper", (0.62, 0.32, 0.16), roughness=0.35, metallic=0.9, grime=0.35, rust=0.25),
            "brass": rig.material("k_brass", (0.62, 0.45, 0.16), roughness=0.3, metallic=0.9, grime=0.3),
            "rubber": rig.material("k_rubber", (0.035, 0.035, 0.035), roughness=0.85, grime=0.2, bump=0.3),
            "concrete": rig.material("k_concrete", (0.42, 0.40, 0.37), roughness=0.9, grime=0.55, scale=4, bump=0.5),
            "chrome": rig.material("k_chrome", (0.6, 0.6, 0.6), roughness=0.25, metallic=1.0, grime=0.2),
            "glass": rig.material("k_glass", (0.25, 0.35, 0.4), roughness=0.1, metallic=0.3, grime=0.1),
            "green_lamp": rig.material("k_green_lamp", (0.3, 1.0, 0.4), emission=(0.2, 1.0, 0.3)),
            "amber_lamp": rig.material("k_amber_lamp", (1.0, 0.7, 0.3), emission=(1.0, 0.55, 0.15)),
            "red_lamp": rig.material("k_red_lamp", (1.0, 0.3, 0.2), emission=(1.0, 0.15, 0.1)),
            "cable_red": rig.material("k_cable_red", (0.5, 0.08, 0.06), roughness=0.6),
            "cable_green": rig.material("k_cable_green", (0.12, 0.4, 0.12), roughness=0.6),
            "cable_blue": rig.material("k_cable_blue", (0.1, 0.18, 0.45), roughness=0.6),
        }
    return PALETTE


def reset():
    global PALETTE
    PALETTE = None


_counter = [0]


def _n(prefix):
    _counter[0] += 1
    return f"{prefix}{_counter[0]}"


def V(p):
    return Vector(p)


def pivot(name, location):
    """An empty to hang moving parts on; children use coordinates relative to it."""
    import bpy
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = rig.root()
    obj.location = location
    obj["layer"] = rig.LAYER
    return obj


def attach(parent, *parts):
    for part in parts:
        part.parent = parent


# ------------------------------------------------------------------ small bits

def rivets(a, b, count, normal, mat=None, radius=0.016):
    """A row of rivet heads from a to b, sticking out along normal."""
    mat = mat or palette()["steel"]
    a, b, nrm = V(a), V(b), V(normal).normalized()
    for k in range(count):
        p = a + (b - a) * (k / max(1, count - 1))
        rig.cylinder(_n("rivet"), p - nrm * 0.004, p + nrm * 0.014, radius, mat, verts=8)


def bolts_around(center, normal, radius, count, mat=None):
    c, nrm = V(center), V(normal).normalized()
    side = nrm.orthogonal().normalized()
    up = nrm.cross(side)
    for k in range(count):
        a = 2 * math.pi * k / count
        p = c + (side * math.cos(a) + up * math.sin(a)) * radius
        rig.cylinder(_n("bolt"), p, p + nrm * 0.02, 0.014, mat or palette()["steel"], verts=6)


def lamp(position, color="amber", size=0.05):
    p = palette()
    rig.box(_n("lamp_base"), (position[0], position[1], position[2] - size * 0.6), (size * 1.6, size * 1.6, size * 0.5), p["dark"], bevel=0.005)
    rig.cylinder(_n("lamp"), (position[0], position[1], position[2] - size * 0.4), (position[0], position[1], position[2] + size * 0.5),
                 size * 0.6, p[color + "_lamp"], verts=12)


# ------------------------------------------------------------------ plates and beams

def plate(center, size, mat, rivet_edges=True, panels=1, axis="z"):
    """A riveted steel plate. axis is the plate normal; panels splits it with seam strips."""
    p = palette()
    c = V(center)
    rig.box(_n("plate"), c, size, mat, bevel=0.01)
    if not rivet_edges:
        return
    sx, sy, sz = (s / 2 for s in size)
    if axis == "z":
        n = Vector((0, 0, 1))
        top = c.z + sz
        corners = [(c.x - sx + 0.04, c.y - sy + 0.04), (c.x + sx - 0.04, c.y - sy + 0.04),
                   (c.x + sx - 0.04, c.y + sy - 0.04), (c.x - sx + 0.04, c.y + sy - 0.04)]
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            rivets((a[0], a[1], top), (b[0], b[1], top), max(2, int(length / 0.12)), n)
        for k in range(1, panels):
            x = c.x - sx + 2 * sx * k / panels
            rig.box(_n("seam"), (x, c.y, top + 0.005), (0.03, 2 * sy, 0.012), p["dark"], bevel=0)
    else:
        idx = {"x": 0, "y": 1}[axis]
        sign = 1
        n = Vector((1, 0, 0)) if axis == "x" else Vector((0, -1, 0))
        face = c.copy()
        face[idx] += (size[idx] / 2 + 0.002) * (1 if axis == "x" else -1)
        other = 1 - idx
        half_o = size[other] / 2 - 0.04
        lo, hi = c.z - sz + 0.04, c.z + sz - 0.04
        for zz in (lo, hi):
            a, b = face.copy(), face.copy()
            a[other] -= half_o
            b[other] += half_o
            a.z = b.z = zz
            rivets(a, b, max(2, int(2 * half_o / 0.12)), n)
        for oo in (-half_o, half_o):
            a, b = face.copy(), face.copy()
            a[other] += oo
            b[other] += oo
            a.z, b.z = lo, hi
            rivets(a, b, max(2, int((hi - lo) / 0.12)), n)


def ibeam(a, b, size=0.14, mat=None):
    """I-section girder from a to b (flanges top/bottom for horizontal beams)."""
    mat = mat or palette()["steel"]
    a, b = V(a), V(b)
    d = b - a
    mid = (a + b) / 2
    length = d.length
    q = d.to_track_quat("X", "Z")
    rot = q.to_euler()
    import bpy
    pivot = bpy.data.objects.new(_n("ibeam"), None)
    bpy.context.scene.collection.objects.link(pivot)
    pivot.parent = rig.root()
    pivot.location = mid
    pivot.rotation_euler = rot
    pivot["layer"] = rig.LAYER
    parts = [
        rig.box(_n("web"), (0, 0, 0), (length, size * 0.15, size), mat, bevel=0.005),
        rig.box(_n("flange"), (0, 0, size / 2), (length, size * 0.8, size * 0.15), mat, bevel=0.005),
        rig.box(_n("flange"), (0, 0, -size / 2), (length, size * 0.8, size * 0.15), mat, bevel=0.005),
    ]
    for part in parts:
        part.parent = pivot
    return pivot


def lattice(a, b, width, depth, segments, mat=None):
    """Box truss between a and b: four chords with diagonal lacing."""
    mat = mat or palette()["steel"]
    a, b = V(a), V(b)
    d = (b - a)
    axis = d.normalized()
    side = axis.cross(Vector((0, 0, 1)))
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    up = side.cross(axis).normalized()
    offs = [side * w + up * h for w in (-width / 2, width / 2) for h in (-depth / 2, depth / 2)]
    for o in offs:
        rig.cylinder(_n("chord"), a + o, b + o, 0.035, mat, verts=8)
    for k in range(segments):
        p0 = a + d * (k / segments)
        p1 = a + d * ((k + 1) / segments)
        for o1, o2 in ((offs[0], offs[1]), (offs[2], offs[3]), (offs[0], offs[2]), (offs[1], offs[3])):
            rig.cylinder(_n("lace"), p0 + o1, p1 + o2, 0.016, mat, verts=6)


# ------------------------------------------------------------------ pipes and hoses

def pipe(points, radius, mat=None, flanges=True):
    """Pipe run through points with ball joints and bolted flanges at every joint."""
    p = palette()
    mat = mat or p["steel"]
    pts = [V(x) for x in points]
    for i in range(len(pts) - 1):
        rig.cylinder(_n("pipe"), pts[i], pts[i + 1], radius, mat, verts=16)
    import bpy
    for i, q in enumerate(pts):
        if 0 < i < len(pts) - 1:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius * 1.02, location=q, segments=16, ring_count=8)
            ball = bpy.context.object
            ball.name = _n("elbow")
            rig._finish(ball, mat, 0, False)
        if flanges:
            nxt = pts[i + 1] if i + 1 < len(pts) else pts[i - 1]
            d = (nxt - q).normalized() * 0.03
            rig.cylinder(_n("flange"), q + d, q + d * 2, radius * 1.45, mat, verts=16)


def hose(points, radius, mat=None, ribs_per_tile=28):
    """Ribbed flexible hose (like the 2.1 pump arms): a core with rings along a smooth path."""
    p = palette()
    mat = mat or p["copper"]
    pts = [V(x) for x in points]
    # Catmull-Rom through the points
    path = []
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[i + 1]
        steps = max(4, int((p2 - p1).length * 12))
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            path.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    path.append(pts[-1])
    for i in range(len(path) - 1):
        rig.cylinder(_n("hose"), path[i], path[i + 1], radius * 0.8, p["dark"], verts=10)
    total = sum((path[i + 1] - path[i]).length for i in range(len(path) - 1))
    count = int(total * ribs_per_tile)
    import bpy
    acc, seg = 0.0, 0
    for k in range(count):
        target = total * k / count
        while seg < len(path) - 2 and acc + (path[seg + 1] - path[seg]).length < target:
            acc += (path[seg + 1] - path[seg]).length
            seg += 1
        a, b = path[seg], path[seg + 1]
        t = (target - acc) / max(1e-6, (b - a).length)
        pos = a + (b - a) * t
        d = (b - a).normalized()
        bpy.ops.mesh.primitive_torus_add(major_radius=radius * 0.85, minor_radius=radius * 0.22, location=pos,
                                         major_segments=12, minor_segments=6)
        ring = bpy.context.object
        ring.name = _n("rib")
        ring.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        rig._finish(ring, mat, 0, False)


def cable(points, color="red", radius=0.012):
    mat = palette()["cable_" + color]
    pts = [V(x) for x in points]
    for i in range(len(pts) - 1):
        rig.cylinder(_n("cable"), pts[i], pts[i + 1], radius, mat, verts=6)


# ------------------------------------------------------------------ machinery

def motor(center, axis="x", length=0.5, radius=0.16, mat=None):
    """Electric motor: finned body, end bell, shaft stub and terminal box."""
    p = palette()
    mat = mat or p["blue"]
    c = V(center)
    d = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}[axis]
    a, b = c - d * length / 2, c + d * length / 2
    rig.cylinder(_n("motor"), a, b, radius, mat, verts=24)
    side = d.orthogonal().normalized()
    up = d.cross(side)
    for k in range(12):
        ang = 2 * math.pi * k / 12
        o = (side * math.cos(ang) + up * math.sin(ang)) * radius
        rig.cylinder(_n("fin"), a + o * 1.0 + d * 0.04, b + o * 1.0 - d * 0.04, 0.012, mat, verts=4)
    rig.cylinder(_n("bell"), b, b + d * 0.06, radius * 0.9, p["dark"], verts=24)
    rig.cylinder(_n("shaft"), b + d * 0.06, b + d * 0.14, radius * 0.18, p["chrome"], verts=12)
    rig.cylinder(_n("fan_cover"), a - d * 0.05, a, radius * 0.95, p["steel"], verts=24)
    tb = c + Vector((0, 0, radius + 0.04))
    rig.box(_n("terminal"), tb, (0.12, 0.12, 0.08), mat, bevel=0.008)
    bolts_around(a - d * 0.05, -d, radius * 0.6, 6)
    return b + d * 0.14


def gearbox(center, size=(0.4, 0.35, 0.35), mat=None):
    p = palette()
    mat = mat or p["olive"]
    c = V(center)
    rig.box(_n("gearbox"), c, size, mat, bevel=0.02)
    for k in range(5):
        x = c.x - size[0] / 2 + 0.05 + k * (size[0] - 0.1) / 4
        rig.box(_n("gb_rib"), (x, c.y - size[1] / 2 - 0.01, c.z), (0.025, 0.02, size[2] * 0.85), mat, bevel=0)
    rig.cylinder(_n("gb_cap"), (c.x, c.y, c.z + size[2] / 2), (c.x, c.y, c.z + size[2] / 2 + 0.04), 0.06, p["dark"], verts=12)
    rivets((c.x - size[0] / 2 + 0.04, c.y - size[1] / 2 - 0.005, c.z + size[2] / 2 - 0.03),
           (c.x + size[0] / 2 - 0.04, c.y - size[1] / 2 - 0.005, c.z + size[2] / 2 - 0.03), 5, (0, -1, 0))


def cabinet(center, size=(0.4, 0.22, 0.6), facing="-y", mat=None):
    """Electrical cabinet with door seams, handle, gauges and indicator lamps."""
    p = palette()
    mat = mat or p["olive"]
    c = V(center)
    rig.box(_n("cabinet"), c, size, mat, bevel=0.015)
    front = c.y - size[1] / 2 - 0.006 if facing == "-y" else c.y + size[1] / 2 + 0.006
    rig.box(_n("door_seam"), (c.x, front, c.z), (0.012, 0.01, size[2] * 0.9), p["dark"], bevel=0)
    rig.box(_n("handle"), (c.x + 0.05, front, c.z), (0.02, 0.02, 0.1), p["chrome"], bevel=0)
    for k, col in enumerate(("green", "amber", "red")):
        lamp((c.x - size[0] / 2 + 0.07 + k * 0.07, front, c.z + size[2] / 2 - 0.08), col, size=0.025)
    rig.cylinder(_n("gauge"), (c.x - 0.1, front, c.z), (c.x - 0.1, front - 0.01, c.z), 0.045, p["glass"], verts=16)
    rig.box(_n("cab_roof"), (c.x, c.y, c.z + size[2] / 2 + 0.015), (size[0] + 0.06, size[1] + 0.06, 0.03), p["dark"], bevel=0.005)


def fan(center, radius=0.18, axis="z"):
    """Vent fan with blades behind a grille."""
    p = palette()
    c = V(center)
    d = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}[axis]
    rig.cylinder(_n("fan_ring"), c - d * 0.04, c + d * 0.02, radius * 1.1, p["dark"], verts=24)
    import bpy
    bpy.ops.mesh.primitive_torus_add(major_radius=radius * 1.08, minor_radius=0.02, location=c + d * 0.02,
                                     major_segments=24, minor_segments=6)
    ring = bpy.context.object
    ring.name = _n("fan_rim")
    ring.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    rig._finish(ring, p["steel"], 0, False)
    for k in range(7):
        ang = 2 * math.pi * k / 7
        side = d.orthogonal().normalized()
        up = d.cross(side)
        o = (side * math.cos(ang) + up * math.sin(ang)) * radius * 0.55
        rig.box(_n("blade"), c + o + d * 0.025, (radius * 0.85, 0.05, 0.01), p["steel"], bevel=0, rotation=(0, 0.3, ang))
    rig.cylinder(_n("hub"), c, c + d * 0.05, radius * 0.25, p["chrome"], verts=12)


# ------------------------------------------------------------------ access

def handrail(points, height=0.45, mat=None, posts_every=0.45):
    """Handrail with top and knee rail along a polyline at floor level, posts in between."""
    mat = mat or palette()["yellow"]
    pts = [V(x) for x in points]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        up = Vector((0, 0, height))
        rig.cylinder(_n("rail_top"), a + up, b + up, 0.018, mat, verts=8)
        rig.cylinder(_n("rail_knee"), a + up * 0.5, b + up * 0.5, 0.012, mat, verts=8)
        n = max(1, int((b - a).length / posts_every))
        for k in range(n + 1):
            q = a + (b - a) * (k / n)
            rig.cylinder(_n("post"), q, q + up, 0.016, mat, verts=8)
        if abs(b.z - a.z) < 0.01:  # toe board only on level runs
            rig.box(_n("kick"), (a + b) / 2 + Vector((0, 0, 0.04)), (max(0.02, abs(b.x - a.x)), max(0.02, abs(b.y - a.y)), 0.07), mat,
                    bevel=0)


def ladder(bottom, top, width=0.36, cage=False, mat=None):
    mat = mat or palette()["yellow"]
    b, t = V(bottom), V(top)
    for s in (-1, 1):
        o = Vector((width / 2 * s, 0, 0)) if abs(t.y - b.y) >= abs(t.x - b.x) or abs(t.x - b.x) < 0.01 else Vector((0, width / 2 * s, 0))
        rig.cylinder(_n("ladder_rail"), b + o, t + o + Vector((0, 0, 0.25)), 0.016, mat, verts=8)
    o = Vector((width / 2, 0, 0))
    n = int((t - b).length / 0.22)
    for k in range(1, n + 1):
        q = b + (t - b) * (k / (n + 1))
        rig.cylinder(_n("rung"), q - o, q + o, 0.011, mat, verts=6)
    if cage:
        for k in range(int((t - b).length / 0.4)):
            q = b + (t - b) * ((k + 1) / (int((t - b).length / 0.4) + 1)) + Vector((0, -0.18, 0))
            import bpy
            bpy.ops.mesh.primitive_torus_add(major_radius=width * 0.62, minor_radius=0.01, location=q, major_segments=16, minor_segments=4)
            hoop = bpy.context.object
            hoop.name = _n("hoop")
            rig._finish(hoop, mat, 0, False)


def grating(center, size, bar_every=0.1, mat=None):
    """Open floor grating: frame plus bars, light can fall through."""
    mat = mat or palette()["steel"]
    c = V(center)
    sx, sy = size[0] / 2, size[1] / 2
    for y in (-sy, sy):
        rig.box(_n("grate_frame"), (c.x, c.y + y, c.z), (2 * sx, 0.04, 0.05), mat, bevel=0.004)
    for x in (-sx, sx):
        rig.box(_n("grate_frame"), (c.x + x, c.y, c.z), (0.04, 2 * sy, 0.05), mat, bevel=0.004)
    n = int(2 * sx / bar_every)
    for k in range(1, n):
        rig.box(_n("grate_bar"), (c.x - sx + k * 2 * sx / n, c.y, c.z), (0.018, 2 * sy, 0.045), mat, bevel=0)
    m = max(1, int(2 * sy / 0.35))
    for k in range(1, m):
        rig.box(_n("grate_tie"), (c.x, c.y - sy + k * 2 * sy / m, c.z - 0.005), (2 * sx, 0.015, 0.035), mat, bevel=0)


def hazard(center, size, stripes=6, axis="x"):
    """Yellow/black hazard stripes on a thin plate."""
    p = palette()
    c = V(center)
    rig.box(_n("hazard_base"), c, size, p["dark"], bevel=0)
    if axis == "x":
        w = size[0] / (2 * stripes)
        for k in range(stripes):
            rig.box(_n("hazard"), (c.x - size[0] / 2 + w * (2 * k + 0.5), c.y, c.z + size[2] / 2 + 0.002),
                    (w, size[1] * 0.98, 0.006), p["yellow"], bevel=0, rotation=(0, 0, 0.5))
    else:
        w = size[1] / (2 * stripes)
        for k in range(stripes):
            rig.box(_n("hazard"), (c.x, c.y - size[1] / 2 + w * (2 * k + 0.5), c.z + size[2] / 2 + 0.002),
                    (size[0] * 0.98, w, 0.006), p["yellow"], bevel=0, rotation=(0, 0, 0.5))


def footing(x, y, size=(0.4, 0.4), height=0.14):
    p = palette()
    rig.box(_n("footing"), (x, y, height / 2), (size[0], size[1], height), p["concrete"], bevel=0.02)
    rig.box(_n("baseplate"), (x, y, height + 0.01), (size[0] * 0.75, size[1] * 0.75, 0.02), p["steel"], bevel=0.004)
    for dx in (-1, 1):
        for dy in (-1, 1):
            q = (x + dx * size[0] * 0.28, y + dy * size[1] * 0.28, height + 0.02)
            rig.cylinder(_n("anchor"), q, (q[0], q[1], q[2] + 0.04), 0.018, p["steel"], verts=6)
