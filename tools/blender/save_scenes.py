"""Saves the scene a render script builds as a .blend file, to look at it in Blender.
The scripts stay the source: edits made in a saved file do not reach the sprites.

Run:  blender -b --factory-startup -P tools/blender/save_scenes.py -- <bunker|silo|e1|b1|b3|wagon> [out_dir]
Default out_dir: tools/blender/scenes. One part per run, the scripts keep module state.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import rig  # noqa: E402

MODULES = {"bunker": "station_bunker", "silo": "station_silo", "e1": "station_e1", "b1": "station_b1", "b3": "station_b3",
           "wagon": "wagon_w1"}

if __name__ == "__main__":
    a = rig.args()
    name = MODULES[a[0]]
    out = os.path.abspath(a[1] if len(a) > 1 else os.path.join(os.path.dirname(__file__), "scenes"))
    os.makedirs(out, exist_ok=True)
    importlib.import_module(name).build()
    path = os.path.join(out, name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("saved", path)
