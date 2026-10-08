"""Tiny pixel-art toolkit used to paint every texture in the pack procedurally.

All randomness is seeded so builds are reproducible.
"""
import math
import os
import random

import numpy as np
from PIL import Image


def hexrgb(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(4))


def shade(c, f):
    """Multiply RGB by f (alpha kept)."""
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))), max(0, min(255, int(c[2] * f))), c[3])


def ramp(colors, t):
    """Sample a list of colors at t in [0,1]."""
    t = max(0.0, min(1.0, t))
    if len(colors) == 1:
        return colors[0]
    pos = t * (len(colors) - 1)
    i = min(int(pos), len(colors) - 2)
    return mix(colors[i], colors[i + 1], pos - i)


def value_noise(w, h, scale, seed, octaves=3, wrap=True):
    """Tileable value noise in [0,1]."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=float)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells_x = max(1, int(round(w / scale)) * (2 ** o))
        cells_y = max(1, int(round(h / scale)) * (2 ** o))
        grid = rng.random((cells_y + 1, cells_x + 1))
        if wrap:
            grid[-1, :] = grid[0, :]
            grid[:, -1] = grid[:, 0]
        ys = np.linspace(0, cells_y, h, endpoint=False)
        xs = np.linspace(0, cells_x, w, endpoint=False)
        y0 = np.floor(ys).astype(int)
        x0 = np.floor(xs).astype(int)
        fy = ys - y0
        fx = xs - x0
        fy = fy * fy * (3 - 2 * fy)
        fx = fx * fx * (3 - 2 * fx)
        a = grid[np.ix_(y0, x0)]
        b = grid[np.ix_(y0, x0 + 1)]
        c = grid[np.ix_(y0 + 1, x0)]
        d = grid[np.ix_(y0 + 1, x0 + 1)]
        top = a + (b - a) * fx[None, :]
        bot = c + (d - c) * fx[None, :]
        layer = top + (bot - top) * fy[:, None]
        out += layer * amp
        total += amp
        amp *= 0.5
    out /= total
    lo, hi = out.min(), out.max()
    if hi > lo:
        out = (out - lo) / (hi - lo)
    return out


class Canvas:
    def __init__(self, w, h, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), dtype=np.uint8)
        self.a[:, :] = fill

    # -- primitives ----------------------------------------------------
    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = c

    def get(self, x, y):
        return tuple(int(v) for v in self.a[y % self.h, x % self.w])

    def rect(self, x0, y0, x1, y1, c):
        """Inclusive rectangle fill."""
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.a[y, x] = c

    def rect_outline(self, x0, y0, x1, y1, c):
        for x in range(x0, x1 + 1):
            self.px(x, y0, c)
            self.px(x, y1, c)
        for y in range(y0, y1 + 1):
            self.px(x0, y, c)
            self.px(x1, y, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def ellipse(self, cx, cy, rx, ry, c, fill=True):
        for y in range(self.h):
            for x in range(self.w):
                d = ((x + 0.5 - cx) / max(rx, 0.01)) ** 2 + ((y + 0.5 - cy) / max(ry, 0.01)) ** 2
                if fill and d <= 1.0:
                    self.a[y, x] = c
                elif not fill and 0.55 <= d <= 1.0:
                    self.a[y, x] = c

    def noise_fill(self, x0, y0, x1, y1, colors, scale=4, seed=0, octaves=3, contrast=1.0):
        w, h = x1 - x0 + 1, y1 - y0 + 1
        n = value_noise(w, h, scale, seed, octaves)
        n = np.clip((n - 0.5) * contrast + 0.5, 0, 1)
        for yy in range(h):
            for xx in range(w):
                self.px(x0 + xx, y0 + yy, ramp(colors, n[yy, xx]))

    def speckle(self, x0, y0, x1, y1, colors, density, seed):
        rng = random.Random(seed)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if rng.random() < density:
                    self.px(x, y, rng.choice(colors))

    def mask_apply(self, mask, fn):
        """mask: set of (x,y); fn(x,y,current)->color"""
        for (x, y) in mask:
            if 0 <= x < self.w and 0 <= y < self.h:
                self.a[y, x] = fn(x, y, self.get(x, y))

    def carve(self, mask, depth_dark=0.55, rim_light=1.25, rim_dark=0.7):
        """Engrave a mask: darken inside, light rim on bottom/right edges, dark rim on top/left."""
        inside = set(mask)
        for (x, y) in inside:
            self.px(x, y, shade(self.get(x, y), depth_dark))
        for (x, y) in inside:
            for dx, dy, f in ((1, 0, rim_light), (0, 1, rim_light), (-1, 0, rim_dark), (0, -1, rim_dark)):
                nx, ny = x + dx, y + dy
                if (nx, ny) not in inside and 0 <= nx < self.w and 0 <= ny < self.h:
                    self.px(nx, ny, shade(self.get(nx, ny), f))

    def emboss(self, mask, light=1.25, dark=0.65):
        inside = set(mask)
        for (x, y) in inside:
            for dx, dy, f in ((-1, 0, light), (0, -1, light), (1, 0, dark), (0, 1, dark)):
                nx, ny = x + dx, y + dy
                if (nx, ny) not in inside:
                    self.px(x, y, shade(self.get(x, y), f))
                    break

    def outline(self, color, src_alpha_min=1):
        """Draw an outline around opaque pixels (for item sprites)."""
        a = self.a
        alpha = a[:, :, 3] >= src_alpha_min
        out = []
        for y in range(self.h):
            for x in range(self.w):
                if alpha[y, x]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and alpha[ny, nx]:
                        out.append((x, y))
                        break
        for (x, y) in out:
            self.a[y, x] = color

    def paste(self, other, ox, oy):
        for y in range(other.h):
            for x in range(other.w):
                c = tuple(int(v) for v in other.a[y, x])
                if c[3] > 0:
                    self.px(ox + x, oy + y, c)

    def blit_region(self, src, sx, sy, w, h, dx, dy):
        for y in range(h):
            for x in range(w):
                self.px(dx + x, dy + y, src.get(sx + x, sy + y))

    def scale(self, factor):
        img = Image.fromarray(self.a, 'RGBA').resize((self.w * factor, self.h * factor), Image.NEAREST)
        c = Canvas(self.w * factor, self.h * factor)
        c.a = np.array(img)
        return c

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Image.fromarray(self.a, 'RGBA').save(path, optimize=True)

    def copy(self):
        c = Canvas(self.w, self.h)
        c.a = self.a.copy()
        return c


def glyph_mask(lines, ox=0, oy=0):
    """Build a mask from an ascii-art list of strings ('#' = set)."""
    m = set()
    for y, row in enumerate(lines):
        for x, ch in enumerate(row):
            if ch == '#':
                m.add((ox + x, oy + y))
    return m


def circle_pts(cx, cy, r):
    pts = set()
    for a in range(0, 360, 4):
        pts.add((int(round(cx + r * math.cos(math.radians(a)))), int(round(cy + r * math.sin(math.radians(a))))))
    return pts
