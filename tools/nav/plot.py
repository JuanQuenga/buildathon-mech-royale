#!/usr/bin/env python3
"""Render the nav bake (surface, walkable mask, components), optional replay tracks and planned paths to PNG.

    python tools/nav/plot.py out.png [--bake bot/navbake.npz] [--replay R.jsonl.gz] [--window x0 x1 y0 y1]
                             [--path x,y x,y ...]  [--layer walk|comp|g|dwall] [--class 0]

`--path` plans with bot.arena.Arena between consecutive points and draws the waypoints.
Needs numpy + matplotlib (offline only).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--bake", default=os.path.join(ROOT, "bot", "navbake.npz"))
    ap.add_argument("--arena", default=os.path.join(ROOT, "arena", "v2"))
    ap.add_argument("--replay")
    ap.add_argument("--window", nargs=4, type=float)
    ap.add_argument("--path", nargs="*")
    ap.add_argument("--layer", default="walk")
    ap.add_argument("--klass", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args()

    z = np.load(a.bake)
    meta = json.loads(bytes(z["meta"]).decode())
    x0, y0, nx, ny = meta["minX"], meta["minY"], meta["nx"], meta["ny"]
    g = z["g"] / 100.0
    ext = (x0 - 0.5, x0 + nx - 0.5, y0 - 0.5, y0 + ny - 0.5)
    fig, ax = plt.subplots(figsize=(14, 10))
    # hillshade of g
    gy, gx = np.gradient(g)
    shade = np.clip(0.6 + 0.4 * (-gx - gy) / np.sqrt(1 + gx * gx + gy * gy), 0, 1)
    ax.imshow(shade, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
    if a.layer == "walk":
        w = ((z["walk"] >> a.klass) & 1).astype(float)
        ov = np.zeros((ny, nx, 4))
        ov[..., 1] = 0.8
        ov[..., 3] = 0.25 * w
        roof = (z["comp"] > 0)
        ov[roof, 0], ov[roof, 2], ov[roof, 3] = 0.9, 0.9, 0.35
        steep = (z["kind"] & 0x10) > 0
        ov[steep] = (1, 0, 0, 0.6)
        ax.imshow(ov, origin="lower", extent=ext)
    elif a.layer == "comp":
        c = z["comp"].astype(float)
        c[c < 0] = np.nan
        ax.imshow(np.where(np.isnan(c), np.nan, (c * 37) % 20), origin="lower", extent=ext, cmap="tab20", alpha=0.6)
    elif a.layer == "g":
        im = ax.imshow(g, origin="lower", extent=ext, cmap="terrain", alpha=0.7)
        fig.colorbar(im, ax=ax, shrink=0.6)
    elif a.layer == "dwall":
        im = ax.imshow(z["dwall"] / 10.0, origin="lower", extent=ext, cmap="viridis", alpha=0.7)
        fig.colorbar(im, ax=ax, shrink=0.6)
    w = json.load(open(os.path.join(a.arena, "world.json")))
    for p in w["prisms"]:
        r = np.asarray(p["ring"]).reshape(-1, 2)
        col = {"building": "k", "stadium": "purple", "bridge": "orange"}[p["kind"]]
        ax.plot(np.r_[r[:, 0], r[0, 0]], np.r_[r[:, 1], r[0, 1]], col, lw=0.4)
        for hh in p.get("holes") or []:
            r = np.asarray(hh).reshape(-1, 2)
            ax.plot(np.r_[r[:, 0], r[0, 0]], np.r_[r[:, 1], r[0, 1]], col, lw=0.3, ls="--")
    if a.replay:
        with gzip.open(a.replay, "rt") as f:
            f.readline()
            pts = []
            for line in f:
                fr = json.loads(line)
                for m in fr.get("m", []):
                    pts.append((m[1], m[2], m[8]))
        pts = np.array(pts)
        gr = (pts[:, 2].astype(int) & 1) > 0
        ax.scatter(pts[gr, 0], pts[gr, 1], s=0.3, c="blue")
        ax.scatter(pts[~gr, 0], pts[~gr, 1], s=0.3, c="cyan")
    if a.path:
        from bot.arena import Arena
        ar = Arena.load(os.path.dirname(a.arena))
        P = [tuple(map(float, s.split(","))) for s in a.path]
        for s, e in zip(P, P[1:]):
            s3 = (s[0], s[1], ar.ground_z(s[0], s[1]))
            e3 = (e[0], e[1], ar.ground_z(e[0], e[1]))
            wp = ar.plan(s3, e3, budget_ms=5000)
            xs = [s3[0]] + [q[0] for q in wp]
            ys = [s3[1]] + [q[1] for q in wp]
            ax.plot(xs, ys, "r.-", lw=1.2, ms=3)
            raw = ar.last_raw_path or []
            if raw:
                ax.plot([q[0] for q in raw], [q[1] for q in raw], "y-", lw=0.6)
            ax.plot([s3[0]], [s3[1]], "go")
            ax.plot([e3[0]], [e3[1]], "rx")
            print(f"path {s}->{e}: {len(wp)} waypoints, len {ar.path_len(s3, e3):.1f} m", file=sys.stderr)
    if a.window:
        ax.set_xlim(a.window[0], a.window[1])
        ax.set_ylim(a.window[2], a.window[3])
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(a.out, dpi=a.dpi)


if __name__ == "__main__":
    main()
