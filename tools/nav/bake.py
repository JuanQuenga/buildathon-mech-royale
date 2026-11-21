#!/usr/bin/env python3
"""Offline navigation bake for the fixed campus map (OWNER: nav).

Run (needs numpy + scipy + matplotlib; NOT needed at runtime):
    python tools/nav/bake.py arena/v2 bot/navbake.npz

Produces a compressed npz consumed by bot/arena.py. Everything is on the terrain vertex grid
(x = minX + i, y = minY + j, 1 m step, nx*ny = 1070*724), arrays indexed [j, i].

  g      int16 cm   standing surface of the "ground column": terrain, raised to the top of every prism
                    whose base is < 9 m above the current surface (buildings -> roof height, low bridge
                    decks -> deck height). Prisms that leave >= 9 m headroom are ceilings (underpasses).
  ceil   int16 cm   lowest ceiling base above g (32767 = none)
  kind   uint8      0 terrain, 1 building, 2 stadium, 3 bridge deck  (what g is the top of)
                    | 0x10 steep terrain (gradient > tan(max_slope))  | 0x20 under a ceiling
  dwall  uint8 dm   distance (decimetres, capped 255) from the vertex to the nearest *wall vertex*
                    (prism-derived vertex that rises > step_up above a neighbour, or the map edge)
  walk   uint8 bits bit k set: vertex belongs to the main ground component for size class k
                    (clearance >= R_PLAN[k], headroom >= 9*S[k], connected by |rise| <= step_up)
  comp   int32      connected-component id for size class 0 (roof islands etc.), -1 = not walkable
  node   uint8[K, by, bx]  coarse 4 m lattice: snapped node offset (ox | oy<<4) within the block, 255 = none
  emask  uint8[K, by, bx]  bit d: directed edge from this block node to neighbour d (DIRS order) is walkable
"""
from __future__ import annotations

import hashlib
import json
import sys
import time

import numpy as np
from matplotlib.path import Path
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

STEP_UP = 1.2
TERRAIN_RISE = 1.6   # per 1 m vertex edge, terrain-to-terrain (see replay_check / docs/nav.md)
MAX_SLOPE_DEG = 50.0
HEIGHT = 9.0
BLOCK = 4
# size classes: (cube scale, planning radius = radius*scale + margin)
SCALES = (1.0, 1.25, 1.5)
MARGIN = 0.4
CAP = 8.0
R_PLAN = tuple(2.5 * s + MARGIN for s in SCALES)
DIRS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
JDIRS = DIRS + tuple((2 * a, 2 * b) for a, b in DIRS)   # jet edges: 1 or 2 blocks away
MAX_JET_CLIMB = 40.0
MIN_COMP = 20
KIND = {"building": 1, "stadium": 2, "bridge": 3}


def load(arena_dir):
    with open(f"{arena_dir}/world.json", "rb") as f:
        raw = f.read()
    w = json.loads(raw)
    t = w["terrain"]
    h = np.fromfile(f"{arena_dir}/terrain.i16", "<i2").reshape(t["ny"], t["nx"]).astype(np.float64) / 100.0
    return w, h, hashlib.sha1(raw).hexdigest()


def rasterize(w, X, Y):
    """Yield (prism, mask-slice, mask) for every prism on the vertex grid."""
    t = w["terrain"]
    x0, y0, nx, ny = t["minX"], t["minY"], t["nx"], t["ny"]
    for p in w["prisms"]:
        r = np.asarray(p["ring"], float).reshape(-1, 2)
        i0 = max(0, int(np.floor(r[:, 0].min() - x0)) - 1)
        i1 = min(nx, int(np.ceil(r[:, 0].max() - x0)) + 2)
        j0 = max(0, int(np.floor(r[:, 1].min() - y0)) - 1)
        j1 = min(ny, int(np.ceil(r[:, 1].max() - y0)) + 2)
        if i0 >= i1 or j0 >= j1:
            continue
        pts = np.stack([X[j0:j1, i0:i1].ravel(), Y[j0:j1, i0:i1].ravel()], 1)
        inside = Path(r).contains_points(pts)
        for hole in p.get("holes") or []:
            hr = np.asarray(hole, float).reshape(-1, 2)
            inside &= ~Path(hr).contains_points(pts)
        yield p, (slice(j0, j1), slice(i0, i1)), inside.reshape(j1 - j0, i1 - i0)


