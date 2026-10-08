"""Tiny orthographic renderer for geometry + texture previews (dev aid, also used for docs images).

Faces are drawn with the painter's algorithm and an exact affine texture mapping
(orthographic projections of rectangles are parallelograms).
"""
import math

import numpy as np
from PIL import Image


def rot_matrix(rx, ry, rz):
    rx, ry, rz = (math.radians(a) for a in (rx, ry, rz))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def cube_faces_3d(cube):
    x0, y0, z0 = cube.origin
    w, h, d = cube.size
    inf = cube.inflate
    x0, y0, z0 = x0 - inf, y0 - inf, z0 - inf
    x1, y1, z1 = x0 + w + 2 * inf, y0 + h + 2 * inf, z0 + d + 2 * inf
    # each face: 4 corners in order (top-left, top-right, bottom-right, bottom-left) as seen from outside
    return {
        'north': [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
        'south': [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
        'east': [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
        'west': [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
        'up': [(x1, y1, z1), (x0, y1, z1), (x0, y1, z0), (x1, y1, z0)],
        'down': [(x1, y0, z0), (x0, y0, z0), (x0, y0, z1), (x1, y0, z1)],
    }


def render(geo, tex, size=360, yaw=-35, pitch=20, scale=None, bg=(46, 44, 54, 255), extra_layers=()):
    texa = np.array(tex) if not isinstance(tex, np.ndarray) else tex
    layers = [texa] + [np.array(l) for l in extra_layers]
    R = rot_matrix(pitch, yaw, 0)
    faces = []
    allpts = []
    for bone, cube in geo.cubes():
        f3 = cube_faces_3d(cube)
        crot = None
        if cube.rotation and cube.pivot:
            crot = (rot_matrix(*cube.rotation), np.array(cube.pivot, dtype=float))
        rects = cube.faces() if cube.face_uv is None else {
            k: (v['uv'][0], v['uv'][1], v['uv_size'][0], v['uv_size'][1]) for k, v in cube.face_uv.items()}
        for name, pts in f3.items():
            P = np.array(pts, dtype=float)
            if crot:
                M, piv = crot
                P = (P - piv) @ M.T + piv
            Q = P @ R.T
            faces.append((name, Q, rects[name]))
            allpts.append(Q)
    allp = np.concatenate(allpts)
    minx, maxx = allp[:, 0].min(), allp[:, 0].max()
    miny, maxy = allp[:, 1].min(), allp[:, 1].max()
    if scale is None:
        scale = 0.85 * size / max(maxx - minx, maxy - miny)
    cxw, cyw = (minx + maxx) / 2, (miny + maxy) / 2
    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[:, :] = bg
    light = {'up': 1.0, 'north': 0.82, 'south': 0.82, 'east': 0.68, 'west': 0.68, 'down': 0.5}

    def to_screen(p):
        return np.array([(p[0] - cxw) * scale + size / 2, size / 2 - (p[1] - cyw) * scale])

    # painter: draw far faces first (camera sits on the -z side looking toward +z)
    faces.sort(key=lambda f: -f[1][:, 2].mean())
    for name, Q, rect in faces:
        # back-face culling: normal z
        a, b, c4 = Q[0], Q[1], Q[3]
        n = np.cross(b - a, c4 - a)
        if n[2] <= 0:
            continue
        s0, s1, s3 = to_screen(Q[0]), to_screen(Q[1]), to_screen(Q[3])
        ex, ey = s1 - s0, s3 - s0   # texture u along ex, v along ey
        det = ex[0] * ey[1] - ex[1] * ey[0]
        if abs(det) < 1e-6:
            continue
        sc = [to_screen(q) for q in Q]
        xs = [p[0] for p in sc]
        ys = [p[1] for p in sc]
        tx, ty, tw, th = rect
        for py in range(max(0, int(min(ys))), min(size, int(max(ys)) + 1)):
            for px in range(max(0, int(min(xs))), min(size, int(max(xs)) + 1)):
                rx, ry = px + 0.5 - s0[0], py + 0.5 - s0[1]
                u = (rx * ey[1] - ry * ey[0]) / det
                v = (ex[0] * ry - ex[1] * rx) / det
                if 0 <= u < 1 and 0 <= v < 1:
                    sx = int(tx + u * tw)
                    sy = int(ty + v * th)
                    for li, L in enumerate(layers):
                        if not (0 <= sy < L.shape[0] and 0 <= sx < L.shape[1]):
                            continue
                        col = L[sy, sx]
                        if col[3] < 20:
                            continue
                        f = light[name] if li == 0 else 1.0
                        rgb = np.clip(col[:3] * f, 0, 255)
                        al = col[3] / 255.0
                        img[py, px, :3] = (img[py, px, :3] * (1 - al) + rgb * al).astype(np.uint8)
                        img[py, px, 3] = 255
    return Image.fromarray(img, 'RGBA')
