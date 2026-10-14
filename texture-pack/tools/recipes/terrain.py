"""Natural terrain: stones, soils, sands, gravel, grass."""
import numpy as np

from engine.noise import (F32, fbm, ridged, worley, cell_random, blur, warped_coords, perlin, grid, norm01,
                          smoothstep, rng)
from engine.color import ramp, mix, vary, match_mean, hexrgb
from engine.material import Tex, MASTER

N = MASTER


# ------------------------------------------------------------------ building blocks
def grains(n, freq, seed, jitter=1.0):
    """Packed rounded grains: returns (dome height 0..1, gap mask 0..1, cell id)."""
    f1, f2, cid = worley(n, freq, seed, jitter)
    edge = f2 - f1
    dome = np.clip(1.0 - (f1 / (f1 + edge + 1e-6)) ** 1.6, 0, 1)
    gap = 1.0 - smoothstep(0.02, 0.12, edge)
    return dome.astype(F32), gap.astype(F32), cid


def crack_field(n, freq, seed, width=0.035, warp=0.04):
    """Thin connected crack network (1 on the crack)."""
    x, y = warped_coords(n, warp, seed + 9, freq=3)
    f1, f2, _ = worley(n, freq, seed, 0.95, x, y)
    return (1.0 - smoothstep(0.0, width, f2 - f1)).astype(F32)


def speckles(n, freq, seed, density=0.12, size=0.35):
    """Sparse mineral flecks: (mask 0..1, value per fleck)."""
    f1, f2, cid = worley(n, freq, seed, 1.0)
    pick = cell_random(cid, seed + 1) < density
    m = (1.0 - smoothstep(size * 0.6, size, f1)) * pick
    return m.astype(F32), cell_random(cid, seed + 2)


# ------------------------------------------------------------------ stones
def fissures(n, seed, freq=3, thresh=0.9, broken=0.45, width=1.0):
    """Long, winding, open-ended fissures (not closed cells): 0..1 on the fissure."""
    x, y = warped_coords(n, 0.08, seed, freq=2)
    r = 1.0 - np.abs(fbm(n, freq, seed + 1, 4, x=x, y=y))
    line = smoothstep(thresh - 0.04 * width, thresh + 0.02, r)
    gate = smoothstep(broken - 0.1, broken + 0.1, 0.5 + 0.5 * fbm(n, 4, seed + 2, 3))
    return (line * gate).astype(F32)


def rock(seed, stops, *, mottling=0.6, cracks=0.7, fleck=None, bump=1.15, strata=0.0, light='top', pits=0.3,
         target=None, ao=0.55, lumps=1.0, crack_freq=3):
    x, y = warped_coords(N, 0.07, seed, freq=3)
    big = fbm(N, 2, seed, 6, x=x, y=y)
    mid = fbm(N, 7, seed + 3, 4, x=x, y=y)
    fine = fbm(N, 28, seed + 4, 3)
    micro = fbm(N, 64, seed + 5, 2)
    h = 0.5 + 0.09 * big * lumps + 0.14 * mid + 0.07 * fine + 0.03 * micro
    t = 0.5 + 0.12 * big * mottling + 0.16 * mid + 0.10 * fine + 0.06 * micro
    if strata:
        band = np.sin((y + 0.05 * big) * 2 * np.pi * 5 + 3 * mid)
        t += strata * 0.08 * band
        h += strata * 0.05 * band
    fis = fissures(N, seed + 11, crack_freq, 0.955, 0.5, 0.6) * cracks
    fis2 = fissures(N, seed + 12, crack_freq * 2, 0.97, 0.6, 0.5) * cracks * 0.7
    h -= 0.16 * fis + 0.08 * fis2
    t -= 0.13 * fis + 0.07 * fis2
    pit = smoothstep(0.62, 0.9, fbm(N, 36, seed + 7, 2)) * pits
    h -= 0.10 * pit
    t -= 0.10 * pit
    albedo = ramp(np.clip(t, 0, 1), stops)
    if fleck:
        for i, (freq, dens, size, col, amt) in enumerate(fleck):
            m, v = speckles(N, freq, seed + 50 + i, dens, size)
            albedo = mix(albedo, hexrgb(col) * (0.85 + 0.3 * v[..., None]), m * amt)
            h = h + 0.04 * m
    albedo = vary(albedo, dh=0.012 * fbm(N, 4, seed + 21, 3), ds=0.18 * fbm(N, 3, seed + 22, 3))
    if target:
        albedo = match_mean(albedo, target)
    return Tex(albedo, norm01(h), light=light, bump=bump, ao=ao)


def stone(seed=1, **kw):
    return rock(seed, [(0.0, '#454547'), (0.3, '#636261'), (0.55, '#7b7976'), (0.8, '#94918c'), (1.0, '#aaa7a1')],
                fleck=[(34, 0.10, 0.3, '#57565a', 0.45), (52, 0.07, 0.3, '#aba8a2', 0.45)], target=0.47, **kw)


# ------------------------------------------------------------------ soils
def dirt(seed=2, light='over', target=0.38, organic=1.0, pebbles=1.0, stops=None):
    x, y = warped_coords(N, 0.09, seed, freq=4)
    base = fbm(N, 3, seed, 6, x=x, y=y)
    crumb_x, crumb_y = warped_coords(N, 0.012, seed + 1, freq=16)
    c1, c2, cid = worley(N, 26, seed + 2, 1.0, crumb_x, crumb_y)
    clump = smoothstep(0.0, 0.35, c2 - c1) * np.clip(1.15 - c1, 0, 1)
    k1, k2, kid = worley(N, 52, seed + 13, 1.0)
    clump = 0.65 * clump + 0.35 * smoothstep(0.0, 0.3, k2 - k1)
    crumbs = fbm(N, 48, seed + 3, 2)
    org = smoothstep(0.0, 0.55, fbm(N, 5, seed + 4, 5)) * organic
    t = 0.5 + 0.14 * base + 0.26 * (clump - 0.45) + 0.10 * crumbs - 0.16 * org
    stops = stops or [(0.0, '#251912'), (0.3, '#3f2c1f'), (0.55, '#56402d'), (0.8, '#6d533b'), (1.0, '#86684b')]
    albedo = ramp(np.clip(t, 0, 1), stops)
    albedo = vary(albedo, dh=0.012 * (cell_random(cid, seed + 5) - 0.5), ds=0.15 * fbm(N, 6, seed + 6, 3))
    h = 0.5 + 0.10 * base + 0.35 * clump + 0.08 * crumbs
    # sparse small pebbles, partly buried
    pf1, pf2, pid = worley(N, 8, seed + 7, 1.0)
    pick = cell_random(pid, seed + 8) < 0.22 * pebbles
    pr = 0.10 + 0.10 * cell_random(pid, seed + 9)
    d = pf1 / (pr + 1e-6)
    peb = (1 - smoothstep(0.75, 1.0, d)) * pick * smoothstep(-0.2, 0.3, fbm(N, 30, seed + 10, 2))
    pcol = ramp(cell_random(pid, seed + 11), [(0, '#463e37'), (0.5, '#5b5249'), (1, '#6c6157')])
    pcol = pcol * (0.85 + 0.2 * np.sqrt(np.clip(1 - d * d, 0, 1)))[..., None]
    albedo = mix(albedo, pcol, peb * 0.75)
    h = h + 0.3 * peb * np.sqrt(np.clip(1 - d * d, 0, 1))
    # fine root fibres
    fib = smoothstep(0.96, 0.99, ridged(N, 9, seed + 12, 3, sharp=3)) * smoothstep(0.0, 0.5, fbm(N, 3, seed + 14, 3) + 0.2)
    albedo = mix(albedo, hexrgb('#8a6f55'), fib * 0.25)
    albedo = match_mean(albedo, target)
    return Tex(albedo, norm01(h), light=light, bump=1.5, ao=0.65, sharpen=0.5)


