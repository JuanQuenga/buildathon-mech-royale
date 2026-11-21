"""Policy v2 ("apex"): objective layers over the base brain. OWNER: integrator.

Every tweak of the base fight loop scored 4.9-5.4 officially, so these layers change WHAT the match is played for,
not how one duel is fought. Each is one brain switch (default off) and they compose:

  drop_king   supply drops are a second life (full HP + full energy + 3 cubes). The base only considered a drop when
              no fight was on, which is never once the squad hunts us. Here the drop is an objective from the moment it
              is called: run to it while fighting, then capture it UNDER FIRE by circling inside the ring.
  vacuum      power cubes (+4 % HP and damage each, upgrades at 1/3/6/10) are collected at once, boosting, whatever is
              shooting; the base grabbed them only when nobody had hit us for 3 s.
  duck        a visible mech charging a laser at us: sprint behind the nearest hard cover, or across its aim line.
  roof        fight from a tall roof (see _roof): ground pursuers lose line of sight when we step back from the edge.

refine() runs after the base brain and may replace its Intent. The zone always wins.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from . import brain as B
from .state import Intent, Threats, WorldState, dist2d, unit2, yaw_to


def _stat(am: Dict[str, Any], key: str) -> None:
    s = am.setdefault("stat", {})
    s[key] = s.get(key, 0) + 1


def refine(state: WorldState, threats: Threats, it: Intent, m: Dict[str, Any]) -> Intent:
    P = B.P
    am = m.setdefault("apex", {})
    for ev in state.events:
        ty = ev.get("type")
        if ty == "drop":
            am["drops_got"] = am.get("drops_got", 0) + 1
            am.setdefault("drop_t", []).append(round(state.t, 1))
        elif ty == "pickup":
            am["vac_last_pick"] = state.t
    zp = m.get("zp") or {}
    out: Optional[Intent] = None
    if P["duck"]:
        out = _duck(state, threats, it, m, am)
    if out is None and P["drop_king"]:
        out = _drop(state, threats, it, m, am, zp, ring_only=True)
    if out is None and P["vacuum"]:
        out = _vacuum(state, threats, it, m, am, zp, 30.0)
    if out is None and P["drop_king"]:
        out = _drop(state, threats, it, m, am, zp, ring_only=False)
    if out is None and P["vacuum"]:
        out = _vacuum(state, threats, it, m, am, zp, float(P["vac_reach"]))
    if out is None and P["roof"]:
        out = _roof(state, threats, it, m, am, zp)
    if out is None:
        return it
    out.spare_ids = it.spare_ids
    if out.face is None:
        out.face = it.face
    m["mode"] = out.mode
    m["last_reason"] = out.reason
    m["modes"]["apex"] = m["modes"].get("apex", 0) + 1
    return out


def _target_id(state: WorldState, it: Intent, m: Dict[str, Any]) -> Optional[int]:
    ft = (m.get("fight") or {}).get("target")
    if ft is not None:
        return ft.id
    if it.target_id is not None and it.mode in ("engage", "retreat", "rotate"):
        return it.target_id
    return None


# ----------------------------------------------------------------------------- supply drops
def _drop(state: WorldState, threats: Threats, it: Intent, m, am, zp, ring_only: bool) -> Optional[Intent]:
    drops = state.obs.get("drops") or []
    if not drops:
        return None
    P = B.P
    walk = max(1.0, state.stat("walk_speed", 11.7))
    z = state.zone
    best = None
    for d in drops:
        pos = d.get("pos")
        if not pos or len(pos) < 2:
            continue
        p = (float(pos[0]), float(pos[1]), float(pos[2]) if len(pos) > 2 else float(state.pos[2]))
        dist = dist2d(p, state.pos)
        lands = float(d.get("lands_in", 0) or 0)
        eta = dist * 1.2 / walk
        if dist > 40.0:
            try:
                e2 = B._eta(state, p)
                if e2 == e2 and e2 != math.inf:
                    eta = max(eta, min(e2, 3.0 * eta + 10.0))
            except Exception:
                pass
        hurt = state.hp < 0.5 * max(1.0, state.max_hp)
        if eta > (P["dk_max_eta_hurt"] if hurt else P["dk_max_eta"]):
            continue
        cap_s = float(d.get("capture_s", 4.0) or 4.0)
        c, r = state.zone_circle_at(state.t + max(eta, lands) + cap_s + 2.0)
        if dist2d(p, c) > r - 3.0:
            continue                      # the ring will be outside the circle before we could finish
        if best is None or eta < best[0]:
            best = (eta, d, p, lands)
    if best is None:
        return None
    eta, d, p, lands = best
    R = float(d.get("radius", 8.0) or 8.0)
    dist = dist2d(p, state.pos)
    tid = _target_id(state, it, m)
    face = it.face
    if tid is not None:
        tr = state.tracks.get(tid)
        if tr is not None:
            face = yaw_to(state.pos, tr.pos)
    in_ring = dist < R - 2.2 and abs(state.pos[2] - p[2]) < 10.0
    if in_ring:
        # circle inside the ring: capture needs 4 s alone in it, and lateral movement is what keeps us alive
        rx, ry = state.pos[0] - p[0], state.pos[1] - p[1]
        r = math.hypot(rx, ry)
        sgn = am.setdefault("ring_sgn", 1.0 if (state.tick // 7) % 2 else -1.0)
        r_t = 0.40 * R
        if r < 0.4:
            mv = (math.cos(state.t * 3.0), math.sin(state.t * 3.0))
        else:
            ux, uy = rx / r, ry / r
            k = max(-1.0, min(1.0, (r_t - r) / 1.5))
            mv = unit2(-uy * sgn + 1.4 * k * ux, ux * sgn + 1.4 * k * uy)
        # somebody else in the ring freezes the clock: shoot it
        for e in threats.enemies:
            if e.kind == "mech" and e.visible and dist2d(e.pos, p) < R + 1.5:
                tid = e.id
                face = yaw_to(state.pos, e.pos)
                break
        _stat(am, "ring")
        return Intent(mode="engage" if tid is not None else "capture", goal=p, target_id=tid, desired_range=None,
                      urgency=0.5, face=face, allow_fire=True, loot_id=d.get("id"), raw_move=mv, raw_boost=False,
                      reason=f"ring {d.get('id')} prog {float(d.get('progress', 0) or 0):.1f}")
    if ring_only:
        return None
    if zp.get("must_go"):
        # only when the drop is itself inside the next circle and we can be there before the edge passes us
        if z and dist2d(p, z["next_center"]) > float(z["next_radius"]) - 5.0:
            return None
        if state.t + eta + 3.0 > float(zp.get("deadline", 1e9)):
            return None
    if lands > eta + float(P["dk_lead_s"]):
        return None                       # too early: carry on, we leave when the trip takes as long as the fall
    _stat(am, "run")
    return Intent(mode="engage" if tid is not None else "capture", goal=p, target_id=tid, desired_range=None,
                  urgency=0.75, face=face, allow_fire=True, loot_id=d.get("id"), weave=dist > 14.0,
                  reason=f"drop run {d.get('id')} eta {eta:.0f} lands {lands:.0f}")


# ----------------------------------------------------------------------------- cubes
def _vacuum(state: WorldState, threats: Threats, it: Intent, m, am, zp, reach: float) -> Optional[Intent]:
    P = B.P
    ncub = int(state.me.get("cubes", 0) or 0)
    if ncub >= int(P["vac_max_cubes"]) or zp.get("must_go"):
        return None
    bl = m["blacklist"]
    best = None
    for r in m["items"].values():
        if r["type"] != "cube" or bl.get(r["id"], -1e9) > state.t:
            continue
        if abs(r["pos"][2] - state.pos[2]) > 6.0:
            continue
        dd = dist2d(r["pos"], state.pos)
        if dd > reach or not B._inside_zone_soon(state, r["pos"], 2.0):
            continue
        if best is None or dd < best[0]:
            best = (dd, r)
    if best is None:
        return None
    dd, c = best
    # watchdog: a cube we cannot get to (ledge, roof edge, pit) must not hold us
    v = am.get("vac")
    if v is None or state.t - v["seen"] > 1.0 or am.get("vac_last_pick", -1e9) > v["t0"]:
        v = am["vac"] = {"t0": state.t, "seen": state.t, "d0": dd}
    v["seen"] = state.t
    if state.t - v["t0"] > 4.0 + v["d0"] / 5.0:
        for r in m["items"].values():
            if r["type"] == "cube" and dist2d(r["pos"], c["pos"]) < 12.0:
                bl[r["id"]] = state.t + 25.0
        am["vac"] = None
        _stat(am, "vac_giveup")
        return None
    tid = _target_id(state, it, m)
    face = it.face
    if tid is not None:
        tr = state.tracks.get(tid)
        if tr is not None:
            face = yaw_to(state.pos, tr.pos)
    _stat(am, "vac")
    return Intent(mode="engage" if tid is not None else "loot", goal=tuple(c["pos"]), loot_id=c["id"], target_id=tid,
                  desired_range=None, urgency=0.75, face=face, allow_fire=True, weave=dd > 14.0,
                  reason=f"vacuum {c['id']} {dd:.0f}m")


# ----------------------------------------------------------------------------- laser duck
def _duck(state: WorldState, threats: Threats, it: Intent, m, am) -> Optional[Intent]:
    worst = None
    for e in threats.enemies:
        if e.kind != "mech" or not (e.charging and e.visible and e.los and e.facing_me):
            continue
        ct = float(getattr(e, "charge_t", 0.0) or 0.0)
        if worst is None or ct > worst[0]:
            worst = (ct, e)
    if worst is None:
        am["duck"] = None
        return None
    P = B.P
    ct, e = worst
    dk = am.get("duck")
    if dk is None or dk["id"] != e.id or state.t - dk["t"] > 0.6:
        spot = None
        if state.arena is not None:
            try:
                spot = state.arena.nearest_cover(state.pos, tuple(e.pos), float(P["duck_reach"]),
                                                 cubes=state.me.get("cubes", 0) or 0, budget_ms=2.0)
            except Exception:
                spot = None
        dk = am["duck"] = {"id": e.id, "t": state.t, "spot": spot}
    spot = dk["spot"]
    tid = _target_id(state, it, m)
    if tid is None:
        tid = e.id
    if spot is not None and dist2d(spot, state.pos) > 0.8:
        mv = unit2(spot[0] - state.pos[0], spot[1] - state.pos[1])
        _stat(am, "duck_cover")
        why = "duck cover"
    else:
        # no cover in reach: sprint across its aim line, the way we already move
        back = math.atan2(state.pos[1] - e.pos[1], state.pos[0] - e.pos[0])
        sx, sy = -math.sin(back), math.cos(back)
        sgn = 1.0 if (state.vel[0] * sx + state.vel[1] * sy) >= 0 else -1.0
        mv = (sx * sgn, sy * sgn)
        _stat(am, "duck_side")
        why = "duck side"
    return Intent(mode="engage", goal=None, target_id=tid, desired_range=None, urgency=0.6,
                  face=yaw_to(state.pos, e.pos), allow_fire=True, raw_move=mv, raw_boost=state.energy > 10.0,
                  reason=f"{why} {e.id}")


# ----------------------------------------------------------------------------- roof
# Flat roofs 11-40 m above the street with a spot >= `depth` m from every edge: (x, y, z, depth), from the baked map
# (tools: flood fill over Arena.G - Arena.H, standable cells). Checked against Arena.surface at run time.
ROOFS = (
    (-65, 262, 12.8, 34), (-152, -101, 14.7, 33), (28, 267, 13.6, 31), (-96, -301, 14.9, 30), (50, -303, 13.1, 26), (457, -234, 23.5, 26),
    (190, 291, 25.2, 23), (272, 229, 24.2, 21), (-42, 340, 17.4, 21), (22, -222, 16.5, 20), (265, 125, 25.4, 20), (402, 239, 26.0, 20),
    (165, -146, 25.7, 18), (256, 12, 22.5, 17), (263, 305, 30.2, 17), (7, -109, 15.2, 16), (-81, -47, 14.7, 16), (536, 233, 19.9, 16),
    (538, 147, 25.7, 15), (54, -108, 18.6, 14), (128, 102, 23.2, 14), (471, 162, 23.5, 14), (132, 169, 20.5, 14), (105, 271, 17.1, 14),
    (362, 313, 25.0, 14), (-47, -204, 19.3, 13), (329, 16, 22.8, 13), (-11, 105, 18.0, 13), (53, 100, 23.8, 13), (229, 191, 28.3, 13),
    (201, 4, 24.4, 12), (408, 48, 20.9, 12), (168, 65, 16.9, 12), (357, 207, 23.6, 12), (56, 207, 36.8, 12), (117, 357, 13.1, 12),
    (390, -252, 17.4, 11), (511, -201, 20.3, 11), (-54, 90, 12.6, 11), (179, 105, 34.7, 11), (202, 109, 16.1, 11), (110, 183, 16.0, 11),
    (26, 162, 11.7, 11), (180, 174, 28.3, 11), (401, 335, 29.0, 11), (326, -252, 12.8, 10), (136, -139, 44.1, 10), (452, 20, 17.5, 10),
    (492, 51, 20.9, 10), (-109, 63, 10.8, 10), (372, 94, 23.7, 10), (-31, 182, 18.0, 10), (338, 327, 19.9, 10), (295, 332, 38.1, 10),
)
_RING8 = tuple((math.cos(k * math.pi / 4.0), math.sin(k * math.pi / 4.0)) for k in range(8))


def _on_roof(ar, x: float, y: float, z: float, margin: float) -> bool:
    """(x, y) is on the roof level z and at least `margin` m from its edge in 8 directions."""
    try:
        if abs(ar.surface(x, y) - z) > 1.0:
            return False
        for cx, cy in _RING8:
            if abs(ar.surface(x + cx * margin, y + cy * margin) - z) > 1.0:
                return False
        return True
    except Exception:
        return False


def _roof_pick(state: WorldState, am) -> Optional[Tuple[float, float, float, float]]:
    """Nearest usable roof that stays inside the circle for a while (sticky)."""
    ar = state.arena
    bad = am.setdefault("roof_bad", {})
    t = state.t
    c60, r60 = state.zone_circle_at(t + 45.0)
    z = state.zone
    cur = am.get("roof_cur")
    best, bs = None, 1e18
    for rf in ROOFS:
        if bad.get(rf[:2], -1e9) > t:
            continue
        if dist2d(rf, c60) > r60 - 12.0:
            continue
        if z and t > float(z.get("shrink_start", 1e9)) - 30.0 and dist2d(rf, z["next_center"]) > float(z["next_radius"]) - 12.0:
            continue
        d = dist2d(rf, state.pos)
        if d > float(B.P["roof_max_m"]):
            continue
        sc = d - 2.0 * rf[3] - (60.0 if cur is not None and cur[:2] == rf[:2] else 0.0)
        if z:
            sc += 0.25 * dist2d(rf, z["next_center"])
        if sc < bs:
            try:
                if abs(ar.surface(rf[0], rf[1]) - rf[2]) > 1.5:
                    continue
            except Exception:
                continue
            best, bs = rf, sc
    return best


def _roof(state: WorldState, threats: Threats, it: Intent, m, am, zp) -> Optional[Intent]:
    """Roof fortress: once armed, climb the nearest big flat roof and fight from it. Stepping back from the edge hides
    us from everything on the street below, so we can regenerate between volleys (45 HP/s after 5 s); pursuers have to
    jet up one by one. Fight at the edge facing the target, heal at the centre."""
    P = B.P
    ar = state.arena
    if ar is None or not getattr(ar, "ok_nav", False) or zp.get("must_go"):
        return None
    if state.mode_guess == "ffa" and not P["roof_ffa"]:
        return None
    kinds = state.weapon_kinds()
    if (kinds + [None, None])[1] is None and state.t < float(P["roof_unarmed_t"]):
        return None
    rf = _roof_pick(state, am)
    if rf is None:
        am["roof_cur"] = None
        return None
    if am.get("roof_cur") is None or am["roof_cur"][:2] != rf[:2]:
        am["roof_cur"] = rf
        am["roof_t0"] = state.t
        am["roof_d0"] = dist2d(rf, state.pos)
    cx, cy, rz, depth = rf
    x, y, zz = state.pos
    tid = _target_id(state, it, m)
    hpf = state.hp / max(1.0, state.max_hp)
    on = abs(zz - rz) < 2.5 and _on_roof(ar, x, y, rz, 1.0)
    if not on:
        # not there yet: give up on a roof we cannot climb in reasonable time
        if state.t - am["roof_t0"] > 25.0 + am["roof_d0"] / 5.0:
            am.setdefault("roof_bad", {})[rf[:2]] = state.t + 90.0
            am["roof_cur"] = None
            _stat(am, "roof_giveup")
            return None
        _stat(am, "roof_go")
        face = it.face
        if tid is not None and state.tracks.get(tid) is not None:
            face = yaw_to(state.pos, state.tracks[tid].pos)
        return Intent(mode="engage" if tid is not None else "rotate", goal=(float(cx), float(cy), float(rz)), target_id=tid,
                      desired_range=None, urgency=0.5, face=face, allow_fire=True, reason=f"roof go {cx},{cy}")
    am["roof_t0"] = state.t          # on it: the give-up clock only runs while travelling
    am["roof_on_s"] = am.get("roof_on_s", 0.0) + state.dt
    margin = 3.2
    vis = [e for e in threats.enemies if e.kind == "mech" and e.visible and (state.t - e.last_seen_t) < 1.0]
    shooters = [e for e in vis if e.los]
    hit_recent = state.recent_damage(2.0) > 0
    # heal at the centre when hurt; if they still hit us there the roof is not cover (someone climbed up / far sniper)
    heal = am.get("roof_heal", False)
    if not heal and hpf < float(P["roof_heal_below"]) and state.t >= am.get("roof_noheal_until", -1e9):
        heal = True
        am["roof_heal_t"] = state.t
    if heal and hpf >= 0.92:
        heal = False
    dc = math.hypot(x - cx, y - cy)
    if heal and dc < 4.0 and hit_recent and state.t - am.get("roof_heal_t", state.t) > 4.0:
        heal = False
        am["roof_noheal_until"] = state.t + 12.0
        _stat(am, "roof_heal_fail")
    am["roof_heal"] = heal
    if heal or not vis:
        mv = (0.0, 0.0)
        if dc > 2.0:
            mv = unit2(cx - x, cy - y)
        _stat(am, "roof_heal" if heal else "roof_wait")
        fire = not heal or (hit_recent and dc < 4.0)
        return Intent(mode="heal" if heal else "hold", goal=(float(cx), float(cy), float(rz)),
                      target_id=tid if fire else None, desired_range=None, urgency=0.4, face=it.face, allow_fire=fire,
                      raw_move=mv, raw_boost=False, reason="roof heal" if heal else "roof wait")
    # fight: walk toward the target until the edge margin stops us, strafe along the edge
    tgt = None
    if tid is not None:
        tgt = next((e for e in vis if e.id == tid), None)
    if tgt is None:
        tgt = min(shooters or vis, key=lambda e: e.dist)
    dx, dy = tgt.pos[0] - x, tgt.pos[1] - y
    dn = math.hypot(dx, dy) or 1.0
    ux, uy = dx / dn, dy / dn
    if state.t >= am.get("roof_flip_t", 0.0):
        am["roof_sgn"] = -am.get("roof_sgn", 1.0)
        am["roof_flip_t"] = state.t + 3.0 + ((state.tick * 7919) % 21) / 10.0
    sg = am.get("roof_sgn", 1.0)
    tx, ty = -uy * sg, ux * sg
    fwd = 0.0 if (tgt.los and dn < 150.0) else 1.0
    step = 2.5
    mv = None
    for (ax, ay) in ((ux * fwd + tx, uy * fwd + ty), (tx, ty), (-tx, -ty), (cx - x, cy - y)):
        vx, vy = unit2(ax, ay)
        if (vx or vy) and _on_roof(ar, x + vx * step, y + vy * step, rz, margin):
            mv = (vx, vy)
            if (ax, ay) == (-tx, -ty):
                am["roof_sgn"] = -sg
            break
    if mv is None:
        mv = unit2(cx - x, cy - y)
    _stat(am, "roof_fight")
    return Intent(mode="engage", goal=None, target_id=tgt.id, desired_range=None, urgency=0.5,
                  face=yaw_to(state.pos, tgt.pos), allow_fire=True, raw_move=mv, raw_boost=False,
                  reason=f"roof fight {tgt.id}")


def summary(m: Dict[str, Any]) -> Dict[str, Any]:
    am = m.get("apex") or {}
    return {"stat": am.get("stat"), "drops": am.get("drops_got", 0), "drop_t": am.get("drop_t")}
