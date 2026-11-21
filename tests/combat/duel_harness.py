#!/usr/bin/env python3
"""Hit-rate and duel measurements for the combat module inside the team simulator (sim/).

Needs numpy (sim engine):  <venv>/bin/python tests/combat/duel_harness.py hitrate|duel [options]

hitrate: our shooter (threats.assess + combat.step in-process, standing or strafing) vs a scripted,
         non-shooting target on open ground at fixed distances, by target motion pattern
         (stand / walk / strafe / juke / jump). Counts shots and hits per weapon.
duel:    1v1 our combat (+ a simple strafing mover) vs a sim built-in bot tier, both with given loadouts.

Everything else (other mechs, npcs) is removed from the match. Results are the sim's physics, which
follow the rulebook + replay checks (see docs/SIM_ISSUES.md for known gaps).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "sim"))

from bot import state as st  # noqa: E402
from bot import threats as TH  # noqa: E402
from bot import combat as CB  # noqa: E402
from config import load_config, sim_config  # noqa: E402
from engine import Match, Weapon  # noqa: E402
from sense import Senses, build_obs  # noqa: E402
from world import World  # noqa: E402
from builtin import BuiltinBot  # noqa: E402

_W = None


def world():
    global _W
    if _W is None:
        _W = World(None)
    return _W


class Counter:
    def __init__(self, M, sid):
        self.shots = {}
        self.sid = sid
        for kind, name in (("gun", "_fire_gun"), ("mortar", "_fire_mortar"), ("laser", "_fire_laser"), ("lightning", "_fire_lightning")):
            orig = getattr(M, name)

            def wrap(m, *a, _o=orig, _k=kind):
                if m.id == self.sid:
                    self.shots[_k] = self.shots.get(_k, 0) + 1
                return _o(m, *a)
            setattr(M, name, wrap)


def find_spot(W, rng, d, tries=400):
    """Open flat spot A and a point B at distance d with clear LOS (eye to center) and flat ground."""
    cells = W.open_ground_cells()
    for _ in range(tries):
        a = cells[rng.randrange(len(cells))]
        ang = rng.uniform(-math.pi, math.pi)
        bx, by = a[0] + d * math.cos(ang), a[1] + d * math.sin(ang)
        try:
            bz = float(W.ground(bx, by))
        except Exception:
            continue
        if abs(bz - a[2]) > 3:
            continue
        # B's surroundings must be open for strafing: probe +-12 m perpendicular
        ok = True
        for s in (-12, 0, 12):
            px, py = bx - s * math.sin(ang), by + s * math.cos(ang)
            pz = float(W.ground(px, py))
            if abs(pz - bz) > 2.0 or not W.los([(a[0], a[1], a[2] + 8)], [(px, py, pz + 4.5)])[0]:
                ok = False
                break
        if ok and not W.inside_solid(bx, by, bz + 1) and not W.inside_solid(a[0], a[1], a[2] + 1):
            return (float(a[0]), float(a[1]), float(a[2])), (bx, by, bz), ang
    raise RuntimeError("no spot")


def new_match(seed):
    cfg = load_config()
    # no zone pressure in these isolated tests
    cfg["zone"]["start_radius"] = 5000.0
    for ph in cfg["zone"]["phases"]:
        ph["radius"] = 4000.0
        ph["dps"] = 0.0
    M = Match(world(), seed=seed, cfg=cfg, sim=sim_config())
    M.projs = []
    M._pending_takes = []
    M._senses = Senses(M)
    for n in M.npcs:
        n.alive = False
    M.crates = {}
    return M, cfg


def place(M, m, p, yaw):
    m.pos = [p[0], p[1], p[2]]
    m.vel = [0.0, 0.0, 0.0]
    m.aim = [yaw, 0.0]
    m.cmd_aim = [yaw, 0.0]
    m.grounded = True


def mk_weapons(M, m, kinds):
    m.weapons = [None, None]
    for i, k in enumerate(kinds[:2]):
        if k:
            w = Weapon(k)
            if k == "gun":
                w.ammo = int(m.wstats["gun"]["mag"])
            m.weapons[i] = w


class Mover:
    """Scripted target / our own legs."""

    def __init__(self, pattern, rng, axis, keep=None):
        self.p = pattern
        self.keep = keep            # desired range to the opponent (our legs in duels), or None
        self.dist = None
        self.rng = rng
        self.axis = axis            # yaw of the line between the two mechs
        self.dir = 1
        self.next_flip = 0.0
        self.walk_yaw = axis + math.pi / 2 + rng.uniform(-0.6, 0.6)

    def act(self, M, m):
        a = {"move": [0.0, 0.0]}
        t = M.t
        perp = self.axis + math.pi / 2
        if self.p == "stand":
            pass
        elif self.p == "walk":
            a["move"] = [math.cos(self.walk_yaw), math.sin(self.walk_yaw)]
            if t > self.next_flip:  # turn around every 6 s to stay in the arena
                self.walk_yaw += math.pi
                self.next_flip = t + 6.0
        elif self.p in ("strafe", "juke", "jump", "boost"):
            if t > self.next_flip:
                self.dir = -self.dir
                if self.p == "strafe":
                    self.next_flip = t + self.rng.uniform(1.2, 2.5)
                else:
                    self.next_flip = t + self.rng.uniform(0.3, 1.0)
            a["move"] = [self.dir * math.cos(perp), self.dir * math.sin(perp)]
            if self.p == "jump" and m.grounded:
                a["jump"] = True
            if self.p == "boost":
                a["boost"] = m.energy > 5
        if self.keep is not None and self.dist is not None:
            radial = max(-1.0, min(1.0, (self.dist - self.keep) / 15.0))
            mx = a["move"][0] * 0.6 + radial * math.cos(self.axis)
            my = a["move"][1] * 0.6 + radial * math.sin(self.axis)
            n = math.hypot(mx, my)
            a["move"] = [mx / n, my / n] if n > 1 else [mx, my]
        return a


def ours_decide(S, M, m, intent, mover):
    vis = M._senses.visible_set([x for x in M.mechs if x.alive], want_items={m.id})
    obs = build_obs(M, m, vis[m.id], full=True)
    S.update(obs)
    t0 = time.perf_counter()
    th = TH.assess(S)
    out = CB.step(S, intent, th)
    dt = time.perf_counter() - t0
    a = {"tick": obs["tick"], "fire": list(out.fire), "reload": out.reload}
    if out.aim is not None:
        a["aim"] = list(out.aim)
    if mover is not None:
        a.update(mover.act(M, m))
    if th.dodge is not None and getattr(th, "dodge_urgency", 0) > 0.3:
        a["move"] = list(th.dodge)
    return a, dt, obs, out


def hitrate(args):
    W = world()
    res = {}
    timings = []
    for pattern in args.patterns.split(","):
        for d in [float(x) for x in args.dists.split(",")]:
            tot_shots, tot_hits, tot_dmg = {}, {}, 0.0
            for rep in range(args.reps):
                seed = 1000 + rep * 17 + int(d)
                rng = random.Random(seed)
                M, cfg = new_match(seed)
                A, Bm = M.mechs[0], M.mechs[1]
                for x in M.mechs[2:]:
                    x.alive = False
                M.alive_count = 2
                pa, pb, ang = find_spot(W, rng, d)
                place(M, A, pa, ang)
                place(M, Bm, pb, ang + math.pi)
                mk_weapons(M, A, args.loadout.split("+"))
                mk_weapons(M, Bm, ["gun"])
                Bm.hp = Bm.max_hp = 1e9
                A.hp = A.max_hp = 1e9
                S = st.WorldState({"type": "hello", "slot": 0, "seed": seed, "config": cfg}, _arena())
                cnt = Counter(M, A.id)
                mover_b = Mover(pattern, rng, ang)
                mover_a = Mover(args.self_move, random.Random(seed + 1), ang) if args.self_move != "stand" else None
                hits = {}
                dmg = 0.0
                intent = st.Intent(mode="engage", target_id=Bm.id)
                while M.t < args.secs:
                    if M.tick % 2 == 0:
                        a, dt, obs, out = ours_decide(S, M, A, intent, mover_a)
                        timings.append(dt)
                        for ev in obs["events"]:
                            if ev.get("type") == "hit" and ev.get("target") == Bm.id:
                                hits[ev["weapon"]] = hits.get(ev["weapon"], 0) + 1
                                dmg += ev["amount"]
                        M.apply_action(A, a)
                        bact = mover_b.act(M, Bm)
                        bact.update({"tick": M.tick, "aim": [ang + math.pi, 0.0]})
                        M.apply_action(Bm, bact)
                    M.step()
                for k, v in cnt.shots.items():
                    tot_shots[k] = tot_shots.get(k, 0) + v
                for k, v in hits.items():
                    tot_hits[k] = tot_hits.get(k, 0) + v
                tot_dmg += dmg
            row = {k: {"shots": tot_shots.get(k, 0), "hits": tot_hits.get(k, 0),
                       "rate": round(tot_hits.get(k, 0) / max(1, tot_shots.get(k, 0)), 3)} for k in set(tot_shots) | set(tot_hits)}
            row["dps"] = round(tot_dmg / (args.reps * args.secs), 1)
            res[f"{pattern}@{int(d)}"] = row
            print(f"{pattern:7s} d={int(d):3d} " + " ".join(f"{k}:{v['hits']}/{v['shots']}={v['rate']:.2f}" for k, v in sorted(row.items()) if k != "dps")
                  + f"  dps {row['dps']}", flush=True)
    timings.sort()
    if timings:
        print(f"combat+threats per decision: p50 {timings[len(timings)//2]*1e3:.3f} ms p99 {timings[int(.99*len(timings))]*1e3:.3f} ms max {timings[-1]*1e3:.3f} ms")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(res, f, indent=1)


_AR = None


def _arena():
    global _AR
    if _AR is None:
        try:
            from bot.arena import Arena
            _AR = Arena.load(os.path.join(ROOT, "arena"))
        except Exception as ex:
            print("arena load failed", ex)
    return _AR


def duel(args):
    W = world()
    wins = losses = draws = 0
    rows = []
    for rep in range(args.reps):
        seed = 5000 + rep
        rng = random.Random(seed)
        M, cfg = new_match(seed)
        A, Bm = M.mechs[0], M.mechs[1]
        for x in M.mechs[2:]:
            x.alive = False
        M.alive_count = 2
        pa, pb, ang = find_spot(W, rng, args.dist)
        place(M, A, pa, ang)
        place(M, Bm, pb, ang + math.pi)
        mk_weapons(M, A, args.loadout.split("+"))
        mk_weapons(M, Bm, args.enemy_loadout.split("+"))
        bot = BuiltinBot(args.tier, W, cfg, seed, 1)
        S = st.WorldState({"type": "hello", "slot": 0, "seed": seed, "config": cfg}, _arena())
        keep = args.keep if args.keep is not None else (28.0 if "lightning" in args.loadout else None)
        mover = Mover(args.self_move, random.Random(seed + 3), ang, keep)
        intent = st.Intent(mode="engage", target_id=Bm.id)
        while M.t < args.secs and A.alive and Bm.alive:
            if M.tick % 2 == 0:
                mover.axis = math.atan2(Bm.pos[1] - A.pos[1], Bm.pos[0] - A.pos[0])
                mover.dist = math.hypot(Bm.pos[0] - A.pos[0], Bm.pos[1] - A.pos[1])
                a, dt, obs, out = ours_decide(S, M, A, intent, mover if args.self_move != "stand" else None)
                M.apply_action(A, a)
                vis = M._senses.visible_set([x for x in M.mechs if x.alive], want_items=set())
                bo = build_obs(M, Bm, vis[Bm.id], full=False)
                M.apply_action(Bm, bot.act(bo, None))
            M.step()
        r = "win" if (A.alive and not Bm.alive) else ("loss" if (Bm.alive and not A.alive) else "draw")
        wins += r == "win"
        losses += r == "loss"
        draws += r == "draw"
        rows.append({"seed": seed, "result": r, "t": round(M.t, 1), "hp_a": round(A.hp), "hp_b": round(Bm.hp)})
    print(f"duel ours[{args.loadout}] vs {args.tier}[{args.enemy_loadout}] @ {args.dist} m: "
          f"win {wins} loss {losses} draw {draws}  ({args.reps} reps)")
    if args.verbose:
        for r in rows:
            print("  ", r)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hitrate")
    h.add_argument("--patterns", default="stand,walk,strafe,juke,jump")
    h.add_argument("--dists", default="40,100,180")
    h.add_argument("--loadout", default="gun")
    h.add_argument("--self-move", default="stand")
    h.add_argument("--reps", type=int, default=3)
    h.add_argument("--secs", type=float, default=12.0)
    h.add_argument("--out", default=None)
    d = sub.add_parser("duel")
    d.add_argument("--tier", default="expert")
    d.add_argument("--loadout", default="gun")
    d.add_argument("--enemy-loadout", default="gun")
    d.add_argument("--dist", type=float, default=100.0)
    d.add_argument("--self-move", default="strafe")
    d.add_argument("--reps", type=int, default=10)
    d.add_argument("--keep", type=float, default=None, help="our legs hold this range (default: 28 m with lightning, else none)")
    d.add_argument("--secs", type=float, default=60.0)
    d.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    if a.cmd == "hitrate":
        hitrate(a)
    else:
        duel(a)


if __name__ == "__main__":
    main()
