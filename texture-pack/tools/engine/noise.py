"""Seamless (periodic) noise and field operations on square float32 images.

Every function returns arrays that tile perfectly: lattices wrap around, distances are measured on a
torus and blurs are done in the frequency domain. Coordinates are in "texture units": the image spans
[0, 1) in both x (columns) and y (rows).
"""
import numpy as np

F32 = np.float32


def rng(seed):
    return np.random.default_rng(seed & 0xFFFFFFFF)


def grid(n):
    """Pixel-centre coordinates in [0, 1) for an n x n image: (x, y) arrays."""
    u = (np.arange(n, dtype=F32) + 0.5) / n
    return np.meshgrid(u, u)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def perlin(n, freq, seed, x=None, y=None):
    """Tileable gradient noise in roughly [-1, 1]; freq = lattice cells across the texture.

    Optional x, y (texture units, any shape) sample the same periodic field at warped positions.
    """
    r = rng(seed)
    fx, fy = (freq, freq) if np.isscalar(freq) else freq
    ang = r.uniform(0, 2 * np.pi, (fy, fx)).astype(F32)
    gx, gy = np.cos(ang), np.sin(ang)
    if x is None:
        x, y = grid(n)
    X = x * fx
    Y = y * fy
    xi = np.floor(X).astype(np.int64)
    yi = np.floor(Y).astype(np.int64)
    xf = (X - xi).astype(F32)
    yf = (Y - yi).astype(F32)
    x0, x1 = xi % fx, (xi + 1) % fx
    y0, y1 = yi % fy, (yi + 1) % fy

    def dot(ix, iy, dx, dy):
        return gx[iy, ix] * dx + gy[iy, ix] * dy

    n00 = dot(x0, y0, xf, yf)
    n10 = dot(x1, y0, xf - 1, yf)
    n01 = dot(x0, y1, xf, yf - 1)
    n11 = dot(x1, y1, xf - 1, yf - 1)
    u, v = _fade(xf), _fade(yf)
    a = n00 + u * (n10 - n00)
    b = n01 + u * (n11 - n01)
    return ((a + v * (b - a)) * 1.414).astype(F32)


def fbm(n, freq, seed, octaves=5, gain=0.5, lacunarity=2, x=None, y=None, stretch=(1, 1)):
    """Fractal sum of tileable gradient noise, normalised to roughly [-1, 1].

    stretch=(sx, sy) multiplies the lattice frequency per axis (e.g. (1, 4) for vertical grain).
    freq may also be an (fx, fy) pair.
    """
    if not np.isscalar(freq):
        stretch = (freq[0] * stretch[0], freq[1] * stretch[1])
        freq = 1
    total = np.zeros((n, n) if x is None else np.shape(x), F32)
    amp, norm = 1.0, 0.0
    f = freq
    for o in range(octaves):
        fr = (max(1, int(round(f * stretch[0]))), max(1, int(round(f * stretch[1]))))
        total += amp * perlin(n, fr, seed + 101 * o, x, y)
        norm += amp
        amp *= gain
        f *= lacunarity
    return total / norm


def ridged(n, freq, seed, octaves=5, gain=0.5, sharp=2.0, **kw):
    """Ridged multifractal in [0, 1]: thin bright ridges (veins, cracks, bark fissures).

    freq may be an (fx, fy) pair; stretch=(sx, sy) multiplies it per axis.
    """
    total = np.zeros((n, n), F32)
    stretch = kw.get('stretch', (1, 1))
    if not np.isscalar(freq):
        stretch = (freq[0] * stretch[0], freq[1] * stretch[1])
        freq = 1
    amp, norm, f = 1.0, 0.0, freq
    for o in range(octaves):
        fr = (max(1, int(round(f * stretch[0]))), max(1, int(round(f * stretch[1]))))
        r = 1.0 - np.abs(perlin(n, fr, seed + 977 * o))
        total += amp * r ** sharp
        norm += amp
        amp *= gain
        f *= 2
    return total / norm


