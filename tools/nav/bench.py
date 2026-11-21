#!/usr/bin/env python3
"""Micro-benchmarks for bot/arena.py queries (run pinned to one core: taskset -c 0 python tools/nav/bench.py).

Prints p50 / p99 / max in microseconds (ms for planning) over random walkable positions.
"""
from __future__ import annotations

import gc
import math
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from bot.arena import Arena  # noqa: E402


def pct(v, unit=1.0):
    v = sorted(v)
    n = len(v)
    return f"p50 {v[n // 2] * unit:8.1f}  p99 {v[int(0.99 * (n - 1))] * unit:8.1f}  max {v[-1] * unit:8.1f}"


def timeit(f, args_list):
    out = []
    for a in args_list:
        t = time.perf_counter()
        f(*a)
        out.append(time.perf_counter() - t)
    return out


def main():
    t = time.perf_counter()
    A = Arena.load(os.path.join(ROOT, "arena"))
    print(f"Arena.load: {(time.perf_counter() - t) * 1000:.0f} ms")
    gc.collect()
    gc.freeze()
    rng = random.Random(11)
    pts = []
    while len(pts) < 600:
        x, y = rng.uniform(-480, 530), rng.uniform(-310, 360)
        if A.walkable(x, y):
            pts.append((x, y, A.surface(x, y)))
    pairs = []
    while len(pairs) < 1000:
        a, b = rng.choice(pts), rng.choice(pts)
        d = math.dist(a[:2], b[:2])
        if 5 < d < 200:
            pairs.append(((a[0], a[1], a[2] + 7.0), (b[0], b[1], b[2] + 4.5)))
    us = 1e6
    print(f"height              {pct(timeit(A.height, [(p[0], p[1]) for p in pts]), us)}  us")
    print(f"ground_z            {pct(timeit(A.ground_z, [(p[0], p[1], p[2] + 1) for p in pts]), us)}  us")
    A._los_cache.clear()
    print(f"shot_clear (<200 m) {pct(timeit(A.shot_clear, pairs), us)}  us  (uncached)")
    print(f"shot_clear cached   {pct(timeit(A.shot_clear, pairs), us)}  us")
    A._los_cache.clear()
    print(f"los (+trees)        {pct(timeit(A.los, pairs), us)}  us  (uncached)")
    A._los_cache.clear()
    print(f"can_see             {pct(timeit(A.can_see, [(a, b) for a, b in pairs[:300]]), us)}  us")
    A._los_cache.clear()
    print(f"can_shoot           {pct(timeit(A.can_shoot, [(a, b) for a, b in pairs[:300]]), us)}  us")
    short = [(a[0], a[1], a[0] + 5 * math.cos(i), a[1] + 5 * math.sin(i)) for i, a in enumerate(pts)]
    longl = [(a[0], b[0], a[1], b[1]) for a, b in pairs[:300]]
    print(f"walk_line 5 m       {pct(timeit(A.walk_line, short), us)}  us")
    print(f"walk_line <200 m    {pct(timeit(lambda x0, x1, y0, y1: A.walk_line(x0, y0, x1, y1), longl), us)}  us")
    plans = []
    while len(plans) < 60:
        a, b = rng.choice(pts), rng.choice(pts)
        if 100 < math.dist(a[:2], b[:2]) < 700:
            plans.append((a, b))
    cold = []
    for a, b in plans:
        A._searches.clear()
        t = time.perf_counter()
        A.plan_nodes(a, b, 0, 1e5)
        cold.append(time.perf_counter() - t)
    print(f"A* complete (cold, 100-700 m)  {pct(cold, 1e3)}  ms   (unbudgeted; runtime slices it)")
    full = []
    for a, b in plans:
        A._searches.clear()
        A.plan_nodes(a, b, 0, 1e5)
        t = time.perf_counter()
        A.plan_full(a, b, budget_ms=1e5)
        full.append(time.perf_counter() - t)
    print(f"plan_full (search cached)      {pct(full, 1e3)}  ms   (snap + path + string-pulling)")
    bud = []
    for a, b in plans:
        A._searches.clear()
        t = time.perf_counter()
        A.plan(a, b, budget_ms=2.0)
        bud.append(time.perf_counter() - t)
    print(f"plan(budget_ms=2) first call   {pct(bud, 1e3)}  ms")
    cov = []
    for i in range(150):
        p = rng.choice(pts)
        a = rng.uniform(0, 6.283)
        d = rng.uniform(30, 120)
        tp = (p[0] + d * math.cos(a), p[1] + d * math.sin(a), p[2])
        A._los_cache.clear()
        t = time.perf_counter()
        A.nearest_cover(p, tp, 60.0)
        cov.append(time.perf_counter() - t)
    print(f"nearest_cover (60 m, cold)     {pct(cov, 1e3)}  ms")


if __name__ == "__main__":
    main()