def prism_edge_dist(p, x0, y0, nx, ny, sub=0.5):
    """Distance (m, capped) from vertices near prism p to its nearest ring/hole edge."""
    rings = [np.asarray(p["ring"], float).reshape(-1, 2)] + [np.asarray(h, float).reshape(-1, 2) for h in p.get("holes") or []]
    allp = np.concatenate(rings)
    i0 = max(0, int(np.floor(allp[:, 0].min() - x0 - CAP)))
    i1 = min(nx, int(np.ceil(allp[:, 0].max() - x0 + CAP)) + 1)
    j0 = max(0, int(np.floor(allp[:, 1].min() - y0 - CAP)))
    j1 = min(ny, int(np.ceil(allp[:, 1].max() - y0 + CAP)) + 1)
    if i0 >= i1 or j0 >= j1:
        return None, None
    f = int(round(1 / sub))
    W, H = (i1 - i0 - 1) * f + 1, (j1 - j0 - 1) * f + 1
    mark = np.zeros((H, W), bool)
    ox, oy = x0 + i0, y0 + j0
    for r in rings:
        a, bb = r, np.roll(r, -1, axis=0)
        for (ax, ay), (bx, by) in zip(a, bb):
            n = int(np.ceil(np.hypot(bx - ax, by - ay) / 0.1)) + 1
            tt = np.linspace(0, 1, n)
            u = np.rint((ax + (bx - ax) * tt - ox) / sub).astype(int)
            v = np.rint((ay + (by - ay) * tt - oy) / sub).astype(int)
            k = (u >= 0) & (u < W) & (v >= 0) & (v < H)
            mark[v[k], u[k]] = True
    if not mark.any():
        return None, None
    d = ndimage.distance_transform_edt(~mark) * sub
    return (slice(j0, j1), slice(i0, i1)), np.minimum(d[::f, ::f], CAP)


