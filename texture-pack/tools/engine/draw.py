"""Anti-aliased vector drawing on the master canvas, in block units (0..16 across, like the vanilla
pixel grid, so functional layouts such as insets and hinges line up). All masks are float 0..1.
"""
import numpy as np

from .noise import F32, smoothstep
from .material import MASTER

N = MASTER
U = N / 16.0                     # master pixels per block unit
_yy, _xx = np.mgrid[0:N, 0:N].astype(F32)
X = (_xx + 0.5) / U              # block-unit coordinates of pixel centres
Y = (_yy + 0.5) / U
AA = 1.0 / U                     # one master pixel, in block units


def rect(x0, y0, x1, y1, soft=AA):
    mx = smoothstep(x0 - soft, x0 + soft, X) * (1 - smoothstep(x1 - soft, x1 + soft, X))
    my = smoothstep(y0 - soft, y0 + soft, Y) * (1 - smoothstep(y1 - soft, y1 + soft, Y))
    return (mx * my).astype(F32)


def bevel(x0, y0, x1, y1, width=0.6):
    """0 at the rectangle edge rising to 1 at `width` inside (a raised, chamfered panel)."""
    d = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Y - y0, y1 - Y))
    return np.clip(d / width, 0, 1).astype(F32)


def circle(cx, cy, r, soft=AA):
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    return (1 - smoothstep(r - soft, r + soft, d)).astype(F32)


def ellipse(cx, cy, rx, ry, angle=0.0, soft=AA):
    c, s = np.cos(angle), np.sin(angle)
    dx, dy = X - cx, Y - cy
    u = (dx * c + dy * s) / rx
    v = (-dx * s + dy * c) / ry
    d = np.sqrt(u * u + v * v)
    k = soft / min(rx, ry)
    return (1 - smoothstep(1 - k, 1 + k, d)).astype(F32)


