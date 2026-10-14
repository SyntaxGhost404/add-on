"""Colour helpers: hex parsing, ramps, and gentle hue/saturation/value variation."""
import numpy as np

from .noise import F32


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], F32)


def ramp(t, stops):
    """Map t (any shape, 0..1) through colour stops [(pos, '#hex' | rgb), ...] -> (..., 3)."""
    pos = np.array([p for p, _ in stops], F32)
    cols = np.array([hexrgb(c) if isinstance(c, str) else c for _, c in stops], F32)
    t = np.clip(t, pos[0], pos[-1])
    out = np.empty(np.shape(t) + (3,), F32)
    for ch in range(3):
        out[..., ch] = np.interp(t, pos, cols[:, ch])
    return out


def mix(a, b, t):
    t = np.asarray(t, F32)
    if t.ndim == 2 and np.ndim(a) == 3:
        t = t[..., None]
    return (a * (1 - t) + b * t).astype(F32)


def rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.max(rgb, axis=-1)
    mn = np.min(rgb, axis=-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = np.where(m, (mx - r) / np.where(m, d, 1), 0)
    gc = np.where(m, (mx - g) / np.where(m, d, 1), 0)
    bc = np.where(m, (mx - b) / np.where(m, d, 1), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2.0 + rc - bc, 4.0 + gc - rc))
    h = np.where(m, (h / 6.0) % 1.0, 0)
    s = np.where(mx > 1e-6, d / np.where(mx > 1e-6, mx, 1), 0)
    return np.stack([h, s, mx], axis=-1).astype(F32)


def hsv_to_rgb(hsv):
    h, s, v = hsv[..., 0] % 1.0, np.clip(hsv[..., 1], 0, 1), np.clip(hsv[..., 2], 0, 1)
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1).astype(F32)


def vary(rgb, dh=None, ds=None, dv=None):
    """Shift hue (turns), scale saturation and value by per-pixel fields (or scalars)."""
    hsv = rgb_to_hsv(rgb)
    if dh is not None:
        hsv[..., 0] = hsv[..., 0] + dh
    if ds is not None:
        hsv[..., 1] = hsv[..., 1] * (1 + ds)
    if dv is not None:
        hsv[..., 2] = hsv[..., 2] * (1 + dv)
    return hsv_to_rgb(hsv)


def grey(rgb, keep=0.0):
    """Desaturate to luminance (keep = fraction of chroma retained)."""
    l = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[..., None]
    return (l + (rgb - l) * keep).astype(F32)


def match_mean(rgb, target, mask=None, strength=1.0):
    """Scale rgb so its mean luminance moves toward target (sRGB 0..1)."""
    l = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    cur = float(l[mask].mean() if mask is not None else l.mean())
    if cur < 1e-4:
        return rgb
    k = (target / cur) ** strength
    return np.clip(rgb * k, 0, 1).astype(F32)