def sand(seed=3, stops=None, target=0.72, light='over', ripples=0.5):
    stops = stops or [(0.0, '#a4875e'), (0.4, '#c8ad7f'), (0.75, '#dcc597'), (1.0, '#ead6aa')]
    base = fbm(N, 4, seed, 5)
    g = fbm(N, 96, seed + 1, 2)
    dome, gap, cid = grains(N, 64, seed + 2)
    col_rand = cell_random(cid, seed + 3)
    rip = fbm(N, 6, seed + 4, 3, stretch=(1, 2)) * ripples
    t = 0.55 + 0.08 * base + 0.14 * g + 0.12 * (col_rand - 0.5) + 0.06 * rip
    albedo = ramp(np.clip(t, 0, 1), stops)
    dark = (col_rand > 0.93) * (1 - gap)
    albedo = mix(albedo, albedo * np.array([0.55, 0.5, 0.48], F32), dark * 0.7)
    light_g = (col_rand < 0.04) * (1 - gap)
    albedo = mix(albedo, np.array([0.97, 0.95, 0.9], F32), light_g * 0.5)
    h = 0.5 + 0.22 * dome + 0.12 * rip + 0.05 * base
    albedo = match_mean(albedo, target)
    return Tex(albedo, norm01(h), light=light, bump=0.6, ao=0.3)


def gravel(seed=4, target=0.47, light='over'):
    albedo = np.zeros((N, N, 3), F32)
    h = np.zeros((N, N), F32)
    # fines
    fines = fbm(N, 64, seed, 2)
    albedo[:] = ramp(0.5 + 0.3 * fines, [(0, '#4a453f'), (1, '#77706a')])
    h[:] = 0.2 + 0.05 * fines
    for layer, (freq, cover, lo, hi) in enumerate(((6, 0.97, 0.55, 1.0), (11, 0.95, 0.4, 0.85), (20, 0.9, 0.25, 0.6), (38, 0.85, 0.15, 0.4))):
        f1, f2, cid = worley(N, freq, seed + 10 * layer, 0.85)
        r = cell_random(cid, seed + 10 * layer + 1)
        keep = r < cover
        radius = 0.46 + 0.14 * cell_random(cid, seed + 10 * layer + 2)
        x, y = grid(N)
        d = f1 / radius
        stone_mask = (1 - smoothstep(0.85, 1.0, d)) * keep
        dome = np.sqrt(np.clip(1 - d * d, 0, 1))
        hue = cell_random(cid, seed + 10 * layer + 3)
        col = ramp(hue, [(0, '#5e5a56'), (0.3, '#7d7872'), (0.55, '#8e8579'), (0.75, '#958479'), (0.9, '#6f6a73'), (1.0, '#a39d94')])
        tex = fbm(N, 48, seed + 10 * layer + 4, 2)
        col = col * (0.78 + 0.28 * dome[..., None] + 0.08 * tex[..., None])
        z = lo + (hi - lo) * dome
        top = (z > h) & (stone_mask > 0.5)
        albedo = np.where(top[..., None], col, albedo)
        h = np.where(top, z, h)
    albedo = vary(albedo, ds=0.15 * fbm(N, 5, seed + 9, 3))
    albedo = match_mean(albedo, target)
    return Tex(albedo, blur(h, 0.6), light=light, bump=2.2, ao=0.75)


def stone_field(seed, freq, x, y, roundness=0.5, gap=0.16):
    """Irregular rounded stones from warped Voronoi: (height 0..1, mask 0..1, cell id)."""
    f1, f2, cid = worley(N, freq, seed, 0.85, x, y)
    edge = f2 - f1
    poly = smoothstep(gap * 0.4, gap * 0.4 + 0.35, edge)
    circ = np.clip(1.0 - f1 / 0.62, 0, 1)
    shape = (1 - roundness) * poly + roundness * np.minimum(poly, smoothstep(0, 0.6, circ))
    mask = smoothstep(0.02, 0.12, shape)
    dome = np.sqrt(np.clip(shape, 0, 1))
    return dome.astype(F32), mask.astype(F32), cid


def cobblestone(seed=5, target=0.47, mossy=0.0, stops=None):
    x, y = warped_coords(N, 0.045, seed, freq=4)
    dome_b, mask_b, cid_b = stone_field(seed + 1, 4, x, y, 0.45, 0.18)
    x2, y2 = warped_coords(N, 0.03, seed + 20, freq=6)
    dome_s, mask_s, cid_s = stone_field(seed + 2, 9, x2, y2, 0.6, 0.2)
    small = mask_s * (1 - mask_b)
    stops = stops or [(0, '#4b4a49'), (0.35, '#666462'), (0.65, '#807d79'), (1, '#9c9892')]
    surf = fbm(N, 22, seed + 3, 4)
    tone_b = cell_random(cid_b, seed + 4)
    tone_s = cell_random(cid_s, seed + 5)
    col_b = ramp(np.clip(0.2 + 0.55 * tone_b + 0.15 * surf + 0.15 * dome_b, 0, 1), stops)
    col_b = vary(col_b, dh=0.03 * (cell_random(cid_b, seed + 6) - 0.5), ds=0.5 * (cell_random(cid_b, seed + 7) - 0.4))
    col_s = ramp(np.clip(0.15 + 0.5 * tone_s + 0.15 * surf + 0.1 * dome_s, 0, 1), stops)
    joint = ramp(0.5 + 0.35 * fbm(N, 26, seed + 8, 3), [(0, '#3a342e'), (0.6, '#4b443c'), (1, '#615749')])
    albedo = mix(joint, col_s, small)
    albedo = mix(albedo, col_b, mask_b)
    h = 0.15 + 0.08 * fbm(N, 30, seed + 9, 2)
    h = np.maximum(h, 0.25 + 0.45 * dome_s * small)
    h = np.where(mask_b > 0.05, np.maximum(h, 0.3 + 0.7 * dome_b * mask_b), h)
    h = h + 0.05 * surf * (mask_b + small)
    cr = fissures(N, seed + 10, 6, 0.95, 0.5) * mask_b
    albedo = mix(albedo, albedo * 0.62, cr * 0.7)
    h -= 0.12 * cr
    if mossy:
        moss_m = smoothstep(0.2, 0.6, fbm(N, 4, seed + 11, 5) + 0.7 * (1 - mask_b) - 0.35 + mossy * 0.35)
        moss_col = ramp(0.5 + 0.45 * fbm(N, 44, seed + 12, 3), [(0, '#344420'), (0.6, '#55692c'), (1, '#77873b')])
        albedo = mix(albedo, moss_col, moss_m * mossy)
        h = h + 0.06 * moss_m
    albedo = match_mean(albedo, target)
    return Tex(albedo, norm01(h), light='top', bump=1.5, ao=0.65)


# ------------------------------------------------------------------ grass (tinted greyscale)
def blades_field(n, seed, count, length, width, angle_spread=np.pi, bright=(0.45, 1.0), base_y=None,
                 upright=False, curve=0.25):
    """Rasterise grass blades into (luminance, coverage, height). Blades wrap around edges.

    Top view: blades point in random directions. Upright (side view): blades grow upward from base_y.
    """
    r = rng(seed)
    lum = np.zeros((n, n), F32)
    cov = np.zeros((n, n), F32)
    hgt = np.zeros((n, n), F32)
    yy, xx = np.mgrid[0:n, 0:n].astype(F32)
    for i in range(count):
        x0, y0 = r.uniform(0, n), (r.uniform(0, n) if base_y is None else base_y + r.uniform(-n * 0.03, n * 0.03))
        if upright:
            ang = -np.pi / 2 + r.uniform(-angle_spread, angle_spread)
        else:
            ang = r.uniform(0, 2 * np.pi)
        L = length * r.uniform(0.55, 1.25) * n
        w = width * r.uniform(0.6, 1.3) * n
        bend = r.uniform(-curve, curve)
        b = r.uniform(*bright)
        steps = max(4, int(L / 1.5))
        for s in range(steps):
            t = s / steps
            a = ang + bend * t * 2
            px = x0 + np.cos(a) * L * t
            py = y0 + np.sin(a) * L * t
            rad = max(0.6, w * (1 - t) ** 0.8 * 0.5)
            x_lo, x_hi = int(px - rad - 1), int(px + rad + 2)
            y_lo, y_hi = int(py - rad - 1), int(py + rad + 2)
            ys = np.arange(y_lo, y_hi) % n
            xs = np.arange(x_lo, x_hi) % n
            gx = np.arange(x_lo, x_hi)[None, :] - px
            gy = np.arange(y_lo, y_hi)[:, None] - py
            d = np.sqrt(gx * gx + gy * gy)
            m = np.clip(rad + 0.5 - d, 0, 1)
            z = (0.3 + 0.7 * t) if not upright else t
            sub_l = lum[np.ix_(ys, xs)]
            sub_c = cov[np.ix_(ys, xs)]
            sub_h = hgt[np.ix_(ys, xs)]
            shade = b * (0.75 + 0.25 * t)
            take = m * (z >= sub_h - 0.05)
            lum[np.ix_(ys, xs)] = sub_l * (1 - take) + shade * take
            hgt[np.ix_(ys, xs)] = np.maximum(sub_h, z * m)
            cov[np.ix_(ys, xs)] = np.maximum(sub_c, m)
    return lum, cov, hgt


