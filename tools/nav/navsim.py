#!/usr/bin/env python3
"""Closed-loop navigation test on the sim's movement physics (sim/engine.py), in process.

    python tools/nav/navsim.py [--n 40] [--seed 1] [--start x,y --goal x,y] [--maxd 400] [--plot out.png]

For each trial: put mech 0 at a walkable start, give navigate.step a fixed goal, step the engine (other mechs
parked in a corner, no NPCs) until within 3 m of the goal or timeout (3 x ideal + 15 s). Reports success rate,
time / ideal (path length / walk speed), stalls, jets and step latency. Physics fidelity is the sim's (see
docs/SIM_ISSUES.md for known differences from the real server).
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "sim"))

from config import load_config, sim_config  # noqa: E402
from engine import Match  # noqa: E402
from sense import self_obs, zone_obs  # noqa: E402
from world import World  # noqa: E402

from bot import navigate  # noqa: E402
from bot.arena import Arena  # noqa: E402
from bot.state import Intent, Threats, WorldState  # noqa: E402


def make_match(world, seed):
    cfg = load_config()
    M = Match(world, seed=seed, cfg=cfg, sim=sim_config())
    M.npcs = []
    M.projs = []
    M._pending_takes = []
    for i, m in enumerate(M.mechs[1:]):
        x, y = -505.0 + 6 * (i % 4), 380.0 - 6 * (i // 4)
        m.pos = [x, y, world.support(x, y, 100.0)]
    return M


def obs_for(M, m):
    return {"type": "obs", "tick": M.tick, "t": round(M.t, 3), "alive": M.alive_count, "self": self_obs(M, m),
            "mechs": [], "projectiles": [], "crates": [], "cubes": [], "pickups": [], "sounds": [], "beams": [],
            "events": [], "drops": [], "zone": zone_obs(M), "offer": None}


def run_trial(world, arena, start, goal, seed=0, timeout=None, urgency=0.5, trace=None):
    M = make_match(world, seed)
    me = M.mechs[0]
    me.pos = [start[0], start[1], world.support(start[0], start[1], 200.0)]
    me.vel = [0.0, 0.0, 0.0]
    hello = {"config": M.cfg, "slot": 0, "seed": seed}
    st = WorldState(hello, arena)
    gz = arena.surface(goal[0], goal[1])
    L = arena.path_len((start[0], start[1], 0), (goal[0], goal[1], gz), budget_ms=1e5)
    ideal = (L if L != math.inf else math.dist(start, goal) * 1.3) / 11.7
    timeout = timeout or (3 * ideal + 15)
    intent = Intent(mode="rotate", goal=(goal[0], goal[1], gz), urgency=urgency)
    lat = []
    t0 = M.t
    while M.t - t0 < timeout:
        if M.tick % M.decide_every == 0:
            st.update(obs_for(M, me))
            a = time.perf_counter()
            out = navigate.step(st, intent, Threats())
            lat.append((time.perf_counter() - a) * 1000)
            M.apply_action(me, {"tick": M.tick, "move": list(out.move), "boost": out.boost, "jump": out.jump})
            if trace is not None:
                trace.append((me.pos[0], me.pos[1], me.pos[2], out.blocked))
            if math.hypot(me.pos[0] - goal[0], me.pos[1] - goal[1]) < 3.0:
                break
        M.step()
    ok = math.hypot(me.pos[0] - goal[0], me.pos[1] - goal[1]) < 3.0
    ns = st.scratch.get("nav", {}).get("stats", {})
    return {"ok": ok, "t": M.t - t0, "ideal": ideal, "L": L, "stalls": ns.get("stalls", 0), "jets": ns.get("jets", 0),
            "lat_max": max(lat) if lat else 0, "lat_p99": sorted(lat)[int(0.99 * (len(lat) - 1))] if lat else 0,
            "end": tuple(round(v, 1) for v in me.pos), "lat": lat}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--start")
    ap.add_argument("--goal")
    ap.add_argument("--mind", type=float, default=50)
    ap.add_argument("--maxd", type=float, default=400)
    ap.add_argument("--plot")
    a = ap.parse_args()
    world = World(os.path.join(ROOT, "arena"))
    arena = Arena.load(os.path.join(ROOT, "arena"))
    rng = random.Random(a.seed)
    trials = []
    if a.start and a.goal:
        trials.append((tuple(map(float, a.start.split(","))), tuple(map(float, a.goal.split(",")))))
    else:
        while len(trials) < a.n:
            s = (rng.uniform(-480, 530), rng.uniform(-310, 360))
            g = (rng.uniform(-480, 530), rng.uniform(-310, 360))
            if not (a.mind <= math.dist(s, g) <= a.maxd):
                continue
            if arena.walkable(*s) and arena.walkable(*g):
                trials.append((s, g))
    res = []
    lat_all = []
    for i, (s, g) in enumerate(trials):
        tr = [] if a.plot else None
        r = run_trial(world, arena, s, g, seed=a.seed + i, trace=tr)
        lat_all += r.pop("lat")
        res.append(r)
        flag = "OK " if r["ok"] else "FAIL"
        print(f"{flag} {s[0]:7.1f},{s[1]:7.1f} -> {g[0]:7.1f},{g[1]:7.1f}  L={r['L']:6.1f} t={r['t']:5.1f}s "
              f"ratio={r['t'] / max(r['ideal'], 1e-3):4.2f} stalls={r['stalls']} jets={r['jets']} "
              f"lat_max={r['lat_max']:.1f}ms end={r['end']}", flush=True)
        if a.plot and len(trials) == 1:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 10))
            ax.plot([p[0] for p in tr], [p[1] for p in tr], "b.-", ms=2)
            for p in arena.prisms:
                rr = p["ring"]
                ax.plot(rr[0::2] + rr[:1], rr[1::2] + rr[1:2], "k", lw=0.5)
            wp = arena.plan((s[0], s[1], 0), (g[0], g[1], 0), budget_ms=1e5)
            ax.plot([s[0]] + [q[0] for q in wp], [s[1]] + [q[1] for q in wp], "r--", lw=0.8)
            pad = 30
            xs = [p[0] for p in tr] + [g[0]]
            ys = [p[1] for p in tr] + [g[1]]
            ax.set_xlim(min(xs) - pad, max(xs) + pad)
            ax.set_ylim(min(ys) - pad, max(ys) + pad)
            ax.set_aspect("equal")
            fig.savefig(a.plot, dpi=110)
    n = len(res)
    ok = sum(r["ok"] for r in res)
    ratios = sorted(r["t"] / r["ideal"] for r in res if r["ok"])
    lat_all.sort()
    print(f"\n{ok}/{n} reached; time/ideal median {ratios[len(ratios) // 2] if ratios else float('nan'):.2f} "
          f"max {max(ratios) if ratios else float('nan'):.2f}; stalls {sum(r['stalls'] for r in res)}; "
          f"step latency p50 {lat_all[len(lat_all) // 2]:.2f} p99 {lat_all[int(0.99 * (len(lat_all) - 1))]:.2f} "
          f"max {lat_all[-1]:.2f} ms")


if __name__ == "__main__":
    main()