def main(arena_dir, out_path):
    t0 = time.time()
    w, h, sha = load(arena_dir)
    t = w["terrain"]
    nx, ny, x0, y0 = t["nx"], t["ny"], t["minX"], t["minY"]
    X, Y = np.meshgrid(x0 + np.arange(nx), y0 + np.arange(ny))

    g = h.copy()
    ceil = np.full_like(h, np.inf)
    kind = np.zeros(h.shape, np.uint8)
    masks = list(rasterize(w, X, Y))
    masks.sort(key=lambda m: m[0]["base"])
    for p, sl, m in masks:
        gs, cs, ks = g[sl], ceil[sl], kind[sl]
        base, top = p["base"], p["top"]
        lift = m & (base < gs + HEIGHT) & (top > gs)
        gs[lift] = top
        ks[lift] = KIND[p["kind"]]
        roof = m & (base >= gs + HEIGHT)
        cs[roof] = np.minimum(cs[roof], base)
    # a ceiling that ended up below a raised surface is irrelevant
    ceil[ceil < g] = np.inf
    print(f"rasterized {len(masks)} prisms in {time.time() - t0:.1f}s", file=sys.stderr)

    # steep terrain (bilinear terrain gradient, central differences)
    # LiDAR terrain has 1 m spikes that house bots walk over (replay: local bilinear slopes up to ~1.4-1.6
    # m/m are climbed without boost), so judge steepness on a lightly smoothed surface.
    gy, gx = np.gradient(ndimage.gaussian_filter(h, 1.0))
    steep = (np.hypot(gx, gy) > np.tan(np.radians(MAX_SLOPE_DEG))) & (kind == 0)

    # Clearance: horizontal distance from each vertex to the nearest prism *edge* that is a wall for a mech
    # standing on that vertex's surface g (prism top > g + step_up and base < g + height). Per-prism local
    # EDTs on a 0.5 m sub-grid with edges densely sampled, so sub-metre slivers are caught (error <= ~0.36 m).
    b = w["bounds"]
    out = (X < b["minX"]) | (X > b["maxX"]) | (Y < b["minY"]) | (Y > b["maxY"])
    dbound = np.minimum.reduce([X - b["minX"], b["maxX"] - X, Y - b["minY"], b["maxY"] - Y])
    dists = [np.minimum(np.full(g.shape, CAP), np.maximum(dbound, 0)) for _ in SCALES]
    for p in w["prisms"]:
        sl, d = prism_edge_dist(p, x0, y0, nx, ny)
        if sl is None:
            continue
        gs = g[sl]
        for k, s in enumerate(SCALES):
            blk = (p["top"] > gs + STEP_UP) & (p["base"] < gs + HEIGHT * s)
            dk = dists[k][sl]
            np.minimum(dk, np.where(blk, d, CAP), out=dk)
    dist = dists[0]
    dwall = np.clip(np.round(dist * 10), 0, 255).astype(np.uint8)
    print(f"clearance fields in {time.time() - t0:.1f}s", file=sys.stderr)

    headroom = ceil - g
    walk = np.zeros(g.shape, np.uint8)
    comp0 = None
    idx = np.arange(nx * ny).reshape(ny, nx)
    for k, (s, rp) in enumerate(zip(SCALES, R_PLAN)):
        ok = (dists[k] >= rp) & (headroom >= HEIGHT * s) & ~out
        rows, cols = [], []
        for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1)):
            a = (slice(max(0, -dj), ny - max(0, dj)), slice(0, nx - di))
            bb = (slice(max(0, dj), ny + min(0, dj)), slice(di, nx))
            ga, gb = g[a], g[bb]
            dz = gb - ga
            both_terrain = (kind[a] == 0) & (kind[bb] == 0)
            e = ok[a] & ok[bb] & (np.abs(dz) <= np.where(both_terrain, TERRAIN_RISE, STEP_UP))
            # uphill into steep terrain is not walkable (treat the edge as blocked both ways)
            e &= ~((dz > 0) & steep[bb]) & ~((dz < 0) & steep[a])
            rows.append(idx[a][e])
            cols.append(idx[bb][e])
        rows = np.concatenate(rows)
        cols = np.concatenate(cols)
        n = nx * ny
        G = coo_matrix((np.ones(len(rows), np.int8), (rows, cols)), shape=(n, n))
        ncomp, lab = connected_components(G, directed=False)
        lab = lab.reshape(ny, nx)
        lab[~ok] = -1
        sizes = np.bincount(lab[lab >= 0].ravel())
        main_c = int(np.argmax(sizes))
        walk |= ((lab == main_c).astype(np.uint8) << k)
        # bit k+3: standable on any component of >= MIN_COMP cells (roofs, stadium bowl/stands, decks)
        bigc = np.zeros(len(sizes) + 1, bool)
        bigc[:len(sizes)] = sizes >= MIN_COMP
        walk |= ((bigc[np.where(lab >= 0, lab, len(sizes))]).astype(np.uint8) << (k + 3))
        print(f"class {k}: r_plan {rp:.2f}  main component {sizes[main_c]} cells, "
              f"{(sizes >= 50).sum()} comps >=50 cells", file=sys.stderr)
        if k == 0:
            # renumber: main = 0, others by size
            order = np.argsort(-sizes)
            remap = np.empty_like(order)
            remap[order] = np.arange(len(order))
            comp0 = np.where(lab >= 0, remap[np.maximum(lab, 0)], -1).astype(np.int32)

    # coarse lattice
    bx, by = (nx + BLOCK - 1) // BLOCK, (ny + BLOCK - 1) // BLOCK
    K = len(SCALES)
    node = np.full((K, by, bx), 255, np.uint8)
    emask = np.zeros((K, by, bx), np.uint8)
    jmask = np.zeros((K, by, bx), np.uint16)
    jclimb = np.zeros((K, by, bx, len(JDIRS)), np.uint8)
    nosky = (np.isfinite(ceil))
    pad_nx, pad_ny = bx * BLOCK, by * BLOCK
    for k, rp in enumerate(R_PLAN):
        wk = np.zeros((pad_ny, pad_nx), bool)
        wk[:ny, :nx] = (walk >> (k + 3)) & 1
        mainb = np.zeros((pad_ny, pad_nx))
        mainb[:ny, :nx] = (walk >> k) & 1
        dd = np.zeros((pad_ny, pad_nx))
        dd[:ny, :nx] = dists[k]
        # score: clearance (saturating) minus distance from block centre
        oy, ox = np.meshgrid(np.arange(BLOCK), np.arange(BLOCK), indexing="ij")
        cdist = np.hypot(ox - (BLOCK - 1) / 2, oy - (BLOCK - 1) / 2)
        sc = np.minimum(dd, rp + 2.5).reshape(by, BLOCK, bx, BLOCK).transpose(0, 2, 1, 3).reshape(by, bx, BLOCK * BLOCK)
        sc = sc - 0.15 * np.tile(cdist.ravel(), (by, bx, 1))
        sc = sc + 2.0 * mainb.reshape(by, BLOCK, bx, BLOCK).transpose(0, 2, 1, 3).reshape(by, bx, BLOCK * BLOCK)
        wb = wk.reshape(by, BLOCK, bx, BLOCK).transpose(0, 2, 1, 3).reshape(by, bx, BLOCK * BLOCK)
        sc = np.where(wb, sc, -1e9)
        best = np.argmax(sc, axis=2)
        has = wb.any(axis=2)
        bo_y, bo_x = best // BLOCK, best % BLOCK
        node[k] = np.where(has, (bo_x | (bo_y << 4)).astype(np.uint8), 255)
        # absolute fine coordinates of nodes
        BJ, BI = np.meshgrid(np.arange(by), np.arange(bx), indexing="ij")
        fi = BI * BLOCK + bo_x
        fj = BJ * BLOCK + bo_y
        NS = 32
        tt = np.linspace(0, 1, NS)
        wk_full = ((walk >> (k + 3)) & 1).astype(bool)

        def sample(di, dj):
            tb_i, tb_j = BI + di, BJ + dj
            valid = has & (tb_i >= 0) & (tb_i < bx) & (tb_j >= 0) & (tb_j < by)
            tb_ic, tb_jc = np.clip(tb_i, 0, bx - 1), np.clip(tb_j, 0, by - 1)
            valid &= has[tb_jc, tb_ic]
            gi, gj = fi[tb_jc, tb_ic], fj[tb_jc, tb_ic]
            si = np.clip(np.rint(fi[..., None] + (gi - fi)[..., None] * tt).astype(int), 0, nx - 1)
            sj = np.clip(np.rint(fj[..., None] + (gj - fj)[..., None] * tt).astype(int), 0, ny - 1)
            return valid, si, sj

        walked = {}
        for d, (di, dj) in enumerate(DIRS):
            valid, si, sj = sample(di, dj)
            stand = wk_full[sj, si]
            zz = g[sj, si]
            rise = np.diff(zz, axis=2)
            # walk / drop: never rise more than step_up between samples; samples we cannot stand on are only
            # allowed while airborne after a drop (well below the highest surface so far)
            runmax = np.maximum.accumulate(zz, axis=2)
            okk = (rise <= STEP_UP).all(axis=2) & (stand | (zz < runmax - 3.0)).all(axis=2) & stand[..., -1]
            e = valid & okk
            walked[(di, dj)] = e
            emask[k] |= (e.astype(np.uint8) << d)
        for d, (di, dj) in enumerate(JDIRS):
            valid, si, sj = sample(di, dj)
            if (di, dj) in walked:
                valid &= ~walked[(di, dj)]
            zz = g[sj, si]
            climb = zz.max(axis=2) - zz[..., 0]
            okk = valid & (climb > STEP_UP) & (climb <= MAX_JET_CLIMB) & ~nosky[sj, si].any(axis=2)
            jmask[k] |= (okk.astype(np.uint16) << d)
            jclimb[k][..., d] = np.where(okk, np.clip(np.ceil((climb + 0.3) * 4), 0, 255), 0).astype(np.uint8)
        nn = has.sum()
        ne = sum(int(((emask[k] >> d) & 1).sum()) for d in range(8))
        nj = sum(int(((jmask[k] >> d) & 1).sum()) for d in range(len(JDIRS)))
        print(f"class {k}: {nn} nodes, {ne} walk/drop edges, {nj} jet edges", file=sys.stderr)

    gcm = np.clip(np.round(g * 100), -32000, 32000).astype(np.int16)
    ccm = np.where(np.isinf(ceil), 32767, np.clip(np.round(ceil * 100), -32000, 32000)).astype(np.int16)
    kind_f = kind | (steep.astype(np.uint8) << 4) | (np.isfinite(ceil).astype(np.uint8) << 5)
    meta = dict(world_sha1=sha, nx=nx, ny=ny, minX=x0, minY=y0, block=BLOCK, scales=SCALES, r_plan=R_PLAN,
                step_up=STEP_UP, max_slope_deg=MAX_SLOPE_DEG, height=HEIGHT, dirs=DIRS, jdirs=JDIRS,
                max_jet_climb=MAX_JET_CLIMB, version=2)
    np.savez_compressed(out_path, meta=np.frombuffer(json.dumps(meta).encode(), np.uint8), g=gcm, ceil=ccm,
                        kind=kind_f, dwall=dwall, walk=walk, comp=comp0, node=node, emask=emask, jmask=jmask,
                        jclimb=jclimb)
    print(f"wrote {out_path} in {time.time() - t0:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "arena/v2", sys.argv[2] if len(sys.argv) > 2 else "bot/navbake.npz")