def grass_top(seed=6, target=0.578):
    soil = 0.12 + 0.06 * fbm(N, 16, seed, 3)
    lum0, cov0, h0 = blades_field(N, seed + 1, 420, 0.075, 0.03, bright=(0.30, 0.55))
    lum1, cov1, h1 = blades_field(N, seed + 2, 380, 0.10, 0.04, bright=(0.50, 0.85))
    lum2, cov2, h2 = blades_field(N, seed + 3, 240, 0.12, 0.045, bright=(0.70, 1.0))
    lum = soil * (1 - cov0) + lum0 * cov0
    lum = lum * (1 - cov1) + lum1 * cov1
    lum = lum * (1 - cov2) + lum2 * cov2
    h = np.maximum(np.maximum(h0 * 0.5, h1 * 0.75), h2)
    mott = fbm(N, 3, seed + 4, 4)
    lum = lum * (0.86 + 0.18 * mott)
    rgb = np.dstack([lum * (1 + 0.05 * mott), lum, lum * (1 - 0.04 * mott)])
    rgb = match_mean(rgb, target)
    return Tex(rgb, blur(h, 0.8), light='over', bump=1.1, ao=0.7)




# ------------------------------------------------------------------ side overhangs (grass, snow, mycelium…)
from engine.draw import polyline, bezier, capsules, scatter  # noqa: E402

XS = (np.arange(N, dtype=F32) + 0.5) / N


def noise_x(seed, freq, octaves=3):
    """Periodic 1-D noise along x (one value per column), roughly [-1, 1]."""
    z = np.zeros_like(XS)
    total, amp, norm = np.zeros_like(XS), 1.0, 0.0
    for o in range(octaves):
        total += amp * perlin(N, (freq * 2 ** o, 1), seed + 17 * o, XS, z)
        norm += amp
        amp *= 0.5
    return total / norm


def hang_edge(seed, depth, wave=0.03, lobes=7, lobe_depth=(0.03, 0.09), lobe_width=(0.03, 0.08)):
    """Lower boundary of a layer seen from the side, per column, in texture units from the top."""
    e = depth + wave * noise_x(seed, 4)
    r = rng(seed + 1)
    for _ in range(lobes):
        cx, w, dp = r.uniform(0, 1), r.uniform(*lobe_width), r.uniform(*lobe_depth)
        dx = np.abs(XS - cx)
        dx = np.minimum(dx, 1 - dx)
        e = np.maximum(e, depth + dp * np.clip(1 - (dx / w) ** 2, 0, 1) ** 0.7)
    return e.astype(F32)


def hanging(seed, edge, count, length=(0.6, 2.4), width=(0.32, 0.6), sway=0.7):
    """Tapered strands hanging below an edge (block units). Returns (mask, shade 0..1)."""
    r = rng(seed)
    m = np.zeros((N, N), F32)
    shade = np.zeros((N, N), F32)
    for _ in range(count):
        cx = r.uniform(0, 16)
        top = float(edge[int(cx / 16 * N) % N]) * 16 - 0.5
        L = r.uniform(*length)
        s = r.uniform(-sway, sway)
        pts = bezier((cx, top), (cx + 0.25 * s, top + 0.35 * L), (cx + 0.7 * s, top + 0.7 * L), (cx + s, top + L), 8)
        mm, along = polyline(pts, np.linspace(r.uniform(*width), 0.08, 8), wrap=True)
        b = r.uniform(0.5, 0.95)
        upd = mm > m
        shade = np.where(upd, b * (1 - 0.4 * along), shade)
        m = np.maximum(m, mm)
    return m, shade


def turf_side(seed, depth=0.21, strands=44):
    """Grey (tintable) turf seen from the side: (luminance full tile, layer mask, mask, height, edge)."""
    x, y = grid(N)
    edge = hang_edge(seed, depth)
    E = edge[None, :]
    sm, sshade = hanging(seed + 2, edge, strands)
    layer = y < E
    mask = layer | (sm > 0.5)
    bl, bc, bh = blades_field(N, seed + 5, 560, 0.085, 0.022, angle_spread=0.3, bright=(0.45, 1.0),
                              upright=True, curve=0.18)
    thatch = 0.36 + 0.2 * fbm(N, 24, seed + 4, 3)
    lum = thatch * (1 - bc) + bl * bc
    rel = np.clip((E - y) / np.maximum(E, 1e-3), 0, 1)
    lum = lum * (0.56 + 0.44 * rel ** 0.5)
    lum = np.where(layer, lum, np.where(sm > 0.02, sshade * 0.8, 0.4))
    h = np.where(mask, 0.78 + 0.12 * lum + 0.08 * bh * layer, 0.0)
    return lum.astype(F32), layer, mask, h.astype(F32), edge


def soil_under(d, mask, layer_edge, seed, humus=0.30, rootlets=0.45, shadow=0.25):
    """Darken the soil just under an overhang (humus, contact shadow) and add pale rootlets."""
    x, y = grid(N)
    below = np.clip(y - layer_edge[None, :], 0, 1)
    under = below > 0
    hum = np.exp(-below / 0.05) * under
    sh = np.clip(blur(mask.astype(F32), 2.5) * 1.5, 0, 1) * (y < 0.75)
    rgb = d.albedo * (1 - humus * hum[..., None]) * (1 - shadow * sh[..., None])
    roots = smoothstep(0.93, 0.985, ridged(N, 10, seed + 9, 3, sharp=3, stretch=(3, 1)))
    roots = roots * np.exp(-below / 0.12) * under
    rgb = mix(rgb, hexrgb('#9b8466') * 0.9, roots * rootlets)
    return rgb.astype(F32)


def grass_side(seed=7, depth=0.21):
    d = dirt(seed + 1, light='top', target=0.36)
    lum, layer, mask, h, edge = turf_side(seed, depth)
    mott = fbm(N, 3, seed + 6, 3)
    grass = np.dstack([lum * (1 + 0.04 * mott), lum, lum * (1 - 0.03 * mott)])
    grass = match_mean(grass, 0.56, mask)
    soil = soil_under(d, mask, edge, seed)
    height = np.where(mask, h, d.height * 0.6)
    return Tex(soil, height, light='top', bump=1.0, ao=0.55, tint_mask=mask, tint_albedo=grass, sharpen=0.45)


# ------------------------------------------------------------------ snow and ice
def snow_albedo(seed, fine=1.0):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    drift = fbm(N, 3, seed, 5, x=x, y=y)
    sculpt = fbm(N, 9, seed + 1, 4)
    grain = fbm(N, 80, seed + 2, 2) * fine
    h = 0.5 + 0.3 * drift + 0.06 * sculpt + 0.03 * grain
    t = 0.82 + 0.05 * drift + 0.04 * sculpt + 0.05 * grain
    alb = ramp(np.clip(t, 0, 1), [(0.6, '#dfe6ef'), (0.8, '#eef2f6'), (0.92, '#f8f9fb'), (1.0, '#ffffff')])
    return alb, norm01(h)


