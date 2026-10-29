"""Turns the Blender renders into Factorio sprite sheets plus graphics/entity/sprites.lua.

Usage: python tools/blender/build_sprites.py <render_dir>
Expects the layout written by render_all.sh: <render_dir>/{w1,b3,b1,e1}/...
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import pack  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "graphics", "entity")
# default colours, as in prototypes/wagon.lua and shared.station_color
WAGON_COLOR = (0.56, 0.23, 0.15)
STATION_COLOR = (0.45, 0.5, 0.22)
# Lift of the north/south frames in tiles. The orthographic camera shortens the
# wagon along the track, so a straight wagon would sit low between its neighbours
# (in game it measured ~0.33 tiles too far from the train ahead).
WAGON_LIFT = 0.33
# The game projects the wagon's sprite shift with its orientation, the script-drawn
# heaps are not projected. Measured on north-south track the heap sat 0.55 tiles
# too high and 7 % too short in the hopper; east-west it fits.
HEAP_DROP = 0.55
HEAP_STRETCH = 0.07
# connector housing colours per belt tier, like the belts' own trim
CONNECTOR_TINTS = {
    "basic": (0.93, 0.7, 0.12),
    "fast": (0.85, 0.22, 0.16),
    "express": (0.2, 0.55, 0.9),
    "turbo": (0.45, 0.8, 0.3),
}


def frames(src, kind, count, stretch):
    return [pack.load(src, kind, i, stretch) for i in range(count)]


def lifted(images, lift):
    """Moves each wagon frame up by lift tiles, scaled by how much it faces north/south."""
    from PIL import Image
    out = []
    for i, im in enumerate(images):
        dy = round(lift * 64 * math.cos(2 * math.pi * i / (2 * len(images))) ** 2)
        moved = Image.new("RGBA", im.size)
        moved.paste(im, (0, -dy))
        out.append(moved)
    return out


def heap_fit(images, drop, stretch):
    """Moves each heap frame down and stretches it along the track, scaled like lifted()."""
    from PIL import Image
    out = []
    for i, im in enumerate(images):
        k = math.cos(2 * math.pi * i / (2 * len(images))) ** 2
        box = im.getbbox()
        moved = Image.new("RGBA", im.size)
        if box:
            part = im.crop(box)
            h = round(part.height * (1 + stretch * k))
            part = part.resize((part.width, h), Image.LANCZOS)
            top = round((box[1] + box[3]) / 2 - h / 2 + drop * 64 * k)
            moved.paste(part, (box[0], top))
        out.append(moved)
    return out


def write_sheet(images, origin, name, line_length, lines_per_file=None):
    """Crops all frames to their common bounding box and writes sheet file(s).

    origin: pixel position of the entity position in the (uncropped) frames.
    Returns the metadata table for sprites.lua.
    """
    box = None
    for im in images:
        b = im.getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    if box is None:
        box = (0, 0, 2, 2)
    w, h = box[2] - box[0], box[3] - box[1]
    count = len(images)
    line_length = min(line_length, count)
    lines_per_file = lines_per_file or math.ceil(count / line_length)
    per_file = line_length * lines_per_file
    files = []
    from PIL import Image
    for f in range(math.ceil(count / per_file)):
        chunk = images[f * per_file:(f + 1) * per_file]
        lines = math.ceil(len(chunk) / line_length)
        sheet = Image.new("RGBA", (w * line_length, h * lines))
        for k, im in enumerate(chunk):
            sheet.paste(im.crop(box), ((k % line_length) * w, (k // line_length) * h))
        fname = f"{name}-{f + 1}.png" if per_file < count else f"{name}.png"
        sheet.save(os.path.join(OUT, fname), optimize=True)
        files.append(fname)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return {
        "files": files, "width": w, "height": h, "line_length": line_length, "lines_per_file": lines_per_file,
        "frame_count": count, "shift": ((cx - origin[0]) / 64, (cy - origin[1]) / 64),
    }


def origin_of(src, stretch):
    """Pixel position of the world origin in a (final size) frame, from the render's camera.json."""
    import json
    with open(os.path.join(src, "camera.json")) as f:
        cam = json.load(f)
    return (cam["width"] * 64 / 2, (cam["height"] / 2 + cam["shift_y"]) * 64 * stretch)


