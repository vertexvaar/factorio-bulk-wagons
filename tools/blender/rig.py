"""Shared Blender rig for rendering Factorio-style sprites.

Factorio sprites are plain orthographic renders from roughly 50 degrees elevation
(fitted against the bounding boxes of the vanilla cargo wagon frames).
One world unit is one tile, 64 px per tile at the final size.

Passes per frame:
  color  - the lit sprite, transparent background
  mask   - white where the runtime tint (train colour) applies, else transparent
  shadow - only the shadow the object throws on the ground
"""
import math
import os
import sys

import bpy
from mathutils import Vector

TILE_PX = 64
ELEVATION = math.radians(50)
SQRT2 = math.sqrt(2)


def args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.62, 0.66, 0.75, 1)
    bg.inputs[1].default_value = 0.28
    scene.world = world
    return scene


def camera(width_tiles, height_tiles, supersample=2, shift_y=0.0):
    """Orthographic camera centred on the world origin (ground level), moved up by shift_y tiles on screen."""
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = width_tiles
    cam_data.sensor_fit = "HORIZONTAL"
    cam = bpy.data.objects.new("cam", cam_data)
    distance = 50
    cam.location = (0, -distance * math.cos(ELEVATION), distance * math.sin(ELEVATION))
    cam.rotation_euler = (math.pi / 2 - ELEVATION, 0, 0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = round(width_tiles * TILE_PX * supersample)
    scene.render.resolution_y = round(height_tiles * TILE_PX * supersample)
    cam_data.shift_y = shift_y / height_tiles * (height_tiles / width_tiles)
    scene.render.resolution_percentage = 100
    return cam


def sun(strength=3.8):
    """Factorio light: from the upper left, shadows fall to the right."""
    data = bpy.data.lights.new("sun", "SUN")
    data.energy = strength
    data.angle = math.radians(3)
    data.color = (1.0, 0.96, 0.9)
    obj = bpy.data.objects.new("sun", data)
    direction = Vector((0.75, -0.4, -1.6)).normalized()  # direction the light travels
    obj.rotation_euler = (-direction).to_track_quat("Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(obj)
    return obj


def fill_light(strength=0.6):
    """Cool, weak back light from the lower right so dark sides keep their shape."""
    data = bpy.data.lights.new("fill", "SUN")
    data.energy = strength
    data.angle = math.radians(10)
    data.color = (0.75, 0.82, 1.0)
    data.use_shadow = False
    obj = bpy.data.objects.new("fill", data)
    direction = Vector((-0.8, 0.6, -0.5)).normalized()
    obj.rotation_euler = (-direction).to_track_quat("Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(obj)
    return obj


def shadow_catcher(size=40):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "shadow_catcher"
    plane.is_shadow_catcher = True
    plane.hide_render = True
    return plane


# ---------------------------------------------------------------- materials

def material(name, color, roughness=0.5, metallic=0.0, grime=0.25, scale=6.0, bump=0.15, emission=None):
    """Principled material with procedural grime and grain, so flat surfaces read as worn metal."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (1 - grime, 1 - grime, 1 - grime, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    # darker in crevices (ambient occlusion), lighter on edges (pointiness)
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.15
    ao_ramp = nt.nodes.new("ShaderNodeMapRange")
    ao_ramp.inputs["To Min"].default_value = 0.4
    nt.links.new(ao.outputs["AO"], ao_ramp.inputs["Value"])

    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs[0].default_value = (*color, 1)
    mix1 = nt.nodes.new("ShaderNodeMix")
    mix1.data_type = "RGBA"
    mix1.blend_type = "MULTIPLY"
    mix1.inputs["Factor"].default_value = 1.0
    nt.links.new(base.outputs[0], mix1.inputs["A"])
    nt.links.new(ramp.outputs["Color"], mix1.inputs["B"])
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    mix2.blend_type = "MULTIPLY"
    mix2.inputs["Factor"].default_value = 1.0
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    nt.links.new(ao_ramp.outputs["Result"], mix2.inputs["B"])
    nt.links.new(mix2.outputs["Result"], bsdf.inputs["Base Color"])

    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = scale * 12
    nt.links.new(coord.outputs["Object"], grain.inputs["Vector"])
    bump_node = nt.nodes.new("ShaderNodeBump")
    bump_node.inputs["Strength"].default_value = bump
    nt.links.new(grain.outputs["Fac"], bump_node.inputs["Height"])
    # rounded shading normals catch crisp highlights on every edge, like hand-finished sprites
    edge = nt.nodes.new("ShaderNodeBevel")
    edge.samples = 8
    edge.inputs["Radius"].default_value = 0.025
    nt.links.new(bump_node.outputs["Normal"], edge.inputs["Normal"])
    nt.links.new(edge.outputs["Normal"], bsdf.inputs["Normal"])

    # vertical streaks of dirt and wear
    streak_coord = nt.nodes.new("ShaderNodeMapping")
    streak_coord.inputs["Scale"].default_value = (30, 30, 1.5)
    nt.links.new(coord.outputs["Object"], streak_coord.inputs["Vector"])
    streaks = nt.nodes.new("ShaderNodeTexNoise")
    streaks.inputs["Scale"].default_value = 1.0
    nt.links.new(streak_coord.outputs["Vector"], streaks.inputs["Vector"])
    streak_ramp = nt.nodes.new("ShaderNodeMapRange")
    streak_ramp.inputs["To Min"].default_value = 1 - grime * 0.6
    nt.links.new(streaks.outputs["Fac"], streak_ramp.inputs["Value"])
    mix3 = nt.nodes.new("ShaderNodeMix")
    mix3.data_type = "RGBA"
    mix3.blend_type = "MULTIPLY"
    mix3.inputs["Factor"].default_value = 1.0
    nt.links.new(mix2.outputs["Result"], mix3.inputs["A"])
    nt.links.new(streak_ramp.outputs["Result"], mix3.inputs["B"])
    nt.links.new(mix3.outputs["Result"], bsdf.inputs["Base Color"])

    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 6
    return mat


# ---------------------------------------------------------------- geometry

ROOT = None
LAYER = "base"  # objects created while LAYER == "top" go to the overhead sprite


def layer(name):
    global LAYER
    LAYER = name


def root():
    global ROOT
    if ROOT is None:
        ROOT = bpy.data.objects.new("root", None)
        bpy.context.scene.collection.objects.link(ROOT)
    return ROOT


def _finish(obj, mat, bevel, mask):
    for m in (mat if isinstance(mat, list) else [mat]):
        obj.data.materials.append(m)
    if bevel:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    obj.parent = root()
    obj["layer"] = LAYER
    obj["mask"] = mask if isinstance(mask, int) and not isinstance(mask, bool) else bool(mask)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def mesh(name, verts, faces, mat, bevel=0.0, mask=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return _finish(obj, mat, bevel, mask)


def box(name, center, size, mat, bevel=0.012, mask=False, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(obj, mat, bevel, mask)


def cylinder(name, p1, p2, radius, mat, verts=16, bevel=0.0, mask=False):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=d.length, location=(p1 + p2) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    obj.location = (p1 + p2) / 2
    obj = _finish(obj, mat, bevel, mask)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def torus(name, center, major, minor, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=center, rotation=rotation,
                                     major_segments=24, minor_segments=8)
    obj = bpy.context.object
    obj.name = name
    obj = _finish(obj, mat, 0, False)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def gear(name, center, radius, thickness, teeth, mat, axis="y"):
    """Spur gear: a disc with box teeth, parented to an empty so it can spin. Returns the empty."""
    pivot = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(pivot)
    pivot.parent = root()
    pivot.location = center
    if axis == "x":
        pivot.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "y":
        pivot.rotation_euler = (math.pi / 2, 0, 0)
    parts = [cylinder(f"{name}_disc", (0, 0, -thickness / 2), (0, 0, thickness / 2), radius, mat, verts=32)]
    parts.append(cylinder(f"{name}_hub", (0, 0, -thickness), (0, 0, thickness), radius * 0.28, mat, verts=16))
    tooth = 2 * math.pi * radius / teeth * 0.5
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        parts.append(box(f"{name}_t{k}", (math.cos(a) * (radius + tooth * 0.4), math.sin(a) * (radius + tooth * 0.4), 0),
                         (tooth * 0.9, tooth, thickness), mat, bevel=0, rotation=(0, 0, a)))
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        parts.append(cylinder(f"{name}_hole{k}", (math.cos(a) * radius * 0.6, math.sin(a) * radius * 0.6, -thickness * 0.6),
                              (math.cos(a) * radius * 0.6, math.sin(a) * radius * 0.6, thickness * 0.6), radius * 0.16,
                              bpy.data.materials.get("dark") or mat, verts=12))
    for part in parts:
        part.parent = pivot
    pivot["layer"] = LAYER
    return pivot


def tube_path(name, points, radius, mat):
    """A bent rod (railing, ladder rail) through the given points."""
    objs = []
    for i in range(len(points) - 1):
        objs.append(cylinder(f"{name}_{i}", points[i], points[i + 1], radius, mat, verts=10))
    return objs


# ---------------------------------------------------------------- rendering

def _set_mask_mode(enabled, white, holdout):
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name == "shadow_catcher":
            continue
        if enabled:
            if "orig_mats" not in obj:
                obj["orig_mats"] = [m.name for m in obj.data.materials]
            # "mask" marks the masked material slots: True = all, an int = only slot 0..n-1
            masked = obj.get("mask")
            for i in range(len(obj.data.materials)):
                tinted = masked is True or masked == 1 and i == 0
                obj.data.materials[i] = white if tinted else holdout
        elif "orig_mats" in obj:
            for i, name in enumerate(obj["orig_mats"]):
                obj.data.materials[i] = bpy.data.materials[name]


def _mask_materials():
    white = bpy.data.materials.new("mask_white")
    white.use_nodes = True
    nt = white.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    holdout = bpy.data.materials.new("mask_holdout")
    holdout.use_nodes = True
    nt = holdout.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    ho = nt.nodes.new("ShaderNodeHoldout")
    nt.links.new(ho.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return white, holdout


FRONT_Y = -1.05  # anything south of the track is in front of passing trains


def _layer_of(obj):
    """Overhead parts, and everything standing south of the track (in front of a
    passing train on screen), go to the top sprite; the rest stays below trains."""
    if obj.get("layer") == "top" or obj.get("hide_in") == "base":
        return "top"
    centre = sum((obj.matrix_world @ Vector(c) for c in obj.bound_box), Vector()) / 8
    return "top" if centre.y < FRONT_Y and centre.z > 0.25 else "base"


def render_frames(out_dir, frames, orientation_of, passes=("color", "mask", "shadow"), samples=48, pose=None):
    """Renders each frame index; orientation_of(i) gives the Factorio orientation (0..1, clockwise from north).

    Passes: color, mask, shadow, plus base/top which split the color pass into the
    parts on the ground and the overhead parts (drawn above trains in game).

    pose(i), if given, is called before rendering frame i to set up animated parts.
    """
    os.makedirs(out_dir, exist_ok=True)
    scene = bpy.context.scene
    catcher = bpy.data.objects.get("shadow_catcher") or shadow_catcher()
    white, holdout = _mask_materials()
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name != "shadow_catcher"]
    for i in frames:
        root().rotation_euler = (0, 0, -orientation_of(i) * 2 * math.pi)
        if pose:
            pose(i)
        for kind in passes:
            catcher.hide_render = kind != "shadow"
            for o in meshes:
                if kind == "shadow":
                    o.visible_camera = False
                elif kind in ("base", "top"):
                    o.visible_camera = _layer_of(o) == kind
                elif kind == "hidden":
                    o.visible_camera = False
                else:
                    o.visible_camera = True
            _set_mask_mode(kind == "mask", white, holdout)
            scene.cycles.samples = {"mask": 4, "shadow": 16}.get(kind, samples)
            scene.cycles.use_denoising = kind != "mask"
            scene.render.filepath = os.path.join(out_dir, f"{kind}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
        _set_mask_mode(False, white, holdout)
        for o in meshes:
            o.visible_camera = True
