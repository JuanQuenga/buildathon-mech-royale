#!/usr/bin/env python3
"""Cross-check the nav bake against a recorded replay (mechreplay/1).

    python tools/nav/replay_check.py <replay.jsonl.gz> [bot/navbake.npz]

Reports, for every recorded mech sample: where it stands relative to the baked surface g, whether its
vertex is walkable (main ground component), roof visits, and clearance statistics. Also derives empirical
movement numbers (speeds, jump/jet climb rates) used to verify docs/nav.md.
"""
from __future__ import annotations

import gzip
import json
import sys

import numpy as np


def main(replay, bake="bot/navbake.npz"):
    z = np.load(bake)
    meta = json.loads(bytes(z["meta"]).decode())
    g = z["g"] / 100.0
    walk = z["walk"]
    kind = z["kind"]
    dwall = z["dwall"] / 10.0
    comp = z["comp"]
    x0, y0, nx, ny = meta["minX"], meta["minY"], meta["nx"], meta["ny"]
    rows = []
    with gzip.open(replay, "rt") as f:
        hdr = json.loads(f.readline())
        for line in f:
            fr = json.loads(line)
            if "m" not in fr:
                continue
            for m in fr["m"]:
                rows.append((fr["t"] / hdr.get("tick_hz", 20), m[0], m[1], m[2], m[3], m[7], m[8], m[9]))
    a = np.array(rows)
    t, mid, x, y, zz, en, flags, cubes = a.T
    i = np.clip(np.rint(x - x0).astype(int), 0, nx - 1)
    j = np.clip(np.rint(y - y0).astype(int), 0, ny - 1)
    gv = g[j, i]
    grounded = (flags.astype(int) & 1) > 0
    dz = zz - gv
    print(f"{len(a)} samples, grounded {grounded.sum()}")
    gr = grounded
    print("grounded z - g (nearest vertex): pct 1/5/50/95/99 =", np.percentile(dz[gr], [1, 5, 50, 95, 99]).round(2))
    w0 = (walk[j, i] & 1) > 0
    print(f"grounded on class-0 main component: {w0[gr].mean() * 100:.1f}%")
    k = kind[j, i] & 15
    print("grounded by surface kind (0 terrain,1 bldg,2 stadium,3 bridge):",
          {int(u): int(((k == u) & gr).sum()) for u in np.unique(k)})
    roof = gr & (k == 1) & (dz > -1.5)
    print(f"grounded on building tops: {roof.sum()} samples, mechs {sorted(set(mid[roof].astype(int)))}")
    off = gr & ~w0
    print(f"grounded off-walk samples: {off.sum()}; clearance there pct 5/50/95:",
          np.percentile(dwall[j, i][off], [5, 50, 95]).round(2) if off.any() else "-")
    print("min clearance (dwall) of grounded samples on terrain:", np.percentile(dwall[j, i][gr & (k == 0)], [0, 0.1, 1, 5]).round(2))
    # off-walk where: comps
    cc = comp[j, i][off]
    print("off-walk comp ids:", np.unique(cc, return_counts=True))
    # speeds
    order = np.lexsort((t, mid))
    a2 = a[order]
    same = a2[1:, 1] == a2[:-1, 1]
    dt = a2[1:, 0] - a2[:-1, 0]
    ok = same & (dt > 0) & (dt < 0.3)
    v = np.hypot(a2[1:, 2] - a2[:-1, 2], a2[1:, 3] - a2[:-1, 3])[ok] / dt[ok]
    vz = ((a2[1:, 4] - a2[:-1, 4]) / np.maximum(dt, 1e-9))[ok]
    print("horizontal speed pct 50/90/99/max:", np.percentile(v, [50, 90, 99, 100]).round(2))
    print("vertical speed pct 0.1/1/99/99.9:", np.percentile(vz, [0.1, 1, 99, 99.9]).round(2))
    return a


if __name__ == "__main__":
    main(*sys.argv[1:])
