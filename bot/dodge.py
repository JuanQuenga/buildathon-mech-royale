"""Predictive bullet dodge (policy v2, brain switch `dodge_plan`). OWNER: integrator.

Official movement tests say reactive dodging is worth about one point (standing still 4.19, speed capped at 6 m/s
4.77, no strafe but full-speed dodging 5.25, base 5.34), and gun bullets are ~90 % of the damage we take in the sim.
The legacy dodge sums one sideways vector per threatening bullet, assuming we keep our velocity. This planner instead
rolls the ground-movement model forward for a fan of candidate moves and tests every visible bullet against each
trajectory, then takes the candidate that is hit least (ties: closest to what navigation wanted).

plan(state, want) -> (move_xy, boost) or None (None = navigation's own move is already safe / nothing to dodge).
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from .state import WorldState

DT = 0.05
STEPS = 16                      # 0.8 s horizon
_DIRS = tuple((math.cos(k * math.pi / 8.0), math.sin(k * math.pi / 8.0)) for k in range(16))


def _roll(x: float, y: float, vx: float, vy: float, tx: float, ty: float, acc_dt: float) -> List[Tuple[float, float]]:
    """Positions at k*DT (k = 0..STEPS) while accelerating toward the target velocity (tx, ty)."""
    out = [(x, y)]
    for _ in range(STEPS):
        dx, dy = tx - vx, ty - vy
        n = math.hypot(dx, dy)
        if n > acc_dt:
            vx += dx / n * acc_dt
            vy += dy / n * acc_dt
        else:
            vx, vy = tx, ty
        x += vx * DT
        y += vy * DT
        out.append((x, y))
    return out


def plan(state: WorldState, want: Optional[Tuple[float, float]], allow_boost: bool = True, stats=None):
    me = state.me
    if not me.get("grounded", True):
        return None
    projs = state.obs.get("projectiles") or []
    if not projs:
        return None
    x, y, z = state.pos
    cubes = float(me.get("cubes", 0) or 0)
    sc = 1.0 + 0.05 * cubes
    R = max(state.stat("radius", 2.5), 2.5 * sc) + 0.3          # body radius + bullet radius
    H = max(state.stat("height", 9.0), 9.0 * sc)
    walk = max(1.0, state.stat("walk_speed", 11.7))
    boost_v = max(walk, state.stat("boost_speed", 19.5))
    acc_dt = state.stat("ground_accel", 58.5) * DT
    charging = False
    for w in me.get("weapons") or []:
        if w and w.get("kind") == "laser" and float(w.get("charge", 0) or 0) > 0:
            charging = True
    if charging:
        mult = state.stat("charge_move_mult", 0.5)
        walk *= mult
        boost_v *= mult
    gun_dmg = float(state.cfg.get("weapons", {}).get("gun", {}).get("damage", 45.0))
    npc_dmg = float(state.cfg.get("npc", {}).get("damage", 25.0))
    horizon = STEPS * DT
    reach = R + 1.2 + boost_v * horizon
    bl = []
    for pr in projs:
        kind = pr.get("kind", "gun")
        if kind == "mortar":
            continue
        try:
            px, py, pz = pr["pos"]
            vx, vy, vz = pr["vel"]
        except Exception:
            continue
        sh = math.hypot(vx, vy)
        if sh < 5.0:
            continue
        ux, uy = vx / sh, vy / sh
        s = (x - px) * ux + (y - py) * uy
        if s < -R:
            continue                                  # already past us
        t0 = s / sh
        if t0 > horizon + 0.15:
            continue
        lat = abs((x - px) * uy - (y - py) * ux)
        if lat > reach:
            continue
        bz = pz + vz * t0
        if bz < z - 2.0 or bz > z + H + 2.0:
            continue
        bl.append((px, py, pz, vz, sh, ux, uy, npc_dmg if kind == "npc" else gun_dmg))
        if len(bl) >= 14:
            break
    if not bl:
        return None
    vx0, vy0 = float(state.vel[0]), float(state.vel[1])
    cands = []
    if want is not None and (want[0] or want[1]):
        n = math.hypot(want[0], want[1])
        wx, wy = want[0] / n, want[1] / n
        cands.append((wx, wy, walk, False, 0.0))
    else:
        wx = wy = 0.0
        cands.append((0.0, 0.0, 0.0, False, 0.0))
    for dx, dy in _DIRS:
        pen = 2.0 * (1.0 - (dx * wx + dy * wy)) if (wx or wy) else 1.0
        cands.append((dx, dy, walk, False, 0.5 + pen))
    if wx or wy:
        cands.append((0.0, 0.0, 0.0, False, 3.0))
    use_boost = allow_boost and state.energy > 25.0 and not charging
    if use_boost:
        for dx, dy in _DIRS[::2]:
            pen = 2.0 * (1.0 - (dx * wx + dy * wy)) if (wx or wy) else 1.0
            cands.append((dx, dy, boost_v, True, 3.5 + pen))
    best, best_cost = None, 1e18
    first_cost = None
    zlo, zhi = z - 0.3, z + H + 0.3
    inv_dt = 1.0 / DT
    for ci, (dx, dy, v, bst, pen) in enumerate(cands):
        tr = _roll(x, y, vx0, vy0, dx * v, dy * v, acc_dt)
        cost = pen
        for (px, py, pz, vz, sh, ux, uy, dmg) in bl:
            # time of closest approach along the bullet's horizontal path, refined against our moving position
            tau = ((x - px) * ux + (y - py) * uy) / sh
            X, Y = x, y
            for _ in range(2):
                if tau <= 0.0:
                    X, Y = x, y
                else:
                    f = tau * inv_dt
                    k = int(f)
                    if k >= STEPS:
                        X, Y = tr[STEPS]
                    else:
                        a, b = tr[k], tr[k + 1]
                        f -= k
                        X, Y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
                tau = ((X - px) * ux + (Y - py) * uy) / sh
            if tau < -0.02:
                continue
            bz = pz + vz * tau
            if bz < zlo or bz > zhi:
                continue
            miss = abs((X - px) * uy - (Y - py) * ux)
            if miss < R:
                cost += dmg
            elif miss < R + 1.0:
                cost += 0.5 * dmg * (1.0 - (miss - R))
        if ci == 0:
            first_cost = cost
            if cost <= 0.01:
                return None                           # navigation's own move is safe
        if cost < best_cost:
            best, best_cost = (dx, dy, bst), cost
    if best is None or first_cost is None or best_cost >= first_cost - 1.0:
        return None
    return (best[0], best[1]), best[2]