def sparkle(seed, density=0.05, strength=0.45, freq=70):
    m, v = speckles(N, freq, seed, density, 0.22)
    return (m * strength * (0.6 + 0.4 * v))[..., None] * np.array([0.95, 0.98, 1.0], F32)


def snow(seed=40, target=0.9):
    alb, h = snow_albedo(seed)
    alb = match_mean(alb, target)
    return Tex(alb, h, light='over', bump=0.45, ao=0.15, emissive=sparkle(seed + 9))


def powder_snow(seed=41, target=0.93):
    alb, h = snow_albedo(seed, fine=1.6)
    puff = fbm(N, 20, seed + 5, 3)
    h = norm01(h + 0.35 * puff)
    alb = match_mean(alb * (0.97 + 0.05 * puff[..., None]), target)
    return Tex(alb, h, light='over', bump=0.4, ao=0.15, emissive=sparkle(seed + 9, 0.09, 0.5, 90))


def snow_cap_side(seed, under_rgb, under_h, depth=0.19):
    """A snow layer draped over the top edge of a side face (untinted)."""
    x, y = grid(N)
    edge = hang_edge(seed, depth, wave=0.02, lobes=6, lobe_depth=(0.02, 0.07), lobe_width=(0.05, 0.12))
    E = edge[None, :]
    layer = y < E
    alb, sh = snow_albedo(seed + 3)
    lip = smoothstep(0.0, 0.06, E - y)
    alb = alb * (0.74 + 0.26 * lip)[..., None] * np.array([0.97, 0.99, 1.03], F32)
    sh_cast = np.clip(blur(layer.astype(F32), 2.0) * 1.4, 0, 1) * (~layer) * (y < 0.75)
    rgb = np.where(layer[..., None], alb, under_rgb * (1 - 0.3 * sh_cast[..., None]))
    h = np.where(layer, 0.82 + 0.15 * sh * lip, under_h * 0.6)
    return rgb.astype(F32), h.astype(F32), layer


def grass_side_snowed(seed=44):
    d = dirt(seed + 1, light='top', target=0.36)
    lum, layer, mask, h, edge = turf_side(seed, 0.27, strands=30)
    frost = ramp(np.clip(lum, 0, 1), [(0, '#3d3a26'), (0.5, '#6a6a48'), (1, '#8f9070')])
    soil = soil_under(d, mask, edge, seed)
    under = np.where(mask[..., None], frost, soil)
    under_h = np.where(mask, h, d.height * 0.6)
    under = match_mean(under, 0.4)
    rgb, height, _ = snow_cap_side(seed + 5, under, under_h)
    return Tex(rgb, height, light='top', bump=1.0, ao=0.5, tint_mask=np.zeros((N, N), bool), sharpen=0.45)


def ice(seed=50, kind='clear', melt=0):
    """kind: 'clear' (translucent), 'packed' or 'blue' (opaque). melt 0..3 for frosted ice.

    Depth comes from a faint deep/shallow cloud, a few long fracture planes that catch the light on
    one side, and sparse streaks of trapped air. Large-scale contrast stays low so blocks don't
    visibly repeat.
    """
    from engine.draw import fractures
    x, y = warped_coords(N, 0.05, seed, freq=3)
    depth = fbm(N, 2, seed, 5, x=x, y=y)
    cloud = fbm(N, 7, seed + 1, 4, x=x, y=y)
    n_major = {'clear': 3, 'packed': 4, 'blue': 3}[kind]
    major, sheet = fractures(seed + 2, n_major, (7, 15), (0.1, 0.22), jag=1.0)
    minor, msheet = fractures(seed + 3, 3 + 2 * melt + (4 if kind == 'packed' else 0), (2, 6), (0.06, 0.12),
                              kinks=3, plane=0.5)
    bub_m, bub_v = speckles(N, 48, seed + 4, 0.07, 0.28)
    streak = smoothstep(0.3, 0.75, fbm(N, (2, 6), seed + 5, 3))
    frost = smoothstep(0.86, 0.97, ridged(N, 10, seed + 6, 3, sharp=3))
    if kind == 'blue':
        stops = [(0, '#1a469f'), (0.45, '#2c64c6'), (0.8, '#4a86dc'), (1, '#7eaeee')]
        t = 0.55 + 0.1 * depth + 0.05 * cloud
        bubbles, frost_amt, line_col = 0.2 * bub_m * streak, 0.08, hexrgb('#c9e0fc')
    elif kind == 'packed':
        stops = [(0, '#86a5da'), (0.5, '#abc5ed'), (0.8, '#cddcf6'), (1, '#edf3fd')]
        t = 0.55 + 0.1 * depth + 0.08 * cloud + 0.05 * fbm(N, 16, seed + 7, 3)
        b2, _ = speckles(N, 80, seed + 10, 0.12, 0.3)
        bubbles = np.clip(0.8 * bub_m + 0.6 * b2, 0, 1) * (0.35 + 0.65 * streak)
        frost_amt, line_col = 0.3, hexrgb('#f5f9ff')
    else:
        stops = [(0, '#76a0e2'), (0.5, '#a0c0f0'), (0.85, '#c9dcf8'), (1, '#f0f6fe')]
        t = 0.55 + 0.12 * depth + 0.08 * cloud
        bubbles, frost_amt, line_col = 0.5 * bub_m * streak, 0.22, hexrgb('#f2f7ff')
    alb = ramp(np.clip(t, 0, 1), stops)
    glow = np.clip(0.6 * sheet + 0.3 * msheet, 0, 1)
    alb = mix(alb, line_col, glow * 0.5)
    milky = smoothstep(0.2, 0.7, fbm(N, 4, seed + 9, 4)) * (0.35 if kind == 'packed' else 0.15)
    alb = mix(alb, np.array([0.93, 0.95, 0.99], F32), milky)
    lines = np.clip(major + 0.7 * minor, 0, 1)
    alb = mix(alb, line_col, lines * 0.85)
    alb = mix(alb, np.array([0.96, 0.98, 1.0], F32), np.clip(bubbles, 0, 1))
    alb = mix(alb, np.array([0.9, 0.94, 1.0], F32), frost * frost_amt)
    h = 0.5 + 0.05 * depth + 0.02 * frost          # fractures are inside the ice: no surface relief
    alpha = None
    if kind == 'clear':
        alpha = np.clip(0.68 + 0.25 * lines + 0.12 * glow + 0.15 * bubbles + 0.05 * frost, 0, 0.96)
        if melt:
            pits = smoothstep(0.66, 0.82, 0.5 + 0.5 * fbm(N, 9, seed + 8 + melt, 3)) * melt / 3
            alb = alb * (1 - 0.15 * pits[..., None])
            alpha = np.clip(alpha - 0.18 * pits, 0.45, 0.97)
            h = h - 0.1 * pits
    target = {'clear': 0.72, 'packed': 0.7, 'blue': 0.45}[kind]
    alb = match_mean(alb, target)
    return Tex(alb, norm01(h), alpha, light='top', bump=0.5, ao=0.2, gloss=0.25)


# ------------------------------------------------------------------ clay, mud, moss
def clay(seed=60, target=0.62):
    x, y = warped_coords(N, 0.06, seed, freq=3)
    lumps = fbm(N, 5, seed, 4, x=x, y=y)
    smear = fbm(N, (3, 9), seed + 1, 3, x=x, y=y)
    silt = fbm(N, 40, seed + 2, 3)
    pores = smoothstep(0.72, 0.9, fbm(N, 50, seed + 3, 2))
    t = 0.55 + 0.1 * lumps + 0.04 * smear + 0.05 * silt
    alb = ramp(np.clip(t, 0, 1), [(0, '#727a86'), (0.4, '#9097a3'), (0.7, '#a7aeb9'), (1, '#c1c6ce')])
    grit, gv = speckles(N, 22, seed + 4, 0.08, 0.3)
    alb = mix(alb, ramp(gv, [(0, '#7d7a74'), (1, '#b3aea2')]), grit * 0.6)
    alb = alb * (1 - 0.12 * pores[..., None])
    h = 0.5 + 0.25 * lumps + 0.06 * smear + 0.05 * silt - 0.05 * pores + 0.1 * grit
    return Tex(match_mean(alb, target), norm01(h), light='over', bump=0.7, ao=0.4)