def lua(value, indent=""):
    if isinstance(value, dict):
        inner = indent + "  "
        items = ",\n".join(f"{inner}[\"{k}\"] = {lua(v, inner)}" for k, v in value.items())
        return "{\n" + items + "\n" + indent + "}"
    if isinstance(value, (list, tuple)):
        return "{ " + ", ".join(lua(v, indent) for v in value) + " }"
    if isinstance(value, str):
        return f"\"{value}\""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main(render_dir):
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    G = pack.GROUND_STRETCH

    src = os.path.join(render_dir, "w1")
    if os.path.isdir(src):
        o = origin_of(src, 1.0)
        meta["wagon"] = {}
        for kind in ("color", "mask", "shadow", *(f"{p}{n}" for p in ("load", "drain") for n in range(1, 5))):
            images = lifted(frames(src, kind, 128, 1.0), WAGON_LIFT)
            if kind.startswith(("load", "drain")):
                images = heap_fit(images, HEAP_DROP, HEAP_STRETCH)
            meta["wagon"][kind] = write_sheet(images, o, f"bulk-wagon-{kind}", 8, 4)

    for key, layers in (
        ("b3", {"base": 1, "base_mask": 1, "shadow": 1, "top_static": 1, "idle": 1, "idle_mask": 1, "extend": 8, "extend_mask": 8,
                "work": 8, "work_mask": 8}),
        ("b1", {"base": 1, "base_mask": 1, "shadow": 1, "top_static": 1, "idle": 1, "idle_mask": 1, "extend": 8, "extend_mask": 8,
                "work": 8, "work_mask": 8}),
        ("e1", {"idle": 1, "idle_mask": 1, "extend": 8, "extend_mask": 8, "work": 8, "work_mask": 8}),
        *((key, {"base": 1, "base_mask": 1, "shadow": 1, "top_static": 1, "idle": 1, "idle_mask": 1, "extend": 8,
                 "extend_mask": 8, "work": 8, "work_mask": 8}) for key in ("bunker", "silo")),
    ):
        for v in range(1, 5):
            src = os.path.join(render_dir, key, f"v{v}")
            if not os.path.isdir(src):
                continue
            o = origin_of(src, G)
            entry = {}
            for kind, count in layers.items():
                entry[kind] = write_sheet(frames(src, kind, count, G), o, f"{key}-{v}-{kind}", 8)
            meta[f"{key}-{v}"] = entry

    # connectors: one tinted housing sheet per belt tier, frames north, east, south, west
    # with the belt leaving the station (out); an input connector shows them turned around
    src = os.path.join(render_dir, "connector")
    if os.path.isdir(src):
        o = origin_of(src, G)
        color = frames(src, "color", 4, G)
        mask = frames(src, "mask", 4, G)
        for tier, tint in CONNECTOR_TINTS.items():
            out = [pack.tinted(c, m, tint) for c, m in zip(color, mask)]
            meta[f"connector-{tier}"] = {
                # checked in game: for both kinds the station lies in the frame's
                # direction, the model has it south, so every frame is turned around
                "out": write_sheet([out[2], out[3], out[0], out[1]], o, f"connector-{tier}-out", 4),
                "in": write_sheet([out[2], out[3], out[0], out[1]], o, f"connector-{tier}-in", 4),
            }

    # 0.5.0 connectors on the station rim: bunker elevator and silo conveyor, same frame order
    for key in ("bunker", "silo"):
        src = os.path.join(render_dir, f"connector-{key}")
        if not os.path.isdir(src):
            continue
        o = origin_of(src, G)
        color = frames(src, "color", 4, G)
        mask = frames(src, "mask", 4, G)
        for tier, tint in CONNECTOR_TINTS.items():
            out = [pack.tinted(c, m, tint) for c, m in zip(color, mask)]
            turned = [out[2], out[3], out[0], out[1]]
            meta[f"connector-{key}-{tier}"] = {
                "out": write_sheet(turned, o, f"connector-{key}-{tier}-out", 4),
                "in": write_sheet(turned, o, f"connector-{key}-{tier}-in", 4),
            }

    # sets missing from render_dir keep their entries, so one part can be re-rendered alone
    blocks = {k: f"  [\"{k}\"] = {lua(v, '  ')}" for k, v in meta.items()}
    path = os.path.join(OUT, "sprites.lua")
    old = {}
    if os.path.exists(path):
        with open(path) as f:
            for m in re.finditer(r'^  \["([^"]+)"\] = \{\n.*?^  \}', f.read(), re.M | re.S):
                old[m.group(1)] = m.group(0)
    merged = {**old, **blocks}
    with open(path, "w") as f:
        f.write("-- Generated by tools/blender/build_sprites.py, do not edit.\nreturn {\n" + ",\n".join(merged.values()) + "\n}\n")
    print("wrote", len(meta), "sprite sets, kept", len(merged) - len(meta))





def icons(render_dir, out_dir):
    """64 px item icons (plus 144 px thumbnail) cut from the renders."""
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    G = pack.GROUND_STRETCH

    def fit(img, size):
        img = img.crop(img.getbbox())
        scale = size / max(img.size)
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size))
        canvas.alpha_composite(img, ((size - img.width) // 2, (size - img.height) // 2))
        return canvas

    w = os.path.join(render_dir, "w1")
    if os.path.isdir(w):
        wagon = pack.tinted(pack.load(w, "color", 40), pack.load(w, "mask", 40), WAGON_COLOR)
        fit(wagon, 64).save(os.path.join(out_dir, "bulk-wagon.png"))
    src = os.path.join(render_dir, "connector")
    if os.path.isdir(src):
        for tier, tint in CONNECTOR_TINTS.items():
            img = pack.tinted(pack.load(src, "color", 1, G), pack.load(src, "mask", 1, G), tint)
            fit(img, 64).save(os.path.join(out_dir, f"connector-{tier}.png"))
    for key, name in (("e1", "unloading-pit"), ("b3", "belt-loader"), ("b1", "loading-station"), ("bunker", "unloading-bunker"),
                      ("silo", "loading-silo")):
        src = os.path.join(render_dir, key, "v1")
        if not os.path.isdir(src):
            continue
        layers = [pack.tinted(pack.load(src, kind, 0, G), pack.load(src, kind + "_mask", 0, G), STATION_COLOR)
                  for kind in ("base", "idle") if os.path.exists(os.path.join(src, f"{kind}_000.png"))]
        img = layers[0].copy()
        for extra in layers[1:]:
            img.alpha_composite(extra)
        fit(img, 64).save(os.path.join(out_dir, f"{name}.png"))


if __name__ == "__main__":
    main(sys.argv[1])
    icons(sys.argv[1], os.path.join(ROOT, "graphics", "icons"))
