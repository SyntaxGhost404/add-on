#!/usr/bin/env python3
"""Diorama preview renderer (development aid).

Renders a small voxel scene in isometric view using the pack's exported textures, approximating the
standard renderer: fixed face brightness (top 1.0, sides 0.8 / 0.62), smooth-lighting style corner
occlusion and biome tinting. It is a review tool for tiling, colour harmony and readability. It
doesn't reproduce the game's renderer.
"""
import numpy as np
from PIL import Image

FACE_LIGHT = {'up': 1.0, 'south': 0.8, 'east': 0.62}


def _face_quad(x, y, z, face, s):
    """Screen-space corners (top-left, top-right, bottom-right, bottom-left) of a block face."""
    def p(px, py, pz):
        return np.array([(px - pz) * s, (px + pz) * s * 0.5 - py * s], np.float32)
    if face == 'up':
        return [p(x, y + 1, z), p(x + 1, y + 1, z), p(x + 1, y + 1, z + 1), p(x, y + 1, z + 1)]
    if face == 'south':
        return [p(x, y + 1, z + 1), p(x + 1, y + 1, z + 1), p(x + 1, y, z + 1), p(x, y, z + 1)]
    return [p(x + 1, y + 1, z + 1), p(x + 1, y + 1, z), p(x + 1, y, z), p(x + 1, y, z + 1)]


def render(world, textures, scale=26, ao=True, sky=(0.62, 0.74, 0.88)):
    """world: dict (x, y, z) -> block name. textures: block name -> {face: (rgba float, tint rgb or None)}.
    With sky=None the image is RGBA and transparent where no block was drawn."""
    s = scale
    corners = []
    for (x, y, z) in world:
        for face in ('up', 'south', 'east'):
            corners.extend(_face_quad(x, y, z, face, s))
    corners = np.array(corners)
    lo = corners.min(0)
    hi = corners.max(0)
    W = int(hi[0] - lo[0]) + 24
    H = int(hi[1] - lo[1]) + 24
    ox = -lo[0] + 12
    oy = -lo[1] + 12
    img = np.zeros((H, W, 3), np.float32)
    img[:] = sky if sky is not None else 0.0
    cov = np.zeros((H, W), np.float32)
    solid = set(world)

    def occ(x, y, z):
        return 1 if (x, y, z) in solid else 0

    order = sorted(world, key=lambda p: (p[0] + p[2], p[1]))
    for (x, y, z) in order:
        name = world[(x, y, z)]
        tex = textures.get(name)
        if tex is None:
            continue
        for face, nb in (('up', (x, y + 1, z)), ('south', (x, y, z + 1)), ('east', (x + 1, y, z))):
            if nb in solid:
                continue
            rgba, tint = tex.get(face, tex.get('side', tex.get('*')))
            q = _face_quad(x, y, z, face, s)
            q = [c + np.array([ox, oy]) for c in q]
            _draw_face(img, q, rgba, tint, FACE_LIGHT[face], _corner_ao(occ, x, y, z, face) if ao else None, cov)
    if sky is None:
        img = np.dstack([img, cov])
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def _corner_ao(occ, x, y, z, face):
    """Per-corner occlusion (tl, tr, br, bl) like smooth lighting: 0 neighbours = 1.0."""
    if face == 'up':
        Y = y + 1
        def c(dx, dz):
            a = occ(x + dx, Y, z)
            b = occ(x, Y, z + dz)
            d = occ(x + dx, Y, z + dz)
            return 1.0 - 0.18 * (a + b + (d if not (a and b) else 1))
        return [c(-1, -1), c(1, -1), c(1, 1), c(-1, 1)]
    if face == 'south':
        Z = z + 1
        def c(dx, dy):
            a = occ(x + dx, y, Z)
            b = occ(x, y + dy, Z)
            d = occ(x + dx, y + dy, Z)
            return 1.0 - 0.18 * (a + b + (d if not (a and b) else 1))
        return [c(-1, 1), c(1, 1), c(1, -1), c(-1, -1)]
    X = x + 1
    def c(dz, dy):
        a = occ(X, y, z + dz)
        b = occ(X, y + dy, z)
        d = occ(X, y + dy, z + dz)
        return 1.0 - 0.18 * (a + b + (d if not (a and b) else 1))
    return [c(1, 1), c(-1, 1), c(-1, -1), c(1, -1)]


def _draw_face(img, q, rgba, tint, light, ao, cov):
    tl, tr, br, bl = q
    ex = tr - tl
    ey = bl - tl
    pts = np.array(q)
    x0, y0 = np.floor(pts.min(0)).astype(int)
    x1, y1 = np.ceil(pts.max(0)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, img.shape[1]), min(y1, img.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
    m = np.array([[ex[0], ey[0]], [ex[1], ey[1]]], np.float32)
    inv = np.linalg.inv(m)
    dx = xx - tl[0]
    dy = yy - tl[1]
    u = inv[0, 0] * dx + inv[0, 1] * dy
    v = inv[1, 0] * dx + inv[1, 1] * dy
    inside = (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
    if not inside.any():
        return
    n = rgba.shape[0]
    tx = np.clip((u * n).astype(int), 0, n - 1)
    ty = np.clip((v * n).astype(int), 0, n - 1)
    col = rgba[ty, tx, :3].copy()
    a = rgba[ty, tx, 3]
    if tint is not None:
        if isinstance(tint, tuple) and len(tint) == 2:
            t_rgb, t_mask = tint
            tm = t_mask[ty, tx]
            col = np.where(tm[..., None], col * t_rgb, col)
        else:
            col = col * tint
    shade = light
    if ao is not None:
        a_tl, a_tr, a_br, a_bl = ao
        uu = np.clip(u, 0, 1)
        vv = np.clip(v, 0, 1)
        top = a_tl * (1 - uu) + a_tr * uu
        bot = a_bl * (1 - uu) + a_br * uu
        shade = light * (top * (1 - vv) + bot * vv)
    col = col * (shade[..., None] if np.ndim(shade) else shade)
    sel = inside & (a > 0.5)
    region = img[y0:y1, x0:x1]
    region[sel] = col[sel]
    cov[y0:y1, x0:x1][sel] = 1.0