def mud(seed=62, target=0.24):
    x, y = warped_coords(N, 0.08, seed, freq=3)
    slab = fbm(N, 4, seed, 5, x=x, y=y)
    ooze = fbm(N, 12, seed + 1, 3, x=x, y=y)
    dimple = smoothstep(0.25, 0.6, fbm(N, 7, seed + 2, 3))
    t = 0.5 + 0.15 * slab + 0.1 * ooze
    alb = ramp(np.clip(t, 0, 1), [(0, '#211d1c'), (0.5, '#3a3433'), (1, '#55504c')])
    puddle = smoothstep(0.35, 0.55, -slab)
    alb = mix(alb, alb * 0.75, puddle)
    h = 0.5 + 0.3 * slab + 0.12 * ooze - 0.15 * dimple
    h = np.where(puddle > 0.5, np.minimum(h, 0.5 + 0.3 * -0.45), h)
    return Tex(match_mean(alb, target), norm01(blur(h, 1.0)), light='over', bump=0.9, ao=0.4, gloss=0.22)


def packed_mud(seed=63, target=0.44, straw=0.9):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    base = fbm(N, 4, seed, 5, x=x, y=y)
    grit = fbm(N, 48, seed + 1, 2)
    t = 0.55 + 0.14 * base + 0.08 * grit
    alb = ramp(np.clip(t, 0, 1), [(0, '#6b4c35'), (0.5, '#8e6a4d'), (1, '#ad8a69')])
    segs, owner = scatter(seed + 2, 190, (0.8, 2.8), (0.12, 0.22), curve=0.15, parts=2, taper=0.2)
    tone = rng(seed + 3).uniform(0.0, 1.0, owner.max() + 1)[owner]
    cols = ramp(tone, [(0, '#a3874e'), (0.6, '#c9ad6c'), (1, '#e0c98c')])
    straw_rgb, cov, _ = capsules(segs, cols)
    alb = mix(alb, straw_rgb, cov * straw)
    cracks = fissures(N, seed + 4, 5, 0.975, 0.6, 0.6)
    alb = alb * (1 - 0.22 * cracks[..., None])
    h = 0.5 + 0.2 * base + 0.06 * grit + 0.12 * cov - 0.2 * cracks
    return Tex(match_mean(alb, target), norm01(h), light='over', bump=1.0, ao=0.55)


def moss(seed=64, stops=None, target=0.38, light='over'):
    """A velvety carpet of tiny shoots: three layers of short fibres, brighter at the tips."""
    from engine.draw import fibres
    stops = stops or [(0, '#17200b'), (0.35, '#34481a'), (0.7, '#5a7629'), (1, '#8aa63f')]
    base = fbm(N, 4, seed, 5)
    lum = 0.12 + 0.06 * fbm(N, 30, seed + 1, 3)
    hgt = np.zeros((N, N), F32)
    for k, (count, ln, lo, hi) in enumerate(((1800, (0.35, 0.7), 0.25, 0.55), (1500, (0.4, 0.8), 0.4, 0.8),
                                              (900, (0.4, 0.9), 0.55, 1.0))):
        l, c, z = fibres(seed + 10 * k, count, ln, (0.10, 0.17), lo, hi, parts=2, curve=0.6, z0=k)
        lum = lum * (1 - c) + l * c
        hgt = np.maximum(hgt, z * c / 3.0)
    lum = lum * (0.85 + 0.25 * base)
    alb = ramp(np.clip(lum, 0, 1), stops)
    alb = vary(alb, dh=0.015 * fbm(N, 6, seed + 3, 3), ds=0.12 * base)
    h = 0.4 * hgt + 0.25 * base
    return Tex(match_mean(alb, target), norm01(blur(h, 0.6)), light=light, bump=1.1, ao=0.65, sharpen=0.4)


# ------------------------------------------------------------------ soils
def coarse_dirt(seed=70, target=0.35):
    d = dirt(seed, organic=0.4, target=0.33, pebbles=0.0)
    alb, h = d.albedo.copy(), d.height * 0.5
    for k, (freq, keep, rad) in enumerate(((10, 0.35, 0.42), (17, 0.45, 0.4), (30, 0.5, 0.38))):
        f1, f2, cid = worley(N, freq, seed + 3 + k, 0.9)
        pick = cell_random(cid, seed + 10 + k) < keep
        r = rad * (0.7 + 0.5 * cell_random(cid, seed + 20 + k))
        dd = f1 / r
        m = (1 - smoothstep(0.8, 1.0, dd)) * pick
        dome = np.sqrt(np.clip(1 - dd * dd, 0, 1))
        col = ramp(cell_random(cid, seed + 30 + k), [(0, '#4b4239'), (0.4, '#665a4c'), (0.75, '#7b6e5f'),
                                                      (1, '#8f8577')])
        col = col * (0.8 + 0.3 * dome[..., None])
        z = 0.35 + 0.4 * dome
        top = (z > h) & (m > 0.5)
        alb = np.where(top[..., None], col, alb)
        h = np.where(top, z, h)
    return Tex(match_mean(alb, target), norm01(blur(h, 0.5)), light='over', bump=1.6, ao=0.7, sharpen=0.5)


def rooted_dirt(seed=72, target=0.42):
    d = dirt(seed, organic=0.6, target=0.42, stops=[(0.0, '#2e2016'), (0.3, '#4b3524'), (0.55, '#674b33'),
                                                     (0.8, '#82623f'), (1.0, '#9c7a52')])
    vis = smoothstep(-0.1, 0.35, fbm(N, 5, seed + 4, 3))
    fsegs, _ = scatter(seed + 3, 150, (1.0, 3.0), (0.14, 0.22), curve=0.7, parts=4, taper=0.6)
    fine, fcov, _ = capsules(fsegs, np.tile(hexrgb('#c4a57c'), (len(fsegs), 1)))
    segs, owner = scatter(seed + 1, 10, (5.0, 10.0), (0.45, 0.8), curve=0.35, parts=8, taper=0.7)
    tone = rng(seed + 2).uniform(0, 1, owner.max() + 1)[owner]
    roots, cov, _ = capsules(segs, ramp(tone, [(0, '#a0805a'), (0.5, '#bf9f74'), (1, '#d6ba8e')]))
    cov = cov * (0.55 + 0.45 * vis)
    alb = mix(d.albedo, fine, fcov * (0.35 + 0.4 * vis))
    alb = mix(alb, roots * (0.85 + 0.25 * blur(cov, 1.2))[..., None], cov)
    h = d.height * 0.7 + 0.35 * blur(cov, 1.5) + 0.1 * fcov
    return Tex(match_mean(alb, target), norm01(h), light='over', bump=1.3, ao=0.6, sharpen=0.5)


def needles_litter(seed, count=900, palette=None):
    palette = palette or [(0, '#2a1a10'), (0.35, '#412818'), (0.7, '#5a3a22'), (0.92, '#6e4c2e'), (1, '#6f655a')]
    segs, owner = scatter(seed, count, (0.6, 1.8), (0.09, 0.14), curve=0.08, parts=1, taper=0.0)
    tone = rng(seed + 1).uniform(0, 1, owner.max() + 1)[owner]
    return capsules(segs, ramp(tone, palette))


def podzol_top(seed=74, target=0.27):
    base = fbm(N, 4, seed, 5)
    alb = ramp(np.clip(0.5 + 0.2 * base + 0.1 * fbm(N, 30, seed + 1, 3), 0, 1),
               [(0, '#22160c'), (0.5, '#382415'), (1, '#4d331d')])
    nv, ncov, nz = needles_litter(seed + 2, 1100)
    alb = mix(alb, nv, ncov)
    tsegs, _ = scatter(seed + 3, 10, (2.0, 4.5), (0.25, 0.4), curve=0.25, parts=4, taper=0.4)
    tw, tcov, tz = capsules(tsegs, np.tile(hexrgb('#5b4128'), (len(tsegs), 1)))
    alb = mix(alb, tw * (0.8 + 0.3 * fbm(N, 40, seed + 4, 2))[..., None], tcov)
    h = 0.3 + 0.1 * base + 0.35 * ncov * (0.5 + 0.5 * nz.clip(0, 1)) + 0.5 * tcov
    return Tex(match_mean(alb, target), norm01(blur(h, 0.5)), light='over', bump=1.3, ao=0.7)


