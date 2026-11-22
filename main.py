"""main.py - front-page news image for Saturday 21 November 2026.

Single self-contained program: standard library only, no network, no
randomness, deterministic output. It draws "THE WORLD TODAY" - a navy
masthead with a gold date line, four flat-illustration panels with
two-line captions, and a dark ticker bar - and writes entry.png under
MAKEFUN_OUTPUT_DIR (default /output). The grader runs it with
`python3 -P -s main.py` twice; both runs must write identical bytes.
"""

import math
import os
import struct
import zlib


# ---------------------------------------------------------------------
# Raster surface: one flat list of RGB tuples plus shape helpers.
# ---------------------------------------------------------------------

class Canvas:
    """A width x height RGB surface stored as a single flat list."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.bg = background
        self.px = [background] * (width * height)

    @property
    def pixels(self):
        w = self.width
        return [self.px[y * w:(y + 1) * w] for y in range(self.height)]

    def rect(self, x, y, w, h, colour):
        left = max(0, int(x))
        top = max(0, int(y))
        right = min(self.width, int(x + w))
        bottom = min(self.height, int(y + h))
        if right <= left or bottom <= top:
            return
        span = [colour] * (right - left)
        buf = self.px
        stride = self.width
        for row in range(top, bottom):
            base = row * stride
            buf[base + left:base + right] = span

    def circle(self, cx, cy, r, colour):
        cx = int(cx)
        cy = int(cy)
        r = int(r)
        rsq = r * r
        left = max(0, cx - r)
        right = min(self.width, cx + r + 1)
        top = max(0, cy - r)
        bottom = min(self.height, cy + r + 1)
        buf = self.px
        stride = self.width
        for y in range(top, bottom):
            dy = y - cy
            dy2 = dy * dy
            base = y * stride
            for x in range(left, right):
                dx = x - cx
                if dx * dx + dy2 <= rsq:
                    buf[base + x] = colour

    def ellipse(self, cx, cy, rx, ry, colour):
        cx = int(cx)
        cy = int(cy)
        rx = int(rx)
        ry = int(ry)
        if rx <= 0 or ry <= 0:
            return
        rxs = rx * rx
        rys = ry * ry
        left = max(0, cx - rx)
        right = min(self.width, cx + rx + 1)
        top = max(0, cy - ry)
        bottom = min(self.height, cy + ry + 1)
        buf = self.px
        stride = self.width
        for y in range(top, bottom):
            dy = y - cy
            base = y * stride
            for x in range(left, right):
                dx = x - cx
                if dx * dx * rys + dy * rys * rxs <= rxs * rys:
                    buf[base + x] = colour

    def line(self, x1, y1, x2, y2, colour, width=1):
        ax, ay, bx, by = float(x1), float(y1), float(x2), float(y2)
        dx = bx - ax
        dy = by - ay
        length = math.hypot(dx, dy)
        if length == 0:
            self.rect(ax - width / 2, ay - width / 2, width, width, colour)
            return
        steps = int(length * 2) + 1
        half = width / 2.0
        for i in range(steps + 1):
            t = i / steps
            self.rect(ax + t * dx - half, ay + t * dy - half,
                      width, width, colour)

    def polygon(self, points, colour):
        if not points:
            return
        n = len(points)
        top = max(0, int(min(p[1] for p in points)))
        bottom = min(self.height - 1, int(max(p[1] for p in points)))
        buf = self.px
        stride = self.width
        for y in range(top, bottom + 1):
            crossings = []
            prev = n - 1
            for cur in range(n):
                xi, yi = points[cur]
                xj, yj = points[prev]
                if (yi < y and yj >= y) or (yj < y and yi >= y):
                    if yj != yi:
                        crossings.append(xi + (y - yi) / (yj - yi) * (xj - xi))
                prev = cur
            crossings.sort()
            for k in range(0, len(crossings) - 1, 2):
                start = max(0, int(crossings[k]))
                end = min(self.width, int(crossings[k + 1]) + 1)
                base = y * stride
                for x in range(start, end):
                    buf[base + x] = colour


# ---------------------------------------------------------------------
# 5x7 bitmap type. Each glyph is (width, seven row bitmasks) with the
# most significant bit as the leftmost column; '$' is six columns wide,
# everything else five. Same letterforms as the earlier entries' font,
# re-encoded here as integers.
# ---------------------------------------------------------------------

FONT = {
    ' ': (5, (0, 0, 0, 0, 0, 0, 0)),
    '$': (6, (4, 31, 20, 14, 5, 31, 4)),
    '%': (5, (25, 26, 2, 4, 8, 8, 19)),
    ',': (5, (0, 0, 0, 0, 4, 4, 8)),
    '-': (5, (0, 0, 0, 31, 0, 0, 0)),
    '.': (5, (0, 0, 0, 0, 0, 4, 4)),
    '/': (5, (1, 1, 2, 4, 8, 16, 16)),
    '0': (5, (14, 19, 21, 21, 25, 17, 14)),
    '1': (5, (4, 12, 4, 4, 4, 4, 31)),
    '2': (5, (14, 17, 1, 6, 8, 16, 31)),
    '3': (5, (31, 1, 2, 6, 1, 17, 14)),
    '4': (5, (16, 17, 17, 31, 1, 1, 1)),
    '5': (5, (31, 16, 30, 1, 1, 17, 14)),
    '6': (5, (14, 16, 16, 30, 17, 17, 14)),
    '7': (5, (31, 1, 2, 4, 8, 8, 8)),
    '8': (5, (14, 17, 17, 14, 17, 17, 14)),
    '9': (5, (14, 17, 17, 15, 1, 1, 14)),
    ':': (5, (0, 4, 4, 0, 4, 4, 0)),
    'A': (5, (14, 17, 17, 31, 17, 17, 17)),
    'B': (5, (30, 17, 17, 30, 17, 17, 30)),
    'C': (5, (15, 16, 16, 16, 16, 16, 15)),
    'D': (5, (30, 17, 17, 17, 17, 17, 30)),
    'E': (5, (31, 16, 16, 30, 16, 16, 31)),
    'F': (5, (31, 16, 16, 30, 16, 16, 16)),
    'G': (5, (15, 16, 16, 23, 17, 17, 15)),
    'H': (5, (17, 17, 17, 31, 17, 17, 17)),
    'I': (5, (31, 4, 4, 4, 4, 4, 31)),
    'J': (5, (7, 2, 2, 2, 2, 18, 12)),
    'K': (5, (17, 18, 20, 24, 20, 18, 17)),
    'L': (5, (16, 16, 16, 16, 16, 16, 31)),
    'M': (5, (17, 27, 21, 21, 17, 17, 17)),
    'N': (5, (17, 25, 21, 19, 17, 17, 17)),
    'O': (5, (14, 17, 17, 17, 17, 17, 14)),
    'P': (5, (30, 17, 17, 30, 16, 16, 16)),
    'Q': (5, (14, 17, 17, 17, 21, 18, 13)),
    'R': (5, (30, 17, 17, 30, 20, 18, 17)),
    'S': (5, (15, 16, 16, 14, 1, 1, 30)),
    'T': (5, (31, 4, 4, 4, 4, 4, 4)),
    'U': (5, (17, 17, 17, 17, 17, 17, 14)),
    'V': (5, (17, 17, 17, 17, 17, 10, 4)),
    'W': (5, (17, 17, 17, 21, 21, 27, 17)),
    'X': (5, (17, 17, 10, 4, 10, 17, 17)),
    'Y': (5, (17, 17, 10, 4, 4, 4, 4)),
    'Z': (5, (31, 1, 2, 4, 8, 16, 31)),
}


def draw_text(canvas, x, y, text, scale=1, colour=(0, 0, 0)):
    pen = x
    for ch in text.upper():
        width, rows = FONT.get(ch, FONT[' '])
        for r in range(7):
            bits = rows[r]
            for c in range(width):
                if (bits >> (width - 1 - c)) & 1:
                    canvas.rect(pen + c * scale, y + r * scale,
                                scale, scale, colour)
        pen += 6 * scale


# ---------------------------------------------------------------------
# PNG writer: filter-0 scanlines, zlib level 9, minimal chunk set.
# ---------------------------------------------------------------------

def _png_chunk(tag, data):
    body = tag + data
    return (struct.pack('>I', len(data)) + body +
            struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF))


def write_png(path, width, height, pixels):
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for (r, g, b) in row:
            raw += bytes((r, g, b))
    packed = zlib.compress(bytes(raw), 9)
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    blob = bytearray(b'\x89PNG\r\n\x1a\n')
    blob += _png_chunk(b'IHDR', header)
    blob += _png_chunk(b'IDAT', packed)
    blob += _png_chunk(b'IEND', b'')
    with open(path, 'wb') as handle:
        handle.write(blob)


# ---------------------------------------------------------------------
# Scenes for 21 November 2026.
# ---------------------------------------------------------------------

def draw_cartel(canvas, x, y, w, h):
    # Mexico captures cartel boss "El Chapo Isidro" overnight in Sinaloa:
    # night desert, helicopter searchlight pinning a pickup on the road.
    sky = [(10, 14, 34), (16, 24, 52), (24, 36, 68)]
    sand = (72, 60, 42)
    sand_dark = (52, 44, 30)
    rock = (28, 26, 40)
    beam = (250, 240, 180)
    beam_edge = (210, 195, 130)
    # helicopter body, lightened so the silhouette reads against the
    # dark night-sky bands instead of blending into them
    heli = (62, 68, 80)
    truck = (150, 40, 45)
    moon = (235, 230, 200)
    star = (220, 220, 235)

    band_h = h // 3
    for i, col in enumerate(sky):
        canvas.rect(x, y + i * band_h, w, band_h + 1, col)
    # stars
    for i in range(34):
        sx = x + (i * 89) % (w - 10) + 5
        sy = y + (i * 53) % 110 + 6
        canvas.circle(sx, sy, 1 if i % 3 else 2, star)
    # moon
    canvas.circle(x + w - 58, y + 44, 24, moon)
    canvas.circle(x + w - 66, y + 38, 20, (245, 242, 220))
    # mountain ridges
    canvas.polygon([(x, y + 190), (x + 90, y + 140), (x + 170, y + 185),
                    (x + 260, y + 138), (x + 340, y + 188), (x + w, y + 150),
                    (x + w, y + 220), (x, y + 220)], rock)
    # desert ground
    canvas.rect(x, y + 218, w, h - 218, sand)
    canvas.rect(x, y + 218, w, 6, sand_dark)
    # road across the ground
    canvas.rect(x, y + 258, w, 34, (30, 28, 30))
    for dx in range(x + 10, x + w - 10, 52):
        canvas.rect(dx, y + 273, 26, 4, (200, 190, 140))

    # helicopter, upper left, rotors spinning
    hx = x + 120
    hy = y + 74
    canvas.line(hx - 70, hy - 26, hx + 70, hy - 26, (180, 180, 190), 3)
    canvas.line(hx - 58, hy - 30, hx + 58, hy - 30, (140, 140, 150), 2)
    canvas.ellipse(hx, hy, 52, 20, heli)
    canvas.rect(hx - 52, hy - 12, 104, 22, heli)
    canvas.polygon([(hx + 48, hy - 8), (hx + 118, hy - 2), (hx + 118, hy + 8),
                    (hx + 48, hy + 10)], heli)
    canvas.line(hx + 118, hy - 22, hx + 118, hy + 16, heli, 4)
    canvas.circle(hx - 30, hy + 2, 8, (150, 200, 230))
    canvas.rect(hx - 8, hy + 12, 14, 16, (25, 28, 34))
    # searchlight cone from the helicopter down to the truck
    tx = x + 250
    ty = y + 272
    canvas.polygon([(hx - 6, hy + 16), (hx + 10, hy + 16),
                    (tx + 46, ty - 6), (tx - 46, ty - 6)], beam_edge)
    canvas.polygon([(hx - 3, hy + 16), (hx + 7, hy + 16),
                    (tx + 36, ty - 6), (tx - 36, ty - 6)], beam)
    canvas.ellipse(tx, ty - 4, 52, 10, (255, 248, 205))

    # pickup truck caught in the beam
    canvas.rect(tx - 44, ty - 26, 88, 18, truck)
    canvas.rect(tx - 26, ty - 40, 40, 16, (120, 30, 35))
    canvas.rect(tx - 22, ty - 37, 14, 11, (170, 210, 235))
    canvas.rect(tx - 4, ty - 37, 14, 11, (170, 210, 235))
    canvas.circle(tx - 28, ty - 6, 9, (12, 12, 14))
    canvas.circle(tx + 30, ty - 6, 9, (12, 12, 14))
    canvas.circle(tx - 28, ty - 6, 4, (160, 160, 170))
    canvas.circle(tx + 30, ty - 6, 4, (160, 160, 170))
    # soldiers closing in, small dark figures
    for sx, sy in [(tx - 78, ty - 2), (tx + 84, ty - 2), (tx + 108, ty + 2)]:
        canvas.circle(sx, sy - 26, 6, (30, 28, 24))
        canvas.rect(sx - 5, sy - 21, 10, 22, (38, 42, 36))
        canvas.line(sx - 5, sy - 20, sx - 14, sy - 12, (20, 20, 20), 3)


def draw_cop31(canvas, x, y, w, h):
    # COP31 climate talks run into overtime in Antalya: a late-night hall,
    # a wall clock near midnight, delegates still at the table, sea outside.
    wall = (232, 220, 198)
    wall_dark = (200, 186, 160)
    sea = (40, 90, 130)
    sea2 = (70, 125, 165)
    wood = (120, 85, 55)
    wood_dark = (90, 62, 38)
    paper = (250, 248, 240)
    clock_face = (252, 250, 244)
    rim = (60, 55, 45)
    skin_a = (225, 185, 150)
    skin_b = (200, 160, 125)
    skin_c = (235, 200, 165)
    suit_a = (35, 45, 70)
    suit_b = (70, 30, 30)
    suit_c = (45, 70, 45)

    canvas.rect(x, y, w, h, wall)
    # window: night sea and moon over Antalya
    wx0 = x + 22
    wy0 = y + 14
    ww = w - 44
    wh = 92
    canvas.rect(wx0, wy0, ww, wh, sea)
    canvas.circle(wx0 + ww - 46, wy0 + 26, 14, (240, 235, 200))
    for mx in range(wx0 + 10, wx0 + ww - 10, 46):
        canvas.line(mx, wy0 + 66, mx + 24, wy0 + 66, sea2, 2)
        canvas.line(mx + 12, wy0 + 82, mx + 34, wy0 + 82, sea2, 2)
    canvas.line(wx0, wy0 + wh, wx0 + ww, wy0 + wh, wall_dark, 3)
    canvas.line(wx0 + ww // 2, wy0, wx0 + ww // 2, wy0 + wh, wall_dark, 3)

    # COP31 banner on the wall
    draw_text(canvas, x + 26, y + 122, "COP31", scale=3, colour=(30, 90, 70))
    draw_text(canvas, x + 130, y + 130, "ANTALYA", scale=2, colour=(90, 80, 65))

    # big wall clock, hands at five to midnight: talks in overtime
    cx = x + w - 92
    cy = y + 138
    canvas.circle(cx, cy, 46, rim)
    canvas.circle(cx, cy, 40, clock_face)
    for a in range(12):
        rad = math.radians(a * 30)
        px1 = cx + int(34 * math.cos(rad))
        py1 = cy + int(34 * math.sin(rad))
        px2 = cx + int(38 * math.cos(rad))
        py2 = cy + int(38 * math.sin(rad))
        canvas.line(px1, py1, px2, py2, rim, 2)
    # minute hand to 11, hour hand near 12
    canvas.line(cx, cy, cx + 26, cy - 22, rim, 3)
    canvas.line(cx, cy, cx - 2, cy - 24, rim, 4)
    canvas.circle(cx, cy, 4, rim)

    # long negotiation table with papers and flags
    ty = y + h - 78
    canvas.ellipse(x + w // 2, ty + 30, 190, 26, wood)
    canvas.ellipse(x + w // 2, ty + 24, 190, 24, (140, 100, 65))
    canvas.rect(x + w // 2 - 6, ty + 30, 12, 40, wood_dark)
    for px in range(x + 60, x + w - 60, 64):
        canvas.rect(px, ty + 12, 34, 20, paper)
        canvas.line(px + 5, ty + 18, px + 29, ty + 18, (150, 150, 150), 1)
        canvas.line(px + 5, ty + 24, px + 29, ty + 24, (150, 150, 150), 1)
    # small national flags on the table
    for fx, fcol in [(x + 52, (200, 35, 40)), (x + 108, (40, 80, 170)),
                     (x + w - 130, (250, 220, 60)), (x + w - 74, (40, 120, 60))]:
        canvas.line(fx, ty - 2, fx, ty - 26, (150, 145, 130), 2)
        canvas.rect(fx + 2, ty - 26, 22, 13, fcol)

    # three delegates still seated, heads bowed over the talks
    for lx, skin, suit in [(x + 96, skin_a, suit_a), (x + w // 2, skin_b, suit_b),
                           (x + w - 96, skin_c, suit_c)]:
        ly = ty - 8
        canvas.polygon([(lx - 28, ly + 30), (lx + 28, ly + 30),
                        (lx + 18, ly - 4), (lx - 18, ly - 4)], suit)
        canvas.rect(lx - 3, ly - 2, 6, 24, (245, 245, 245))
        canvas.circle(lx, ly - 16, 15, skin)
        canvas.circle(lx, ly - 20, 16, (60, 55, 50))
        canvas.rect(lx - 16, ly - 20, 32, 9, (60, 55, 50))


def draw_kryvyi(canvas, x, y, w, h):
    # Russian ballistic strike on Kryvyi Rih: night city, explosions over a
    # damaged apartment block, missile trails, rescue lights below.
    night = (10, 12, 30)
    night2 = (18, 22, 48)
    star = (225, 225, 240)
    tower = (22, 24, 42)
    tower_b = (32, 34, 56)
    lit = (255, 210, 110)
    fire = (255, 140, 40)
    fire2 = (255, 200, 80)
    smoke = (90, 90, 100)
    smoke2 = (60, 60, 70)
    street = (28, 26, 32)

    canvas.rect(x, y, w, h, night)
    canvas.rect(x, y, w, 120, night2)
    for i in range(30):
        sx = x + (i * 101) % (w - 10) + 5
        sy = y + (i * 47) % 100 + 6
        canvas.circle(sx, sy, 1 if i % 3 else 2, star)
    # missile trails arcing down from the sky
    canvas.line(x + 60, y + 8, x + 150, y + 150, (255, 190, 120), 3)
    canvas.line(x + 66, y + 8, x + 156, y + 150, (255, 150, 60), 2)
    canvas.line(x + w - 70, y + 4, x + w - 170, y + 128, (255, 190, 120), 3)
    canvas.line(x + w - 64, y + 4, x + w - 164, y + 128, (255, 150, 60), 2)

    # city skyline
    base = y + h
    heights = [0.34, 0.46, 0.30, 0.52, 0.38, 0.44, 0.32, 0.48, 0.36, 0.40]
    cols = [tower, tower_b, tower, tower_b, tower, tower_b, tower, tower, tower_b, tower]
    bw = w // len(heights)
    for i, hh in enumerate(heights):
        bh = int(h * hh)
        bx = x + i * bw
        canvas.rect(bx + 2, base - 64 - bh + 18, bw - 4, bh + 46, cols[i])
        for wy in range(base - 64 - bh + 30, base - 70, 18):
            for wx in range(bx + 8, bx + bw - 10, 14):
                if (wx * 5 + wy * 3) % 6 == 0:
                    canvas.rect(wx, wy, 4, 6, lit)
    # damaged apartment block, broken top, dark windows
    dx = x + int(w * 0.42)
    dw = 74
    canvas.rect(dx, y + 150, dw, 128, (38, 36, 52))
    canvas.polygon([(dx, y + 150), (dx + 18, y + 128), (dx + 34, y + 150),
                    (dx + 52, y + 134), (dx + dw, y + 150)], (24, 24, 36))
    for wy in range(y + 162, y + 268, 20):
        for wx in range(dx + 10, dx + dw - 12, 16):
            if (wx + wy) % 3:
                canvas.rect(wx, wy, 7, 9, lit)
            else:
                canvas.rect(wx, wy, 7, 9, (8, 8, 12))

    # two explosion bursts with smoke columns
    for ex, ey, r in [(x + 108, y + 168, 30), (x + w - 96, y + 152, 26)]:
        canvas.circle(ex, ey, r + 22, (120, 60, 20))
        canvas.circle(ex, ey, r + 10, fire)
        canvas.circle(ex, ey, r, fire2)
        canvas.circle(ex, ey - 6, 12, (255, 240, 180))
        canvas.circle(ex - 8, ey - r - 26, 16, smoke)
        canvas.circle(ex + 10, ey - r - 44, 20, smoke2)
        canvas.circle(ex - 2, ey - r - 62, 14, smoke)
    # street with an ambulance, lights on
    canvas.rect(x, base - 34, w, 34, street)
    ax = x + int(w * 0.60)
    ay = base - 30
    canvas.rect(ax - 46, ay - 4, 92, 20, (235, 235, 235))
    canvas.rect(ax - 46, ay - 16, 34, 14, (235, 235, 235))
    canvas.rect(ax - 42, ay - 13, 12, 9, (150, 200, 235))
    canvas.rect(ax - 14, ay - 11, 12, 12, (200, 40, 40))
    canvas.rect(ax - 11, ay - 14, 6, 18, (200, 40, 40))
    canvas.circle(ax - 28, ay + 16, 7, (12, 12, 14))
    canvas.circle(ax + 28, ay + 16, 7, (12, 12, 14))
    canvas.circle(ax + 52, ay - 22, 5, (255, 60, 60))
    canvas.circle(ax + 52, ay - 22, 9, (255, 120, 120))


def draw_mercury(canvas, x, y, w, h):
    # BepiColombo enters orbit around Mercury after an eight-year trip:
    # black space, sun glare, cratered Mercury, the twin orbiters arriving.
    space = (5, 6, 18)
    star = (235, 235, 245)
    sun = (255, 205, 90)
    mercury = (172, 152, 128)
    mercury_dark = (140, 122, 100)
    crater = (120, 102, 84)
    body = (215, 215, 220)
    panel = (50, 90, 170)
    gold = (215, 175, 75)
    earth = (90, 140, 220)

    canvas.rect(x, y, w, h, space)
    for i in range(44):
        sx = x + (i * 97) % (w - 12) + 6
        sy = y + (i * 61) % (h - 12) + 6
        r = 1 if i % 3 else 2
        canvas.circle(sx, sy, r, star)
    # sun glare, upper left
    sx0 = x + 54
    sy0 = y + 52
    canvas.circle(sx0, sy0, 46, (110, 70, 18))
    canvas.circle(sx0, sy0, 32, (200, 140, 40))
    canvas.circle(sx0, sy0, 20, sun)
    # tiny Earth, far left, where the trip began
    ex = x + 34
    ey = y + 118
    canvas.circle(ex, ey, 7, earth)
    canvas.circle(ex - 2, ey - 2, 3, (160, 200, 245))
    # dashed trajectory Earth -> spacecraft -> Mercury
    px = x + int(w * 0.52)
    py = y + int(h * 0.42)
    mx = x + int(w * 0.80)
    my = y + int(h * 0.52)
    for t in range(0, 12):
        t0 = t / 12.0
        t1 = (t + 0.55) / 12.0
        canvas.line(ex + (px - ex) * t0, ey + (py - ey) * t0,
                    ex + (px - ex) * t1, ey + (py - ey) * t1, (150, 150, 180), 2)
        canvas.line(px + (mx - px) * t0, py + (my - py) * t0,
                    px + (mx - px) * t1, py + (my - py) * t1, (150, 150, 180), 2)

    # Mercury, big cratered disc on the right
    canvas.circle(mx, my, 86, mercury_dark)
    canvas.circle(mx - 6, my - 6, 82, mercury)
    for cx2, cy2, cr in [(mx - 34, my - 30, 12), (mx + 22, my - 44, 9),
                         (mx + 38, my + 8, 14), (mx - 8, my + 34, 10),
                         (mx + 4, my - 8, 7), (mx - 48, my + 12, 8),
                         (mx + 52, my - 26, 6)]:
        canvas.circle(cx2, cy2, cr, crater)
        canvas.circle(cx2 - 2, cy2 - 2, cr - 3, (150, 132, 110))
    # terminator shadow on Mercury's right edge
    canvas.polygon([(mx + 30, my - 82), (mx + 86, my - 40), (mx + 86, my + 40),
                    (mx + 30, my + 82), (mx + 62, my)], (150, 130, 106))

    # the twin orbiters, still joined, arriving at Mercury
    canvas.rect(px - 24, py - 14, 48, 28, body)
    canvas.rect(px - 24, py - 14, 48, 5, (170, 170, 178))
    # solar wings
    canvas.rect(px - 108, py - 8, 82, 16, panel)
    canvas.rect(px + 26, py - 8, 82, 16, panel)
    for wx in range(px - 104, px - 30, 14):
        canvas.line(wx, py - 8, wx, py + 8, (90, 140, 210), 1)
    for wx in range(px + 30, px + 104, 14):
        canvas.line(wx, py - 8, wx, py + 8, (90, 140, 210), 1)
    # dish and gold foil
    canvas.circle(px + 8, py - 30, 14, (240, 240, 245))
    canvas.circle(px + 8, py - 30, 8, (200, 200, 208))
    canvas.line(px + 8, py - 16, px + 8, py - 14, body, 4)
    canvas.rect(px - 24, py + 8, 48, 6, gold)
    # antenna mast with beacon
    canvas.line(px - 8, py - 14, px - 8, py - 36, body, 3)
    canvas.circle(px - 8, py - 38, 3, (255, 120, 80))


# ---------------------------------------------------------------------
# Page assembly (21 November 2026).
# ---------------------------------------------------------------------

def build_entry():
    width = 1024
    height = 1024
    cream = (245, 242, 235)
    canvas = Canvas(width, height, cream)

    mast_h = 135
    navy = (20, 30, 50)
    gold = (215, 175, 75)
    white = (255, 255, 255)
    dark_gray = (40, 40, 40)
    panel_bg = (238, 235, 226)
    ticker_bg = (30, 30, 35)

    canvas.rect(0, 0, width, mast_h, navy)
    canvas.line(0, mast_h, width, mast_h, gold, 4)

    draw_text(canvas, 60, 22, "THE WORLD TODAY", scale=5, colour=white)
    draw_text(canvas, 62, 85, "SATURDAY, 21 NOVEMBER 2026", scale=2, colour=gold)
    canvas.line(62, 112, 420, 112, (80, 100, 130), 1)

    ticker_h = 45
    t_y = height - ticker_h
    canvas.rect(0, t_y, width, ticker_h, ticker_bg)
    canvas.line(0, t_y, width, t_y, gold, 2)
    ticker_text = "ALSO TODAY: PERU QUAKE 6.7 - MARKETS SLIDE - GTA FESTIVAL MIAMI"
    draw_text(canvas, 25, t_y + 14, ticker_text, scale=2, colour=(230, 230, 230))

    p_w = 440
    p_h = 320
    col1_x = 72
    col2_x = 512
    row1_y = 170
    row2_y = 575

    # Panel 1: Mexico captures "El Chapo Isidro"
    canvas.rect(col1_x - 8, row1_y - 8, p_w + 16, p_h + 38, panel_bg)
    draw_cartel(canvas, col1_x, row1_y, p_w, p_h)
    draw_text(canvas, col1_x, row1_y + p_h + 8, "EL CHAPO ISIDRO CAUGHT", scale=2, colour=dark_gray)
    draw_text(canvas, col1_x, row1_y + p_h + 23, "MEXICO NABS FBI FUGITIVE", scale=2, colour=dark_gray)

    # Panel 2: COP31 talks run into overtime in Antalya
    canvas.rect(col2_x - 8, row1_y - 8, p_w + 16, p_h + 38, panel_bg)
    draw_cop31(canvas, col2_x, row1_y, p_w, p_h)
    draw_text(canvas, col2_x, row1_y + p_h + 8, "COP31 TALKS IN OVERTIME", scale=2, colour=dark_gray)
    draw_text(canvas, col2_x, row1_y + p_h + 23, "ANTALYA: NO DEAL YET", scale=2, colour=dark_gray)

    # Panel 3: Russian strike on Kryvyi Rih
    canvas.rect(col1_x - 8, row2_y - 8, p_w + 16, p_h + 38, panel_bg)
    draw_kryvyi(canvas, col1_x, row2_y, p_w, p_h)
    draw_text(canvas, col1_x, row2_y + p_h + 8, "MISSILES HIT KRYVYI RIH", scale=2, colour=dark_gray)
    draw_text(canvas, col1_x, row2_y + p_h + 23, "2 KILLED, 60 WOUNDED", scale=2, colour=dark_gray)

    # Panel 4: BepiColombo reaches Mercury
    canvas.rect(col2_x - 8, row2_y - 8, p_w + 16, p_h + 38, panel_bg)
    draw_mercury(canvas, col2_x, row2_y, p_w, p_h)
    draw_text(canvas, col2_x, row2_y + p_h + 8, "BEPICOLOMBO AT MERCURY", scale=2, colour=dark_gray)
    draw_text(canvas, col2_x, row2_y + p_h + 23, "8-YEAR TRIP ENDS TODAY", scale=2, colour=dark_gray)

    out_dir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'entry.png')

    write_png(out_path, width, height, canvas.pixels)
    print(f"Successfully generated {out_path}")

if __name__ == '__main__':
    build_entry()
