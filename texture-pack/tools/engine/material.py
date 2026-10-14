"""Material finishing: baked lighting, cavity occlusion, tinting conventions and tier export.

A recipe returns a `Tex` at the master resolution (MASTER x MASTER). `finish()` bakes the light into
the albedo, and `export()` filters it down to every tier, keeps cut-outs crisp, dilates colour under
transparent pixels and writes PNG/TGA files.
"""
import os

import numpy as np
from PIL import Image

from .noise import blur, F32

MASTER = 256
TIERS = (32, 64, 128)

# Light directions in texture space (x right, y down, z out of the surface).
# 'top': soft key light from above and slightly left, for faces the engine never rotates.
# 'over': straight overhead, direction-free, for faces the engine rotates at random (isotropic).
_L_TOP = np.array([-0.32, -0.62, 0.72], F32)
_L_TOP /= np.linalg.norm(_L_TOP)


def srgb_to_lin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(F32)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055).astype(F32)


def luminance(rgb):
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(F32)


class Tex:
    """A material at master resolution.

    albedo  (n, n, 3) sRGB in [0, 1]
    height  (n, n) relief in [0, 1] or None (flat)
    alpha   (n, n) coverage in [0, 1] or None (opaque)
    light   'top' | 'over' | 'none'
    bump    normal strength (1.0 = moderate relief)
    ao      cavity occlusion strength (0..1)
    cutout  alpha is a hard alpha-test mask (leaves, plants): exported as 0/255
    tint_mask (n, n) bool: written into the alpha channel instead of transparency (grass side .tga)
    tint_albedo (n, n, 3) or None: full-tile albedo of the tinted layer; `albedo` is then the untinted
              layer, and each tier picks between them with its own downsampled mask (no grey fringes)
    """

    def __init__(self, albedo, height=None, alpha=None, *, light='top', bump=1.0, ao=0.45, cutout=False,
                 tint_mask=None, sharpen=0.35, gloss=0.0, emissive=None, tint_albedo=None):
        self.albedo = np.clip(albedo, 0, 1).astype(F32)
        self.height = None if height is None else np.clip(height, 0, 1).astype(F32)
        self.alpha = None if alpha is None else np.clip(alpha, 0, 1).astype(F32)
        self.light = light
        self.bump = bump
        self.ao = ao
        self.cutout = cutout
        self.tint_mask = tint_mask
        self.sharpen = sharpen
        self.gloss = gloss
        self.emissive = emissive
        self.tint_albedo = None if tint_albedo is None else np.clip(tint_albedo, 0, 1).astype(F32)

    def but(self, **changes):
        """A copy with some attributes replaced."""
        t = Tex.__new__(Tex)
        t.__dict__.update(self.__dict__)
        for k, v in changes.items():
            setattr(t, k, v)
        return t


def normals(h, bump):
    n = h.shape[0]
    s = bump * n / 48.0
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * s
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * s
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    return -gx * inv, -gy * inv, nz * inv


def cavity(h, radii=(1.5, 5.0, 14.0)):
    """Multi-scale cavity term in [0, 1] (1 = deep crevice) from a height field."""
    acc = np.zeros_like(h)
    for r in radii:
        acc += np.clip((blur(h, r) - h) * 6.0, 0, 1)
    return acc / len(radii)


def finish(t):
    """Return baked RGBA (float, sRGB) at master resolution."""
    rgb = t.albedo
    if t.height is not None and t.light != 'none':
        nx, ny, nz = normals(t.height, t.bump)
        if t.light == 'over':
            shade = nz
        else:
            shade = (nx * _L_TOP[0] + ny * _L_TOP[1] + nz * _L_TOP[2]) / _L_TOP[2]
        shade = np.clip(shade, 0.3, 1.55)
        cav = cavity(t.height)
        occl = 1.0 - t.ao * cav
        lin = srgb_to_lin(rgb)
        # cool sky fill in shadow, faint warmth on lit relief
        shadow = np.clip((1.0 - shade) * 0.8 + (1.0 - occl) * 1.2, 0, 1)[..., None]
        light = np.clip(shade - 1.0, 0, 1)[..., None]
        cool = np.array([0.93, 0.98, 1.08], F32)
        warm = np.array([1.05, 1.01, 0.95], F32)
        lin = lin * (shade * occl)[..., None]
        lin = lin * (1 + (cool - 1) * shadow * 0.6) * (1 + (warm - 1) * light)
        if t.gloss > 0:
            hx, hy, hz = -0.25, -0.45, 0.86
            hl = np.clip(nx * hx + ny * hy + nz * hz, 0, 1) ** 40
            lin = lin + t.gloss * hl[..., None]
        rgb = lin_to_srgb(lin)
    if t.emissive is not None:
        rgb = np.clip(rgb + t.emissive, 0, 1)
    a = np.ones(rgb.shape[:2], F32) if t.alpha is None else t.alpha
    return np.dstack([rgb, a]).astype(F32)


# ---------------------------------------------------------------------------------- tier export
def _down2(rgba, cutout):
    n = rgba.shape[0] // 2
    a = rgba[..., 3]
    prem = rgba[..., :3] * a[..., None]
    p = prem.reshape(n, 2, n, 2, 3).mean(axis=(1, 3))
    aa = a.reshape(n, 2, n, 2).mean(axis=(1, 3))
    rgb = np.where(aa[..., None] > 1e-4, p / np.maximum(aa[..., None], 1e-4), rgba[..., :3].reshape(n, 2, n, 2, 3).mean(axis=(1, 3)))
    return np.dstack([rgb, aa]).astype(F32)