def mycelium_top(seed=76, target=0.4):
    from engine.draw import fibres
    base = fbm(N, 4, seed, 5)
    lum = 0.3 + 0.1 * fbm(N, 24, seed + 1, 3)
    hgt = np.zeros((N, N), F32)
    for k, (count, lo, hi) in enumerate(((1400, 0.3, 0.6), (900, 0.45, 0.85))):
        l, c, z = fibres(seed + 5 + k, count, (0.3, 0.8), (0.07, 0.12), lo, hi, parts=2, curve=0.9, z0=k)
        lum = lum * (1 - 0.8 * c) + l * 0.8 * c
        hgt = np.maximum(hgt, z * c / 2)
    lum = lum * (0.85 + 0.25 * base)
    alb = ramp(np.clip(lum, 0, 1), [(0, '#3a2f3d'), (0.4, '#5d4f5f'), (0.75, '#7f727e'), (1, '#a4979f')])
    dots, dv = speckles(N, 30, seed + 3, 0.08, 0.32)
    alb = mix(alb, hexrgb('#ded3d3'), dots * 0.6)
    h = 0.3 * hgt + 0.2 * base + 0.15 * dots
    return Tex(match_mean(alb, target), norm01(blur(h, 0.5)), light='over', bump=0.9, ao=0.5)


def layer_side(seed, top_tex, under_tex, depth, strands=0, strand_rgb=None, target=None, lobes=7,
               lobe_depth=(0.03, 0.09)):
    """Untinted top layer (podzol, mycelium, nylium…) seen from the side over a soil."""
    x, y = grid(N)
    edge = hang_edge(seed, depth, lobes=lobes, lobe_depth=lobe_depth)
    E = edge[None, :]
    layer = y < E
    mask = layer.copy()
    sm = np.zeros((N, N), F32)
    if strands:
        sm, sshade = hanging(seed + 2, edge, strands)
        mask = layer | (sm > 0.5)
    rel = np.clip((E - y) / np.maximum(E, 1e-3), 0, 1)
    top_rgb = top_tex.albedo * (0.7 + 0.3 * rel ** 0.5)[..., None]
    if strands:
        top_rgb = np.where(layer[..., None], top_rgb, strand_rgb * (0.6 + 0.4 * sshade[..., None]))
    soil = soil_under(under_tex, mask, edge, seed)
    rgb = np.where(mask[..., None], top_rgb, soil)
    h = np.where(mask, 0.75 + 0.2 * top_tex.height, under_tex.height * 0.6)
    if target:
        rgb = match_mean(rgb, target)
    return Tex(rgb, h, light='top', bump=1.0, ao=0.55, sharpen=0.45)


def path_top(seed=78, target=0.47):
    x, y = warped_coords(N, 0.06, seed, freq=3)
    base = fbm(N, 4, seed, 5, x=x, y=y)
    dust = smoothstep(0.1, 0.5, fbm(N, 6, seed + 1, 4))
    grit_h, grit_gap, gid = grains(N, 34, seed + 2, 1.0)
    t = 0.5 + 0.14 * base + 0.08 * grit_h + 0.1 * dust
    alb = ramp(np.clip(t, 0, 1), [(0, '#5a4128'), (0.4, '#7b5c38'), (0.75, '#98774d'), (1, '#b59468')])
    pm, pv = speckles(N, 18, seed + 3, 0.18, 0.3)
    alb = mix(alb, ramp(pv, [(0, '#6d655c'), (1, '#9b9286')]), pm * 0.8)
    segs, owner = scatter(seed + 4, 40, (0.5, 1.2), (0.1, 0.15), curve=0.3, parts=2)
    gv, gcov, _ = capsules(segs, np.tile(hexrgb('#7c7a3a'), (len(segs), 1)))
    alb = mix(alb, gv, gcov * 0.6)
    h = 0.5 + 0.08 * base + 0.06 * grit_h + 0.2 * pm
    return Tex(match_mean(alb, target), norm01(h), light='over', bump=0.8, ao=0.5)


def path_side(seed=79):
    d = dirt(seed + 1, light='top', target=0.38)
    pt = path_top(seed + 2)
    x, y = grid(N)
    edge = hang_edge(seed, 0.2, wave=0.02, lobes=4, lobe_depth=(0.02, 0.05))
    E = edge[None, :]
    band = (y < E)
    soil = soil_under(d, band, edge, seed, humus=0.15, rootlets=0.25, shadow=0.1)
    rgb = np.where(band[..., None], pt.albedo * 0.92, soil)
    h = np.where(band, 0.7 + 0.2 * pt.height, d.height * 0.6)
    alpha = (y >= 1 / 16).astype(F32)
    return Tex(match_mean(rgb, 0.42), h, alpha, light='top', bump=1.0, ao=0.5, cutout=True, sharpen=0.45)


def farmland(seed=80, wet=False):
    x, y = grid(N)
    meander = 0.025 * fbm(N, 3, seed, 3) + 0.01 * fbm(N, 9, seed + 1, 2)
    phase = (y + meander) * 4
    ridge = 0.5 + 0.5 * np.cos(2 * np.pi * phase)
    wx, wy = warped_coords(N, 0.02, seed + 2, freq=8)
    f1, f2, cid = worley(N, 24, seed + 3, 1.0, wx, wy)
    clod = np.clip(1 - f1 / 0.75, 0, 1) ** 0.7 * smoothstep(0.0, 0.25, f2 - f1)
    g1, g2, gid = worley(N, 44, seed + 4, 1.0)
    crumb = np.clip(1 - g1 / 0.7, 0, 1) * smoothstep(0.0, 0.2, g2 - g1)
    base = fbm(N, 5, seed + 5, 4)
    on_ridge = smoothstep(0.25, 0.8, ridge)
    h = 0.5 * ridge ** 1.3 + 0.22 * clod * on_ridge + 0.1 * crumb + 0.06 * base
    t = 0.45 + 0.22 * (ridge - 0.5) + 0.12 * clod * on_ridge + 0.06 * crumb + 0.06 * base
    t = t + 0.06 * (cell_random(cid, seed + 6) - 0.5) * on_ridge
    if wet:
        alb = ramp(np.clip(t, 0, 1), [(0, '#160b04'), (0.5, '#2e1c0d'), (1, '#4b3119')])
        return Tex(match_mean(alb, 0.2), norm01(blur(h, 0.6)), light='top', bump=1.4, ao=0.65, gloss=0.15)
    alb = ramp(np.clip(t, 0, 1), [(0, '#463021'), (0.5, '#6d4f35'), (1, '#957357')])
    return Tex(match_mean(alb, 0.42), norm01(blur(h, 0.6)), light='top', bump=1.4, ao=0.65)


# ------------------------------------------------------------------ sandstone
SANDSTONE = [(0.0, '#b49a6a'), (0.35, '#cdb582'), (0.7, '#dcc797'), (1.0, '#ebdbb1')]
RED_SANDSTONE = [(0.0, '#8a3f14'), (0.35, '#a6531d'), (0.7, '#b9672b'), (1.0, '#cc7f3e')]