def seg_dist(ax, ay, bx, by, xs=None, ys=None):
    xs = X if xs is None else xs
    ys = Y if ys is None else ys
    px, py = xs - ax, ys - ay
    vx, vy = bx - ax, by - ay
    t = np.clip((px * vx + py * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
    dx, dy = px - t * vx, py - t * vy
    return np.sqrt(dx * dx + dy * dy), t


def polyline(points, widths, soft=AA, wrap=False):
    """Stroke a polyline with per-point widths (block units). Returns (mask, along-param 0..1)."""
    pts = np.asarray(points, F32)
    w = np.broadcast_to(np.asarray(widths, F32), (len(pts),))
    seg_len = np.sqrt(((pts[1:] - pts[:-1]) ** 2).sum(1))
    total = seg_len.sum() + 1e-9
    acc = np.concatenate([[0], np.cumsum(seg_len)]) / total
    mask = np.zeros((N, N), F32)
    along = np.zeros((N, N), F32)
    offsets = [(0, 0)]
    if wrap:
        offsets = [(dx, dy) for dx in (-16, 0, 16) for dy in (-16, 0, 16)]
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        rr = max(w[i], w[i + 1]) / 2 + 2 * AA
        for ox, oy in offsets:
            x_lo, x_hi = min(ax, bx) + ox - rr, max(ax, bx) + ox + rr
            y_lo, y_hi = min(ay, by) + oy - rr, max(ay, by) + oy + rr
            if x_hi < 0 or y_hi < 0 or x_lo > 16 or y_lo > 16:
                continue
            c0, c1 = max(0, int(x_lo * U) - 1), min(N, int(x_hi * U) + 2)
            r0, r1 = max(0, int(y_lo * U) - 1), min(N, int(y_hi * U) + 2)
            xs, ys = X[r0:r1, c0:c1], Y[r0:r1, c0:c1]
            d, t = seg_dist(ax + ox, ay + oy, bx + ox, by + oy, xs, ys)
            rad = (w[i] + (w[i + 1] - w[i]) * t) / 2
            m = 1 - smoothstep(rad - soft, rad + soft, d)
            sub = mask[r0:r1, c0:c1]
            upd = m > sub
            along[r0:r1, c0:c1] = np.where(upd, acc[i] + t * (acc[i + 1] - acc[i]), along[r0:r1, c0:c1])
            mask[r0:r1, c0:c1] = np.maximum(sub, m)
    return mask, along


def bezier(p0, p1, p2, p3, steps=24):
    t = np.linspace(0, 1, steps, dtype=F32)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, F32) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def leaf(cx, cy, angle, length, width, tip=1.0, soft=AA, xs=None, ys=None):
    """Lanceolate leaf from its base (cx, cy) pointing along `angle`. Returns (mask, u along, v across)."""
    xs = X if xs is None else xs
    ys = Y if ys is None else ys
    c, s = np.cos(angle), np.sin(angle)
    dx, dy = xs - cx, ys - cy
    u = (dx * c + dy * s) / length
    v = (-dx * s + dy * c)
    half = width / 2 * np.sin(np.clip(u, 0, 1) * np.pi) ** (0.7 * tip)
    inside = (u >= 0) & (u <= 1)
    d = np.abs(v) - half
    m = (1 - smoothstep(-soft, soft, d)) * inside
    return m.astype(F32), u.astype(F32), (v / (width / 2 + 1e-6)).astype(F32)


def polygon(points, soft=AA):
    """Filled polygon (even-odd), anti-aliased by distance to edges."""
    pts = np.asarray(points, F32)
    inside = np.zeros((N, N), bool)
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        cond = ((yi > Y) != (yj > Y)) & (X < (xj - xi) * (Y - yi) / (yj - yi + 1e-9) + xi)
        inside ^= cond
        j = i
    dmin = np.full((N, N), 1e9, F32)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        d, _ = seg_dist(a[0], a[1], b[0], b[1])
        dmin = np.minimum(dmin, d)
    sd = np.where(inside, -dmin, dmin)
    return (1 - smoothstep(-soft, soft, sd)).astype(F32)


class Layer:
    """Accumulates albedo / height / alpha with painter's-order compositing."""

    def __init__(self, albedo=None, height=None, alpha=None):
        self.albedo = np.zeros((N, N, 3), F32) if albedo is None else albedo.astype(F32).copy()
        self.height = np.zeros((N, N), F32) if height is None else height.astype(F32).copy()
        self.alpha = np.zeros((N, N), F32) if alpha is None else alpha.astype(F32).copy()

    def paint(self, mask, color, height=None, alpha=1.0, height_mode='max'):
        m = np.clip(mask, 0, 1)[..., None]
        col = color if np.ndim(color) == 3 else np.broadcast_to(np.asarray(color, F32), (N, N, 3))
        self.albedo = self.albedo * (1 - m) + col * m
        if height is not None:
            h = height if np.ndim(height) == 2 else np.full((N, N), height, F32)
            mm = m[..., 0]
            if height_mode == 'max':
                self.height = np.where(mm > 0.5, np.maximum(self.height, h), self.height)
            else:
                self.height = self.height * (1 - mm) + h * mm
        self.alpha = np.maximum(self.alpha, np.clip(mask, 0, 1) * alpha)
        return self


def capsules(segs, values, soft=AA, wrap=True):
    """Rasterise many short tapered strokes in one pass each (needles, fibres, twigs, rootlets).

    segs: (k, 7) array of ax, ay, bx, by, width_a, width_b, z in block units; values: (k, C).
    A stroke covers earlier strokes where its z is not lower. Returns (value (N, N, C), coverage, z).
    """
    segs = np.asarray(segs, F32)
    values = np.asarray(values, F32)
    C = values.shape[1]
    val = np.zeros((N, N, C), F32)
    cov = np.zeros((N, N), F32)
    zz = np.full((N, N), -1e9, F32)
    for (ax, ay, bx, by, wa, wb, z), v in zip(segs, values):
        rr = max(wa, wb) / 2 + 2 * AA
        c0, c1 = int(np.floor((min(ax, bx) - rr) * U)), int(np.ceil((max(ax, bx) + rr) * U)) + 1
        r0, r1 = int(np.floor((min(ay, by) - rr) * U)), int(np.ceil((max(ay, by) + rr) * U)) + 1
        cols, rows = np.arange(c0, c1), np.arange(r0, r1)
        if not wrap:
            cols = cols[(cols >= 0) & (cols < N)]
            rows = rows[(rows >= 0) & (rows < N)]
            if not len(cols) or not len(rows):
                continue
        xs, ys = ((cols + 0.5) / U)[None, :], ((rows + 0.5) / U)[:, None]
        d, t = seg_dist(ax, ay, bx, by, xs, ys)
        rad = (wa + (wb - wa) * t) / 2
        m = 1 - smoothstep(rad - soft, rad + soft, d)
        ix = np.ix_(rows % N, cols % N)
        sub_z = zz[ix]
        take = m * (z >= sub_z - 1e-6)
        val[ix] = val[ix] * (1 - take[..., None]) + v * take[..., None]
        cov[ix] = np.maximum(cov[ix], m)
        zz[ix] = np.where(take > 0.5, np.maximum(sub_z, z), sub_z)
    return val, cov, zz


def scatter(seed, count, length, width, *, angle=None, spread=np.pi, curve=0.0, parts=1, z=None, taper=0.3):
    """Random stroke geometry for `capsules`: returns (segs, per-stroke index) with `parts` segments
    per stroke (gently curved when curve > 0). Lengths and widths are (lo, hi) in block units."""
    from .noise import rng
    r = rng(seed)
    segs, owner = [], []
    for i in range(count):
        x, y = r.uniform(0, 16), r.uniform(0, 16)
        a = r.uniform(0, 2 * np.pi) if angle is None else angle + r.uniform(-spread, spread)
        L = r.uniform(*length) / parts
        w = r.uniform(*width)
        bend = r.uniform(-curve, curve)
        zi = r.uniform(0, 1) if z is None else z
        for p in range(parts):
            w0 = w * (1 - taper * p / parts)
            w1 = w * (1 - taper * (p + 1) / parts)
            nx, ny = x + np.cos(a) * L, y + np.sin(a) * L
            segs.append((x, y, nx, ny, w0, w1, zi + 0.001 * p))
            owner.append(i)
            x, y, a = nx, ny, a + bend
    return np.asarray(segs, F32), np.asarray(owner)


def fractures(seed, count, length=(6.0, 14.0), width=(0.12, 0.28), kinks=5, jag=0.6, plane=0.9):
    """Long, thin, slightly kinked fracture lines across the tile (wrapping), each with a soft
    one-sided sheet that fades away from the line, like an inclined crack plane seen inside ice or
    glass. Returns (line mask 0..1, plane glow 0..1)."""
    from .noise import rng
    r = rng(seed)
    lines = np.zeros((N, N), F32)
    glow = np.zeros((N, N), F32)
    offs = [(dx, dy) for dx in (-16, 0, 16) for dy in (-16, 0, 16)]
    for _ in range(count):
        x, y = r.uniform(0, 16), r.uniform(0, 16)
        a = r.uniform(0, np.pi)
        L = r.uniform(*length) / kinks
        w = r.uniform(*width)
        side = r.choice([-1.0, 1.0])
        depth = r.uniform(0.5, 1.0)
        best = np.full((N, N), 1e9, F32)
        sgn = np.zeros((N, N), F32)
        for k in range(kinks):
            a2 = a + r.uniform(-jag, jag) * 0.5
            nx, ny = x + np.cos(a2) * L, y + np.sin(a2) * L
            for ox, oy in offs:
                d, t = seg_dist(x + ox, y + oy, nx + ox, ny + oy)
                cross = (nx - x) * (Y - (y + oy)) - (ny - y) * (X - (x + ox))
                closer = d < best
                best = np.where(closer, d, best)
                sgn = np.where(closer, np.sign(cross), sgn)
            x, y = nx, ny
        lines = np.maximum(lines, 1 - smoothstep(w / 2 - AA, w / 2 + AA, best))
        sheet = np.exp(-best / plane) * (sgn == side) * depth
        glow = np.maximum(glow, sheet.astype(F32))
    return lines, glow


def fibres(seed, count, length, width, lo=0.3, hi=1.0, *, parts=3, curve=0.35, angle=None, spread=np.pi,
           z0=0.0, jitter=0.15):
    """Short strokes whose brightness rises from base to tip (moss shoots, fur, hyphae, needles).

    Returns (luminance, coverage, z) where z = z0 + position along the stroke.
    """
    from .noise import rng
    segs, owner = scatter(seed, count, length, width, angle=angle, spread=spread, curve=curve, parts=parts)
    r = rng(seed + 7)
    gain = r.uniform(1 - jitter, 1 + jitter, owner.max() + 1)[owner]
    part = np.arange(len(segs)) % parts
    frac = (part + 1) / parts
    vals = (lo + (hi - lo) * frac) * gain
    segs[:, 6] = z0 + frac + 0.1 * r.uniform(0, 1, owner.max() + 1)[owner]
    lum, cov, zz = capsules(segs, vals[:, None])
    return lum[..., 0], cov, np.where(cov > 0.02, zz, z0)
