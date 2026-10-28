"""Generates simple placeholder sprites until the final artwork exists.

Pure standard library (zlib/struct), no Pillow needed.
Run: python tools/make_placeholders.py
"""
import os
import struct
import zlib

OUT = os.path.join(os.path.dirname(__file__), "..", "graphics", "placeholder")
TILE = 64  # px per tile, sprites use scale = 0.5


def write_png(path, w, h, pixels):
    raw = b"".join(b"\x00" + bytes(pixels[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 4)

    def rect(self, x0, y0, x1, y1, rgba):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                i = (y * self.w + x) * 4
                self.px[i:i + 4] = bytes(rgba)

    def rotated(self, quarter_turns):
        c = self
        for _ in range(quarter_turns % 4):
            r = Canvas(c.h, c.w)
            for y in range(c.h):
                for x in range(c.w):
                    si = (y * c.w + x) * 4
                    nx, ny = c.h - 1 - y, x  # 90 degrees clockwise
                    di = (ny * r.w + nx) * 4
                    r.px[di:di + 4] = c.px[si:si + 4]
            c = r
        return c

    def save(self, name):
        write_png(os.path.join(OUT, name), self.w, self.h, self.px)


def station(frame, inner, accent, beam):
    # 6 x 2 tiles, rail runs vertically through the middle two tiles
    c = Canvas(6 * TILE, 2 * TILE)
    for x0 in (0, 4 * TILE):
        c.rect(x0, 0, x0 + 2 * TILE, 2 * TILE, frame)
        c.rect(x0 + 8, 8, x0 + 2 * TILE - 8, 2 * TILE - 8, inner)
    if beam:
        c.rect(2 * TILE, 40, 4 * TILE, 88, beam)
    # belt port marker on the east end, upper tile
    c.rect(5 * TILE + 8, 8, 6 * TILE, TILE - 8, accent)
    return c


def wagon_station(frame, inner, accent):
    # 6 x 6 tiles, rail runs vertically through the middle two tiles, docks on the long sides
    c = Canvas(6 * TILE, 6 * TILE)
    for x0 in (0, 4 * TILE):
        c.rect(x0, 0, x0 + 2 * TILE, 6 * TILE, frame)
        c.rect(x0 + 8, 8, x0 + 2 * TILE - 8, 6 * TILE - 8, inner)
    for k in range(6):
        c.rect(4, k * TILE + 20, 12, k * TILE + 44, accent)
        c.rect(6 * TILE - 12, k * TILE + 20, 6 * TILE - 4, k * TILE + 44, accent)
    return c


def connector(frame, hood, container_up):
    # 1 x 1 tile seen with the goods flowing north: side rails along the belt and a hood
    # over the half towards the station (north for an input, south for an output)
    c = Canvas(TILE, TILE)
    c.rect(0, 0, 8, TILE, frame)
    c.rect(TILE - 8, 0, TILE, TILE, frame)
    y0 = 0 if container_up else TILE // 2
    c.rect(0, y0, TILE, y0 + TILE // 2, hood)
    return c


def connector_sheet(frame, hood, container_up):
    # the loader sheet: one frame per direction, north, east, south, west
    single = connector(frame, hood, container_up)
    sheet = Canvas(4 * TILE, TILE)
    for d in range(4):
        r = single.rotated(d)
        for y in range(TILE):
            sheet.px[(y * sheet.w + d * TILE) * 4:(y * sheet.w + d * TILE + TILE) * 4] = r.px[y * TILE * 4:(y + 1) * TILE * 4]
    return sheet


def icon(frame, inner, accent):
    c = Canvas(64, 64)
    c.rect(4, 20, 60, 44, frame)
    c.rect(10, 26, 54, 38, inner)
    c.rect(28, 4, 36, 60, (160, 160, 160, 255))
    c.rect(48, 22, 60, 30, accent)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    belt = (214, 165, 28, 255)
    pit = station((139, 135, 126, 255), (29, 27, 24, 255), belt, None)
    loader = station((122, 90, 44, 255), (154, 138, 106, 255), belt, (77, 83, 89, 255))
    belt_loader = station((180, 74, 42, 255), (110, 90, 58, 255), belt, (61, 61, 61, 255))
    for v in range(4):
        pit.rotated(v).save(f"unloading-pit-{v + 1}.png")
        loader.rotated(v).save(f"loading-station-{v + 1}.png")
        belt_loader.rotated(v).save(f"belt-loader-{v + 1}.png")
    bunker = wagon_station((139, 135, 126, 255), (29, 27, 24, 255), belt)
    silo = wagon_station((122, 90, 44, 255), (154, 138, 106, 255), belt)
    for v in range(2):
        bunker.rotated(v).save(f"unloading-bunker-{v + 1}.png")
        silo.rotated(v).save(f"loading-silo-{v + 1}.png")
    for name, frame, hood in (("bunker", (139, 135, 126, 255), (60, 58, 54, 255)),
                              ("silo", (122, 90, 44, 255), (154, 138, 106, 255))):
        connector_sheet(frame, hood, True).save(f"connector-{name}-in.png")
        connector_sheet(frame, hood, False).save(f"connector-{name}-out.png")
    icon((139, 135, 126, 255), (29, 27, 24, 255), belt).save("unloading-pit-icon.png")
    icon((122, 90, 44, 255), (154, 138, 106, 255), belt).save("loading-station-icon.png")
    icon((180, 74, 42, 255), (110, 90, 58, 255), belt).save("belt-loader-icon.png")


if __name__ == "__main__":
    main()
