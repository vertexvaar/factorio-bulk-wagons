"""Item icons of the 0.5 bulk connectors: the bunker elevator or the silo conveyor of
connector_v2.py, seen from the south-west at a lower angle than in game so the casing
fills the icon. The painted parts take the belt tier's colour (build_sprites.py
tints them).

Run:  blender -b --factory-startup -P tools/blender/connector_icon.py -- <out_dir> <bunker|silo> [azimuth]
Renders color_000 and mask_000, square, 256 px.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import connector_v2  # noqa: E402
import kit  # noqa: E402
import rig  # noqa: E402

AZIMUTH = {"bunker": 330, "silo": 330}  # degrees around z; 0 looks from the station side (south), 330 from the south-west
ELEVATION = 32
SIZE = 256


def frame(azimuth):
    """Square orthographic camera looking at the model from the azimuth, fitted to it."""
    import bpy
    from mathutils import Euler, Vector
    scene = bpy.context.scene
    rot = Euler((math.radians(90 - ELEVATION), 0, math.radians(azimuth)))
    forward = Vector((0, 0, -1))
    forward.rotate(rot)
    right, up = Vector((1, 0, 0)), Vector((0, 1, 0))
    right.rotate(rot)
    up.rotate(rot)
    points = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == "MESH" and o.visible_camera
              and o.name != "shadow_catcher" for c in o.bound_box]
    xs, ys = [p.dot(right) for p in points], [p.dot(up) for p in points]
    centre = right * (min(xs) + max(xs)) / 2 + up * (min(ys) + max(ys)) / 2
    data = bpy.data.cameras.new("icon_cam")
    data.type = "ORTHO"
    data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.04
    cam = bpy.data.objects.new("icon_cam", data)
    cam.location = centre - forward * 50
    cam.rotation_euler = rot
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene["framing"] = [1, 1, 0]


if __name__ == "__main__":
    a = rig.args()
    out, kind = a[0], a[1]
    azimuth = float(a[2]) if len(a) > 2 else AZIMUTH[kind]
    rig.reset()
    kit.reset()
    p = kit.palette()
    rig.layer("base")
    connector_v2.BUILDERS[kind](p)
    rig.sun()
    rig.fill_light()
    frame(azimuth)
    rig.render_frames(out, [0], lambda i: 0, passes=("color", "mask"), samples=64)