def sandstone(seed=90, face='side', stops=SANDSTONE, target=0.8):
    x, y = grid(N)
    wx, wy = warped_coords(N, 0.03, seed, freq=3)
    base = fbm(N, 4, seed, 5, x=wx, y=wy)
    grain = fbm(N, 96, seed + 1, 2)
    dome, gap, cid = grains(N, 72, seed + 2)
    speck = (cell_random(cid, seed + 3) - 0.5)
    if face == 'side':
        r = rng(seed + 4)
        th = r.uniform(0.5, 1.6, 9)
        bounds = np.concatenate([[0], np.cumsum(th) / th.sum()])
        tone_l, hard_l = r.uniform(-1, 1, 9), r.uniform(-1, 1, 9)
        wy2 = wy + 0.012 * fbm(N, (4, 1), seed + 5, 3, x=wx, y=wy)
        idx = np.clip(np.searchsorted(bounds, wy2 % 1.0, side='right') - 1, 0, 8)
        pos = ((wy2 % 1.0) - bounds[idx]) / (bounds[idx + 1] - bounds[idx])
        edge = smoothstep(0.0, 0.12, pos) * smoothstep(1.0, 0.85, pos)
        lam = np.sin(2 * np.pi * (wy2 * 36 + 3 * wx))
        t = 0.55 + 0.13 * tone_l[idx] + 0.05 * base + 0.06 * grain + 0.05 * speck + 0.02 * lam
        h = 0.5 + 0.1 * hard_l[idx] * edge + 0.04 * edge + 0.03 * lam + 0.05 * grain + 0.05 * dome
        light = 'top'
    elif face == 'bottom':
        pits = smoothstep(0.55, 0.85, fbm(N, 24, seed + 5, 3))
        t = 0.5 + 0.1 * base + 0.08 * grain + 0.08 * speck - 0.12 * pits
        h = 0.5 + 0.12 * base + 0.06 * grain + 0.08 * dome - 0.2 * pits
        light = 'over'
    else:  # top: wind-smoothed
        rip = fbm(N, 5, seed + 6, 3, stretch=(1, 2))
        t = 0.55 + 0.07 * base + 0.05 * grain + 0.05 * speck + 0.04 * rip
        h = 0.5 + 0.1 * base + 0.03 * grain + 0.05 * dome + 0.06 * rip
        light = 'over'
    alb = ramp(np.clip(t, 0, 1), stops)
    return Tex(match_mean(alb, target), norm01(h), light=light, bump=0.9, ao=0.45)


def cut_sandstone(seed=93, stops=SANDSTONE, target=0.8):
    """Cut ('smooth') sandstone: dressed ashlar courses with fine joints."""
    s = sandstone(seed, 'top', stops, target)
    x, y = grid(N)
    joint = smoothstep(0.03, 0.0, np.minimum(np.abs(y - 0.5), np.minimum(y, 1 - y)))
    chip = smoothstep(0.6, 0.85, fbm(N, 20, seed + 1, 3)) * smoothstep(0.06, 0.0, np.minimum(np.abs(y - 0.5), np.minimum(y, 1 - y)))
    joint = smoothstep(0.018, 0.0, np.minimum(np.abs(y - 0.5), np.minimum(y, 1 - y)))
    alb = s.albedo * (1 - 0.12 * joint[..., None]) * (1 - 0.1 * chip[..., None])
    h = s.height * 0.4 + 0.6 - 0.25 * joint - 0.25 * chip
    return Tex(match_mean(alb, target), norm01(h), light='top', bump=1.0, ao=0.6)


def carved_sandstone(seed=94, stops=SANDSTONE, target=0.79):
    """Chiseled sandstone: a framed panel carved with a radiating rosette (original motif)."""
    from engine.draw import X, Y, rect, circle
    s = sandstone(seed, 'top', stops, target)
    frame = rect(1.0, 1.0, 15.0, 15.0) - rect(2.2, 2.2, 13.8, 13.8)
    cx, cy = 8.0, 8.0
    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    ang = np.arctan2(Y - cy, X - cx)
    petals = (np.cos(ang * 8) * 0.5 + 0.5) ** 2
    rosette = smoothstep(4.6, 4.3, r) * smoothstep(1.2, 1.5, r) * (petals > 0.35)
    ring = smoothstep(0.35, 0.15, np.abs(r - 5.4))
    corner = sum(circle(px, py, 0.7) for px in (3.4, 12.6) for py in (3.4, 12.6))
    hub = circle(cx, cy, 1.0)
    relief = np.clip(frame + rosette + ring + corner + hub, 0, 1)
    wear = smoothstep(0.2, 0.75, fbm(N, 7, seed + 2, 4))
    relief = blur(relief, 1.2) * (1 - 0.35 * wear)
    sunk = rect(2.2, 2.2, 13.8, 13.8) * (1 - relief)
    h = 0.55 + 0.3 * relief - 0.2 * sunk + 0.08 * s.height
    border = smoothstep(0.0, 0.03, np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y)) / 16)
    alb = s.albedo * (1 - 0.1 * sunk[..., None]) * (0.85 + 0.15 * border[..., None])
    return Tex(match_mean(alb, target), blur(h, 0.8), light='top', bump=1.6, ao=0.7)


# ------------------------------------------------------------------ bedrock, obsidian
def bedrock(seed=96, target=0.33):
    t = rock(seed, [(0.0, '#121213'), (0.3, '#2b2b2c'), (0.55, '#4a4a4a'), (0.8, '#6f6e6c'), (1.0, '#9a9893')],
             mottling=2.2, cracks=1.4, lumps=1.8, pits=0.6, bump=1.5, ao=0.7, crack_freq=4,
             fleck=[(20, 0.12, 0.35, '#0e0e0f', 0.7), (30, 0.06, 0.3, '#a8a49c', 0.5)])
    x, y = warped_coords(N, 0.08, seed + 7, freq=3)
    f1, f2, cid = worley(N, 3, seed + 8, 1.0, x, y)
    clast = cell_random(cid, seed + 9)
    alb = t.albedo * (0.88 + 0.24 * clast[..., None])
    return t.but(albedo=match_mean(alb, target))


def obsidian(seed=98, crying=False):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    f1, f2, cid = worley(N, 4, seed + 1, 0.9, x, y)
    shell = (f1 * 3.0 + 0.3 * cell_random(cid, seed + 2)) % 1.0
    conch = smoothstep(0.0, 0.08, shell) * smoothstep(0.35, 0.08, shell)
    ridge = 1 - smoothstep(0.0, 0.04, f2 - f1)
    cloud = fbm(N, 3, seed + 3, 5)
    t = 0.35 + 0.15 * cloud + 0.14 * conch + 0.15 * cell_random(cid, seed + 4)
    alb = ramp(np.clip(t, 0, 1), [(0, '#06040b'), (0.4, '#140d22'), (0.7, '#2a1c44'), (1, '#4b3a70')])
    alb = mix(alb, hexrgb('#6f5c98'), ridge * 0.6)
    h = 0.5 + 0.3 * (1 - f1) * 0.5 + 0.1 * cloud - 0.1 * ridge
    emissive = None
    if crying:
        seams = smoothstep(0.9, 0.97, ridged(N, 4, seed + 5, 4, sharp=2.0)) * smoothstep(0.0, 0.4, fbm(N, 4, seed + 6, 3) + 0.2)
        from engine.draw import capsules
        rr = rng(seed + 7)
        segs, vals = [], []
        for _ in range(9):
            x0, y0 = rr.uniform(0, 16), rr.uniform(0, 16)
            w = rr.uniform(0.4, 0.8)
            x1, y1 = x0, y0
            for k in range(rr.integers(2, 5)):
                x2, y2 = x1 + rr.uniform(-0.35, 0.35), y1 + rr.uniform(0.5, 1.4)
                segs.append((x1, y1, x2, y2, w, w * 0.75, 0))
                vals.append((rr.uniform(0.55, 0.9),))
                x1, y1, w = x2, y2, w * 0.75
        tv, tc, _ = capsules(np.array(segs), np.array(vals))
        seep = smoothstep(0.55, 0.75, 0.5 + 0.5 * fbm(N, 6, seed + 8, 4)) * smoothstep(0.3, 0.6, seams + 0.4)
        glow = np.clip(seams * 0.8 + tc * tv[..., 0] + seep * 0.7, 0, 1)
        alb = mix(alb, hexrgb('#7a1fd0'), glow * 0.8)
        emissive = (glow ** 1.5 * 0.55)[..., None] * hexrgb('#b05cff')
    alb = match_mean(alb, 0.06 if not crying else 0.07)
    return Tex(alb, norm01(h), light='over', bump=1.2, ao=0.4, gloss=0.35, emissive=emissive)