def _sharpen(rgb, amount, sigma=0.7):
    if amount <= 0:
        return rgb
    return np.clip(rgb + amount * (rgb - blur(rgb, sigma)), 0, 1).astype(F32)


def dilate(rgb, mask, iterations=12):
    """Fill colour under transparent pixels from opaque neighbours (prevents dark mip halos)."""
    rgb = rgb.copy()
    m = mask.astype(F32)
    for _ in range(iterations):
        if m.min() > 0:
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros_like(m)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            mm = np.roll(np.roll(m, dy, 0), dx, 1)
            acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * mm[..., None]
            cnt += mm
        grow = (m == 0) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][..., None]
        m = np.where(grow, 1.0, m).astype(F32)
    if m.min() == 0:
        mean = rgb[m > 0].mean(axis=0) if (m > 0).any() else np.full(3, 0.5, F32)
        rgb[m == 0] = mean
    return rgb


def cutout_alpha(a, coverage):
    """Binary alpha for a tier that keeps the master's coverage. A fixed 50% threshold erases stems and
    blades thinner than a tier texel, so the threshold drops (never below 0.2) until the opaque share
    matches the master's. It never rises above 0.5, so no pixel that a plain threshold keeps is lost."""
    t = 0.5
    if 0.0 < coverage < 1.0:
        t = min(0.5, max(0.2, float(np.quantile(a, 1.0 - coverage))))
    return (a >= t).astype(F32)


def to_tier(rgba_master, res, *, cutout=False, sharpen=0.35):
    rgba = rgba_master
    while rgba.shape[0] > res:
        rgba = _down2(rgba, cutout)
    rgb, a = rgba[..., :3], rgba[..., 3]
    rgb = _sharpen(rgb, sharpen if res < MASTER else 0)
    if cutout:
        a = cutout_alpha(a, float((rgba_master[..., 3] >= 0.5).mean()))
        rgb = dilate(rgb, a > 0)
    elif a.min() < 1.0:
        rgb = dilate(rgb, a > 0.02)
    return np.dstack([rgb, a]).astype(F32)


def to_uint8(rgba):
    return np.clip(np.round(rgba * 255), 0, 255).astype(np.uint8)


def save_image(rgba8, path, ext='png', opaque=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if opaque:
        im = Image.fromarray(rgba8[..., :3], 'RGB')
    else:
        im = Image.fromarray(rgba8, 'RGBA')
    if ext == 'tga':
        im.save(path + '.tga', format='TGA')
    else:
        im.save(path + '.png', optimize=True)


def stack_frames(frames):
    """Vertical flipbook strip from a list of equally sized RGBA arrays."""
    return np.concatenate(frames, axis=0)


def edge_weight(n, inner=0.30, outer=0.08):
    """1.0 within `outer` of any edge, 0.0 beyond `inner`: keeps borders identical across variants."""
    u = (np.arange(n, dtype=F32) + 0.5) / n
    d1 = np.minimum(u, 1 - u)
    d = np.minimum(d1[None, :], d1[:, None])
    t = np.clip((d - outer) / (inner - outer), 0, 1)
    return (1 - t * t * (3 - 2 * t)).astype(F32)


def edge_variant(base, var, inner=0.30, outer=0.08):
    """Variant whose edge band equals `base` (seamless next to any other variant of the same base)."""
    w = edge_weight(base.albedo.shape[0], inner, outer)
    alb = base.albedo * w[..., None] + var.albedo * (1 - w[..., None])
    h = None
    if base.height is not None and var.height is not None:
        h = base.height * w + var.height * (1 - w)
    return var.but(albedo=alb.astype(F32), height=h)


def mask_to_tier(mask, res):
    m = mask.astype(F32)
    while m.shape[0] > res:
        n = m.shape[0] // 2
        m = m.reshape(n, 2, n, 2).mean(axis=(1, 3))
    return m >= 0.5


def tiers(t, resolutions, cutout=False):
    """Finish a Tex once and filter it to each resolution: {res: RGBA float}.

    Tint-masked textures (grass side) get their alpha replaced by the per-tier mask, and when the
    recipe supplies `tint_albedo`, tinted and untinted layers are filtered separately and picked by
    that mask, so no tier shows a grey or brown fringe along the boundary.
    """
    rgba = finish(t)
    alt = finish(t.but(albedo=t.tint_albedo)) if t.tint_albedo is not None else None
    out = {}
    for res in resolutions:
        tier = to_tier(rgba, res, cutout=t.cutout or cutout, sharpen=t.sharpen)
        if t.tint_mask is not None:
            m = mask_to_tier(t.tint_mask, res)
            if alt is not None:
                tb = to_tier(alt, res, sharpen=t.sharpen)
                tier[..., :3] = np.where(m[..., None], tb[..., :3], tier[..., :3])
            tier[..., 3] = m.astype(F32)
        out[res] = tier
    return out


def bake_tint(t, color):
    """Inventory ('carried') version of a tint-masked or grey texture: tint baked into the colour."""
    c = np.asarray(color, F32)
    if t.tint_mask is None:
        return t.but(albedo=np.clip(t.albedo * c, 0, 1).astype(F32))
    tinted = (t.tint_albedo if t.tint_albedo is not None else t.albedo) * c
    alb = np.where(t.tint_mask[..., None], tinted, t.albedo)
    return t.but(albedo=np.clip(alb, 0, 1).astype(F32), tint_mask=None, tint_albedo=None)