def worley(n, freq, seed, jitter=0.9, x=None, y=None, metric='euclid'):
    """Tileable cellular noise.

    Returns (f1, f2, cell_id) where distances are in cell units (1.0 = one cell) and cell_id is an
    integer per feature point (stable for the seed), so callers can colour cells individually.
    """
    r = rng(seed)
    fx, fy = (freq, freq) if np.isscalar(freq) else freq
    off = r.uniform(0.5 - jitter / 2, 0.5 + jitter / 2, (fy, fx, 2)).astype(F32)
    if x is None:
        x, y = grid(n)
    X = x * fx
    Y = y * fy
    cx = np.floor(X).astype(np.int64)
    cy = np.floor(Y).astype(np.int64)
    f1 = np.full(X.shape, 1e9, F32)
    f2 = np.full(X.shape, 1e9, F32)
    cid = np.zeros(X.shape, np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ix = cx + dx
            iy = cy + dy
            wx, wy = ix % fx, iy % fy
            px = ix + off[wy, wx, 0]
            py = iy + off[wy, wx, 1]
            if metric == 'manhattan':
                d = np.abs(X - px) + np.abs(Y - py)
            elif metric == 'cheby':
                d = np.maximum(np.abs(X - px), np.abs(Y - py))
            else:
                d = np.sqrt((X - px) ** 2 + (Y - py) ** 2)
            better = d < f1
            f2 = np.where(better, f1, np.minimum(f2, d))
            cid = np.where(better, wy * fx + wx, cid)
            f1 = np.where(better, d, f1)
    return f1.astype(F32), f2.astype(F32), cid


def cell_random(cid, seed, count=None):
    """A stable random value in [0, 1) per cell id."""
    r = rng(seed)
    size = int(cid.max()) + 1 if count is None else count
    table = r.random(size).astype(F32)
    return table[cid]


def blur(a, sigma):
    """Periodic Gaussian blur (sigma in pixels) via FFT. Works on (n, n) or (n, n, c)."""
    if sigma <= 0:
        return a
    n = a.shape[0]
    f = np.fft.fftfreq(n).astype(F32)
    kx = np.exp(-2 * (np.pi * f * sigma) ** 2)
    k = np.outer(kx, kx)
    if a.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(a) * k)).astype(F32)
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        out[..., c] = np.real(np.fft.ifft2(np.fft.fft2(a[..., c]) * k))
    return out


def sample(a, x, y):
    """Bilinear periodic sampling of image a at texture coordinates (x, y)."""
    n = a.shape[0]
    X = x * n - 0.5
    Y = y * n - 0.5
    x0 = np.floor(X).astype(np.int64)
    y0 = np.floor(Y).astype(np.int64)
    fx = (X - x0).astype(F32)
    fy = (Y - y0).astype(F32)
    x0 %= n
    y0 %= n
    x1 = (x0 + 1) % n
    y1 = (y0 + 1) % n
    if a.ndim == 3:
        fx = fx[..., None]
        fy = fy[..., None]
    top = a[y0, x0] * (1 - fx) + a[y0, x1] * fx
    bot = a[y1, x0] * (1 - fx) + a[y1, x1] * fx
    return (top * (1 - fy) + bot * fy).astype(F32)


def warp(a, amount, seed, freq=4, octaves=3):
    """Domain-warp image a by a periodic noise displacement (amount in texture units)."""
    n = a.shape[0]
    x, y = grid(n)
    dx = fbm(n, freq, seed, octaves)
    dy = fbm(n, freq, seed + 55, octaves)
    return sample(a, x + amount * dx, y + amount * dy)


def warped_coords(n, amount, seed, freq=4, octaves=3):
    x, y = grid(n)
    return x + amount * fbm(n, freq, seed, octaves), y + amount * fbm(n, freq, seed + 55, octaves)


def norm01(a):
    lo, hi = float(a.min()), float(a.max())
    return ((a - lo) / (hi - lo + 1e-9)).astype(F32)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-12), 0, 1)
    return (t * t * (3 - 2 * t)).astype(F32)


def shift(a, dx, dy):
    """Periodic integer shift (positive dx moves content right)."""
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)