# ------------------------------------------------------------------ archaeology
def suspicious(seed, base_tex, stage, shard=('#8f5232', '#b4714a', '#3b2a20')):
    """Sand or gravel hiding a fired-clay shard: barely hinted at stage 0, brushed clear by stage 3."""
    from engine.draw import X, Y
    body, edge_c, paint = (hexrgb(c) for c in shard)
    reveal = [0.12, 0.38, 0.62, 0.88][stage]
    cx, cy, ang = 8.4, 9.2, 0.3
    u = (X - cx) * np.cos(ang) + (Y - cy) * np.sin(ang)
    v = -(X - cx) * np.sin(ang) + (Y - cy) * np.cos(ang)
    curve = v + 0.05 * u * u
    jag = 0.7 * fbm(N, 9, seed, 3)
    shape = ((np.abs(u) + jag) < 3.0) & (curve > -1.4 + 0.4 * jag) & (curve < 1.6 + 0.3 * jag)
    rim = shape & ~(((np.abs(u) + jag) < 2.7) & (curve > -1.15 + 0.4 * jag) & (curve < 1.35 + 0.3 * jag))
    uncover = 0.5 + 0.5 * fbm(N, 6, seed + 1, 4) + 0.3 * (1 - np.clip(np.abs(u) / 3, 0, 1)) - 0.15
    exposed = shape * smoothstep(1 - reveal - 0.08, 1 - reveal + 0.08, uncover)
    band = (np.abs(curve - 0.3) < 0.35) * 1.0
    grain = 0.9 + 0.15 * fbm(N, 30, seed + 2, 2)
    shard_rgb = mix(body[None, None, :] * grain[..., None], paint, band * 0.8)
    shard_rgb = np.where(rim[..., None], edge_c, shard_rgb)
    dust = 0.25 * (1 - reveal)
    shard_rgb = mix(shard_rgb, base_tex.albedo, dust)
    brushed = smoothstep(1.0, 0.0, np.sqrt(u * u * 0.03 + curve * curve * 0.05)) * reveal
    streak = 0.5 + 0.5 * np.sin(2 * np.pi * (v * 1.4 + 0.6 * fbm(N, 8, seed + 3, 2)))
    alb = base_tex.albedo * (1 + 0.1 * brushed[..., None] * (streak[..., None] - 0.5))
    alb = mix(alb, shard_rgb, exposed)
    h = np.where(exposed > 0.5, 0.75 + 0.05 * grain, base_tex.height * (1 - 0.2 * brushed))
    return Tex(alb, norm01(h), light='top', bump=1.2, ao=0.6)


# ------------------------------------------------------------------ registration
from engine.material import edge_variant, bake_tint  # noqa: E402

GRASS_CARRIED = hexrgb('#6fa84f')


def edged(fn, seed, step=31):
    """Variant factory: variant 0 is fn(seed); variant v keeps fn(seed)'s border band."""
    def make(v):
        base = fn(seed)
        return base if v == 0 else edge_variant(base, fn(seed + step * v))
    return make


def free(fn, seed, step=31):
    """Variant factory for randomly rotated (isotropic) faces: fully independent seeds."""
    return lambda v: fn(seed + step * v)


def register(R):
    R.block('stone', edged(lambda s: stone(s), 1), variants=[6, 3, 3])
    R.block('dirt', free(lambda s: dirt(s), 2), variants=[5, 3, 3])
    R.block('grass_top', free(lambda s: grass_top(s), 6), variants=[5, 3, 3], key='tl_grass_top')
    R.block_entry('grass', textures={'down': 'flattened_dirt', 'side': 'grass_side', 'up': 'tl_grass_top'})
    R.block('grass_side', lambda v: grass_side(7))
    R.block('grass_carried', lambda v: bake_tint(grass_top(6), GRASS_CARRIED))
    R.block('grass_side_carried', lambda v: bake_tint(grass_side(7), GRASS_CARRIED))
    R.block('grass_side_snowed', lambda v: grass_side_snowed(44))
    R.block('grass_block_snow', lambda v: grass_side_snowed(44).but(tint_mask=None))
    R.block('snow', free(lambda s: snow(s), 40), variants=[5, 3, 3])
    R.block('powder_snow', lambda v: powder_snow(41))
    R.block('ice', lambda v: ice(50, 'clear'))
    for m in range(4):
        R.block(f'frosted_ice_{m}', lambda v, m=m: ice(50, 'clear', melt=m))
    R.block('ice_packed', edged(lambda s: ice(s, 'packed'), 52), variants=[5, 3])
    R.block('blue_ice', lambda v: ice(54, 'blue'))
    R.block('sand', free(lambda s: sand(s), 3), variants=[5, 3, 2])
    R.block('red_sand', free(lambda s: sand(s, stops=[(0.0, '#7d3a17'), (0.4, '#a1501f'), (0.75, '#b8652b'),
                                                      (1.0, '#c97a3c')], target=0.47), 33),
            variants=[5, 3, 2])
    R.block('gravel', free(lambda s: gravel(s), 4), variants=[5, 3, 3])
    R.block_entry('gravel', isotropic=True)
    R.block('cobblestone', edged(lambda s: cobblestone(s), 5), variants=[5, 3, 3])
    R.block('cobblestone_mossy', edged(lambda s: cobblestone(s, mossy=0.85), 9), variants=[5, 3])
    R.block('clay', free(lambda s: clay(s), 60), variants=[4, 3])
    R.block('mud', lambda v: mud(62))
    R.block('packed_mud', lambda v: packed_mud(63))
    R.block('moss_block', free(lambda s: moss(s), 64), variants=[4, 3])
    R.block_entry('moss_block', isotropic=True)
    R.block('pale_moss_block', lambda v: moss(65, stops=[(0, '#2b3129'), (0.4, '#4e5a4a'), (0.75, '#76826f'),
                                                          (1, '#a1ab96')], target=0.42))
    R.block('coarse_dirt', free(lambda s: coarse_dirt(s), 70), variants=[4, 3])
    R.block('dirt_with_roots', lambda v: rooted_dirt(72))
    R.block('dirt_podzol_top', lambda v: podzol_top(74))
    R.block('dirt_podzol_side', lambda v: layer_side(75, podzol_top(74), dirt(76, light='top', target=0.36), 0.17,
                                                     target=0.33, lobes=3, lobe_depth=(0.02, 0.04)))
    R.block('mycelium_top', lambda v: mycelium_top(76))
    R.block('mycelium_side', lambda v: layer_side(77, mycelium_top(76), dirt(78, light='top', target=0.36), 0.18,
                                                  strands=26, strand_rgb=hexrgb('#8d808a'), target=0.36))
    R.block('grass_path_top', lambda v: path_top(78))
    R.block('grass_path_side', lambda v: path_side(79), cutout=True)
    R.block('farmland_dry', lambda v: farmland(80))
    R.block('farmland_wet', lambda v: farmland(80, wet=True))
    for name, face in (('sandstone_top', 'top'), ('sandstone_bottom', 'bottom'), ('sandstone_normal', 'side')):
        R.block(name, lambda v, f=face: sandstone(90, f))
        R.block('red_' + name, lambda v, f=face: sandstone(91, f, RED_SANDSTONE, 0.45))
    R.block('sandstone_smooth', lambda v: cut_sandstone(93))
    R.block('red_sandstone_smooth', lambda v: cut_sandstone(95, RED_SANDSTONE, 0.45))
    R.block('sandstone_carved', lambda v: carved_sandstone(94))
    R.block('red_sandstone_carved', lambda v: carved_sandstone(97, RED_SANDSTONE, 0.44))
    R.block('bedrock', edged(lambda s: bedrock(s), 96), variants=[4, 3])
    R.block('obsidian', free(lambda s: obsidian(s), 98), variants=[4, 3])
    R.block('crying_obsidian', lambda v: obsidian(99, crying=True))
    for st in range(4):
        R.block(f'suspicious_sand_{st}', lambda v, st=st: suspicious(120, sand(3).but(light='top'), st))
        R.block(f'suspicious_gravel_{st}', lambda v, st=st: suspicious(121, gravel(4).but(light='top'), st))
