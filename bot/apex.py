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

import os
import sys

from . import brain as B
from .state import Intent, Threats, WorldState, dist2d, unit2, yaw_to


_LOG = bool(os.environ.get("MECH_APEXLOG"))


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
            if P["dk_last_stand"]:
                m["last_stand"] = True
        elif ty == "pickup":
            am["vac_last_pick"] = state.t
    zp = m.get("zp") or {}
    out: Optional[Intent] = None
    if P["phoenix"]:
        out = _phoenix(state, threats, it, m, am, zp)
    if out is None and P["pet"]:
        out = _pet(state, threats, it, m, am, zp)
    if out is None and P["bank"]:
        out = _bank(state, threats, it, m, am, zp)
    if out is None and P["duck"]:
        out = _duck(state, threats, it, m, am)
    if out is None and P["corner"]:
        out = _corner(state, threats, it, m, am, zp)
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
    if _LOG and state.tick % 20 == 0:
        try:
            bk = am.get("bank") or {}
            wl = {i: round(w.get("hpf", 0), 2) for i, w in (bk.get("W") or {}).items()}
            vs = [(e.id, round(e.dist), round((e.hp or 0) / max(1.0, e.max_hp or 1400), 2), int(e.los))
                  for e in threats.enemies if e.kind == "mech" and e.visible]
            print(f"[apex] t={state.t:.0f} hp={state.hp:.0f} k={state.kills} ph={bk.get('phase')} W={wl} "
                  f"out={(out.reason if out is not None else 'base:' + it.mode + ' ' + it.reason)[:40]} vis={vs}", file=sys.stderr)
        except Exception:
            pass
    if out is None:
        if P["bank"] and am.get("bank_spare"):
            it.spare_ids = list(set(it.spare_ids or []) | set(am["bank_spare"]))
        if P["pet"] and am.get("pet_spare"):
            it.spare_ids = list(set(it.spare_ids or []) | set(am["pet_spare"]))
        return it
    if not out.spare_ids:
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


def _drift_intent(state: WorldState, it: Intent, goal, why: str) -> Optional[Intent]:
    """The base brain is duelling a target: keep that duel (strafe, range, fire) and drift toward `goal`."""
    if it.mode != "engage" or it.target_id is None or not it.desired_range or it.goal is not None:
        return None
    tr = state.tracks.get(it.target_id)
    if tr is None or state.t - tr.last_seen_t > 1.5:
        return None
    dx, dy = goal[0] - state.pos[0], goal[1] - state.pos[1]
    n = math.hypot(dx, dy)
    if n < 1.0:
        return None
    return Intent(mode="engage", goal=None, target_id=it.target_id, desired_range=it.desired_range, urgency=it.urgency,
                  face=it.face, allow_fire=True, avoid=it.avoid, drift=(dx / n, dy / n), reason=why)


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
        lim = P["dk_max_eta_hurt"] if hurt else P["dk_max_eta"]
        if am.get("dk_commit") == d.get("id"):
            lim = P["dk_max_eta_hurt"] + 20.0      # once on the way stay on the way (no flip-flop as HP crosses 50 %)
        if eta > lim:
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
        am["dk_commit"] = d.get("id")
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
    hpf = state.hp / max(1.0, state.max_hp)
    close = dist < float(P["dk_sprint_m"]) and lands < 3.0
    if P["dk_drift"] and not close and not (hpf < 0.45 and lands < eta):
        # fight our way there: the duel goes on (kills, lateral speed), biased toward the drop
        di = _drift_intent(state, it, p, f"drop drift {d.get('id')} eta {eta:.0f} lands {lands:.0f}")
        if di is not None:
            _stat(am, "drift")
            am["dk_commit"] = d.get("id")
            di.loot_id = d.get("id")
            return di
    if lands > eta + float(P["dk_lead_s"]):
        return None                       # too early: carry on, we leave when the trip takes as long as the fall
    _stat(am, "run")
    am["dk_commit"] = d.get("id")
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
    if P["vac_drift"] and dd > 25.0:
        di = _drift_intent(state, it, c["pos"], f"vacuum drift {c['id']} {dd:.0f}m")
        if di is not None:
            _stat(am, "vac_drift")
            v["t0"] = max(v["t0"], state.t - 2.0)      # the give-up clock only runs on the direct run
            di.loot_id = c["id"]
            return di
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


# ----------------------------------------------------------------------------- phoenix (heal cycle)
def _phoenix(state: WorldState, threats: Threats, it: Intent, m, am, zp) -> Optional[Intent]:
    """Heal cycle, the way today's 6.2-6.4 bots do it in the live Top-16 Showdown (hamsters, TigerTown27, Vice City:
    3,000-4,000 HP regenerated per match in 5-8 episodes, 2/3 of all damage they take; we regenerate a few hundred).
    Their episodes start exactly regen_delay after their last hit taken AND their last hit dealt, with no enemy in line
    of sight although the nearest stands 55-80 m away, and run to full HP while they stand still.
    So below px_low, when a spot hidden from every mech we know of is in reach: go there (firing only at mechs close
    enough to hit us anyway), then stand still, silent and not shooting until px_high. If somebody walks into a line
    on us the reset is over: fight on with the base brain and try again later from the new geometry."""
    P = B.P
    px = am.setdefault("px", {"on": False, "t0": 0.0, "hp0": 0.0, "spot": None, "n": 0, "gain": 0.0, "done": 0,
                              "prev_hp": state.hp, "retry_t": -1e9, "seen_since": None, "probe_t": -1e9})
    t = state.t
    hpf = state.hp / max(1.0, state.max_hp)
    if px["on"] and state.hp > px["prev_hp"]:
        px["gain"] += state.hp - px["prev_hp"]
    px["prev_hp"] = state.hp
    if zp.get("must_go") or (state.mode_guess == "ffa" and not P["px_ffa"]):
        px["on"] = False
        return None
    mechs = [e for e in threats.enemies if e.kind == "mech" and t - e.last_seen_t < float(P["px_mem_s"])]
    if state.mode_guess != "ffa" and P["px_hunters_only"]:
        # practice squad: only the mechs hunting us shoot; a passive house bot wandering past is not a reason to
        # leave cover (sim: resets were abandoned for passives; 5-16 % ran to full HP)
        hs = set(getattr(threats, "hunters", None) or []) | set(threats.attackers or [])
        hm = [e for e in mechs if e.id in hs or (e.facing_me and e.dist < 120.0)]
        if hm:
            mechs = hm
    seeing = [e for e in mechs if e.visible and e.los and t - e.last_seen_t < 0.6]
    killable = set(getattr(threats, "killable", None) or [])
    threats_pos = [tuple(e.pos) for e in sorted(mechs, key=lambda e: e.dist)[:4]]

    def find_spot():
        if not threats_pos or state.arena is None:
            return None
        c = None
        # hidden from the four nearest mechs if possible, else from the three / two nearest (the far ones hit less)
        for k in (4, 3, 2):
            if len(threats_pos) < k and k != 4:
                continue
            try:
                c = state.arena.nearest_cover(state.pos, threats_pos[:k], float(P["px_reach"]),
                                              cubes=state.me.get("cubes", 0) or 0, budget_ms=2.0)
            except Exception:
                c = None
            if c is not None and not (B._inside_zone_soon(state, c, 6.0) and B._in_safe_future(state, c)):
                c = None
            if c is not None or len(threats_pos) <= 2 or k <= int(P["px_min_hide"]):
                break
        return c

    if not px["on"] and P["px_anchor"] and float(P["px_low"]) <= hpf < float(P["px_anchor_hp"]) and mechs:
        # fight where a reset is possible: while duelling drift toward the nearest spot hidden from the mechs around us
        an = px.setdefault("anchor", {"t": -1e9, "spot": None})
        if t - an["t"] > 1.5:
            an["t"] = t
            try:
                an["spot"] = state.arena.nearest_cover(state.pos, threats_pos[:3], float(P["px_anchor_m"]),
                                                       cubes=state.me.get("cubes", 0) or 0, budget_ms=2.0) \
                    if state.arena is not None else None
            except Exception:
                an["spot"] = None
            if an["spot"] is not None and not B._inside_zone_soon(state, an["spot"], 6.0):
                an["spot"] = None
        sp = an["spot"]
        if sp is not None and dist2d(sp, state.pos) > 22.0:
            di = _drift_intent(state, it, sp, f"anchor {dist2d(sp, state.pos):.0f}m")
            if di is not None:
                _stat(am, "px_anchor")
                return di
    if not px["on"]:
        if hpf >= float(P["px_low"]) or t < px["retry_t"] or t - px["probe_t"] < 1.0:
            return None
        if any(e.id in killable and e.los for e in seeing):
            return None                               # finish the kill first
        if not mechs:
            return None                               # nobody around: the base brain's own heal mode does this
        px["probe_t"] = t
        spot = find_spot()
        if spot is None:
            _stat(am, "px_nocover")
            return None
        if dist2d(spot, state.pos) > float(P["px_near_m"]) and any(e.dist < float(P["px_press_m"]) for e in seeing):
            _stat(am, "px_pressed")
            return None                               # a mech on top of us and the cover is far: fighting on costs less
        px.update(on=True, t0=t, hp0=state.hp, spot=spot, seen_since=None, moved=False)
        px["n"] += 1
        _stat(am, "px_start")
    spot = px["spot"]
    d = dist2d(spot, state.pos)
    if hpf >= float(P["px_high"]):
        px["on"] = False
        px["done"] += 1
        _stat(am, "px_done")
        return None
    at_spot = d < 3.0
    if at_spot and not seeing and P["px_relocate"] and not px.get("moved") and threats_pos and state.arena is not None:
        # out of sight: do not stay where they last saw us go. One more hop to a second hidden spot, itself reached
        # without crossing anybody's line of sight; the hunters walk to the last place they saw us.
        px["moved"] = True
        try:
            ar = state.arena
            tx = sum(p[0] for p in threats_pos) / len(threats_pos)
            ty = sum(p[1] for p in threats_pos) / len(threats_pos)
            ux, uy = unit2(state.pos[0] - tx, state.pos[1] - ty)
            best = None
            for ang in (0.0, 0.7, -0.7, 1.4, -1.4):
                ca, sa = math.cos(ang), math.sin(ang)
                hop = float(P["px_hop_m"])
                p2 = (state.pos[0] + (ux * ca - uy * sa) * hop, state.pos[1] + (ux * sa + uy * ca) * hop, state.pos[2])
                c = ar.nearest_cover(p2, threats_pos[:3], 25.0, cubes=state.me.get("cubes", 0) or 0, budget_ms=1.2)
                if c is None or dist2d(c, state.pos) < 28.0 or abs(c[2] - state.pos[2]) > 6.0:
                    continue
                if not (B._inside_zone_soon(state, c, 6.0) and B._in_safe_future(state, c)):
                    continue
                mid = ((c[0] + state.pos[0]) * 0.5, (c[1] + state.pos[1]) * 0.5)
                q1 = ((c[0] + 3 * state.pos[0]) * 0.25, (c[1] + 3 * state.pos[1]) * 0.25)
                q3 = ((3 * c[0] + state.pos[0]) * 0.25, (3 * c[1] + state.pos[1]) * 0.25)
                if sum(ar.exposure([mid, q1, q3], threats_pos[:3])) > 0:
                    continue
                best = c
                break
            if best is not None:
                px["spot"] = spot = best
                d = dist2d(spot, state.pos)
                at_spot = False
                _stat(am, "px_hop")
        except Exception:
            pass
    if at_spot:
        if seeing:
            if px["seen_since"] is None:
                px["seen_since"] = t
        else:
            px["seen_since"] = None
        if px["seen_since"] is not None and t - px["seen_since"] > 0.7:
            px["on"] = False                          # found: the reset is over, fight
            px["retry_t"] = t + float(P["px_retry_s"])
            _stat(am, "px_found")
            return None
    if t - px["t0"] > float(P["px_max_s"]) and state.hp < px["hp0"] + 150.0:
        px["on"] = False
        px["retry_t"] = t + 2.0 * float(P["px_retry_s"])
        _stat(am, "px_fail")
        return None
    face = it.face
    if mechs:
        face = yaw_to(state.pos, min(mechs, key=lambda e: e.dist).pos)
    if at_spot:
        _stat(am, "px_sit")
        return Intent(mode="heal", goal=None, target_id=None, desired_range=None, urgency=0.3, face=face,
                      allow_fire=False, allow_boost=False, max_speed=0.0, reason=f"phoenix sit {hpf:.2f}")
    close = [e for e in seeing if e.dist < float(P["px_fight_m"])]
    _stat(am, "px_go")
    return Intent(mode="retreat", goal=tuple(spot), target_id=close[0].id if close else None, desired_range=None,
                  urgency=0.9, face=face, allow_fire=bool(close), allow_boost=True, weave=bool(seeing) and d > 12.0,
                  avoid=threats_pos, reason=f"phoenix cover {d:.0f}m {hpf:.2f}")


# ----------------------------------------------------------------------------- corner duel
def _peek_pair(state: WorldState, e, threats: Threats):
    """(H, E): a spot hidden from the target (and the other mechs shooting at us) and, a few metres from it, a spot
    with a clear shot at the target that the others see least. (None, None) when the ground offers none."""
    import time as _time
    ar = state.arena
    P = B.P
    t_end = _time.perf_counter() + 0.004
    cubes = state.me.get("cubes", 0) or 0
    hs = set(getattr(threats, "hunters", None) or []) | set(threats.attackers or [])
    others = [tuple(o.pos) for o in sorted(threats.enemies, key=lambda o: o.dist)
              if o.kind == "mech" and o.id != e.id and o.visible and (o.id in hs or o.facing_me) and o.dist < 200.0][:2]
    tpos = tuple(e.pos)
    H = None
    try:
        H = ar.nearest_cover(state.pos, [tpos] + others, float(P["cn_reach"]), cubes=cubes, budget_ms=1.8)
        if H is None and others:
            H = ar.nearest_cover(state.pos, [tpos], float(P["cn_reach"]), cubes=cubes, budget_ms=1.2)
    except Exception:
        H = None
    if H is None or not B._inside_zone_soon(state, H, 6.0):
        return None, None
    k = ar.size_class(cubes)
    best, bk = None, None
    for r in (4.0, 6.5, 9.0):
        for j in range(10):
            if _time.perf_counter() > t_end:
                break
            a = j * math.pi / 5.0
            cx, cy = H[0] + r * math.cos(a), H[1] + r * math.sin(a)
            try:
                cz = ar.surface(cx, cy)
                if abs(cz - H[2]) > 1.5 or not ar.standable(cx, cy, k) or not ar.walk_line(H[0], H[1], cx, cy, k):
                    continue
                if ar.can_shoot((cx, cy, cz), tpos, cubes, 0) is None:
                    continue
                ex = sum(ar.exposure([(cx, cy)], others)) if others else 0
            except Exception:
                continue
            key = (ex, r)
            if bk is None or key < bk:
                best, bk = (cx, cy, cz), key
        if best is not None and bk[0] == 0:
            break
    if best is None:
        return None, None
    return H, best


def _corner(state: WorldState, threats: Threats, it: Intent, m, am, zp) -> Optional[Intent]:
    """Corner duel with the laser: charge behind hard cover, step out a few metres, release (the gun fires while we
    are out), step back for the cooldown. The house squad can then shoot only during the short peek, and the heal
    cycle's cover is already at our back. kyoto-max (practice #1) fights the same way in the live Showdown: out of
    everyone's line of sight, 3 s bursts, back into cover."""
    P = B.P
    if zp.get("must_go") or state.arena is None or not getattr(state.arena, "ok_nav", False):
        return None
    if it.mode != "engage" or it.target_id is None:
        return None
    las = None
    for w in state.me.get("weapons") or []:
        if w and w.get("kind") == "laser":
            las = w
    if las is None:
        return None
    e = threats.by_id(it.target_id)
    if e is None or e.kind != "mech" or not (25.0 <= e.dist <= float(P["cn_max_m"])):
        return None
    t = state.t
    cn = am.setdefault("cn", {"H": None, "E": None, "t": -1e9, "tid": None, "phase": "hide", "peek_t": 0.0})
    if cn["tid"] != e.id or t - cn["t"] > 1.5 or cn["H"] is None or dist2d(cn["H"], state.pos) > float(P["cn_reach"]) + 8.0:
        H, E = _peek_pair(state, e, threats)
        if H is None and cn["tid"] == e.id and cn["H"] is not None and t - cn["t"] < 4.0:
            pass                                       # keep the pair we have for a moment
        else:
            cn.update(H=H, E=E, t=t, tid=e.id)
    H, E = cn["H"], cn["E"]
    if H is None or E is None:
        _stat(am, "cn_none")
        return None
    charge = float(las.get("charge", 0) or 0)
    cd = float(las.get("cooldown", 0) or 0)
    full = float((las.get("stats") or {}).get("charge", 0.75))
    if cn["phase"] == "hide":
        if charge >= full - 0.12:
            cn["phase"], cn["peek_t"] = "peek", t
    elif (charge <= 0 and cd > 0.3) or t - cn["peek_t"] > float(P["cn_peek_s"]):
        cn["phase"] = "hide"
    goal = E if cn["phase"] == "peek" else H
    _stat(am, "cn_" + cn["phase"])
    return Intent(mode="engage", goal=tuple(goal), target_id=e.id, desired_range=None, urgency=0.45,
                  face=yaw_to(state.pos, e.pos), allow_fire=True, reason=f"corner {cn['phase']} {e.id}")


# ----------------------------------------------------------------------------- pet hunters
def _pet(state: WorldState, threats: Threats, it: Intent, m, am, zp) -> Optional[Intent]:
    """The squad hunts weakest first and adds hunters as it loses members, so the hunters are always the weakest house
    bots alive. Killing a hunter promotes a stronger one (calibrated sim: damage intake triples once the easy tier is
    dead; 2/3 of matches end at exactly that stage). So the first pet_n mechs that attack us unprovoked are never
    killed: they are worn down to a third of their HP and kept as weak hunters while we kill everybody else. When our
    HP runs low (or nothing else is left to shoot) the pets are cashed in: several quick kills at the end."""
    P = B.P
    pt = am.setdefault("pet", {"ids": [], "cash": False, "other_t": state.t, "cash_t": None})
    am["pet_spare"] = []
    if state.mode_guess == "ffa":
        return None
    t = state.t
    ids = pt["ids"]
    for ev in state.events:
        if ev.get("type") == "damaged":
            by = ev.get("by")
            if by is None or by >= 100 or by in ids or len(ids) >= int(P["pet_n"]):
                continue
            tr = state.tracks.get(by)
            if tr is None or tr.dmg_from_me < 60.0:       # it started it: one of the squad's hunters
                ids.append(by)
    ids[:] = [i for i in ids if not (state.tracks.get(i) is not None and state.tracks[i].dead)]
    if not ids:
        return None
    hpf_me = state.hp / max(1.0, state.max_hp)
    mechs = [e for e in threats.enemies if e.kind == "mech" and e.visible and t - e.last_seen_t < 1.0]
    others = [e for e in mechs if e.id not in ids]
    if others:
        pt["other_t"] = t
    if not pt["cash"] and (hpf_me < float(P["pet_cash_hp"]) or t > float(P["pet_until"])
                           or t - pt["other_t"] > float(P["pet_idle_s"])):
        pt["cash"] = True
        pt["cash_t"] = round(t, 1)
        pt["cash_n"] = len(ids)
        _stat(am, "pet_cash_start")
    if zp.get("must_go"):
        if not pt["cash"]:
            am["pet_spare"] = list(ids)
        return None
    if pt["cash"]:
        cand = [e for e in mechs if e.id in ids and e.los]
        if not cand:
            return None
        e = min(cand, key=lambda q: ((q.hp if q.hp is not None else 1400.0), q.dist))
        _stat(am, "pet_cash")
        return Intent(mode="engage", goal=None, target_id=e.id, desired_range=B._desired_range(state, e), urgency=0.5,
                      face=yaw_to(state.pos, e.pos), allow_fire=True, reason=f"cash pet {e.id}")
    am["pet_spare"] = list(ids)
    spare = list(ids)
    los_others = [e for e in others if e.los and e.dist < 215.0]
    if los_others:
        e = min(los_others, key=lambda q: ((q.hp if q.hp is not None else 1400.0) / 1400.0 + q.dist / 300.0))
        _stat(am, "pet_kill_other")
        return Intent(mode="engage", goal=None, target_id=e.id, desired_range=B._desired_range(state, e), urgency=0.5,
                      face=yaw_to(state.pos, e.pos), allow_fire=True, spare_ids=spare, avoid=[], reason=f"kill {e.id} (pets {len(ids)})")
    if it.mode in ("loot", "capture", "rotate", "heal") and it.target_id is None and it.loot_id is not None:
        return None                                    # the base brain is fetching a weapon / cubes: let it
    # only pets in sight: wear the freshest one down, then go and find someone we are allowed to kill
    pets_vis = [e for e in mechs if e.id in ids and e.los]
    wound = [e for e in pets_vis if e.hp is not None and e.max_hp and e.hp / e.max_hp > float(P["pet_wound_hp"])]
    if wound and hpf_me > 0.55:
        e = max(wound, key=lambda q: q.hp)
        _stat(am, "pet_wound")
        return Intent(mode="engage", goal=None, target_id=e.id, desired_range=max(95.0, B._desired_range(state, e)),
                      urgency=0.5, face=yaw_to(state.pos, e.pos), allow_fire=True,
                      spare_ids=[i for i in ids if i != e.id], reason=f"wound pet {e.id}")
    best, bd = None, 400.0
    for tr in state.tracks.values():
        if tr.kind != "mech" or tr.dead or tr.id in ids or t - tr.last_seen_t > 40.0:
            continue
        d = dist2d(tr.pos, state.pos)
        if d < bd and B._inside_zone_soon(state, tr.pos, 3.0):
            best, bd = tr, d
    if best is not None:
        _stat(am, "pet_seek")
        return Intent(mode="loot", goal=tuple(best.pos), urgency=0.4, face=yaw_to(state.pos, best.pos), allow_fire=True,
                      spare_ids=spare, weave=True, reason=f"seek {best.id} (pets {len(ids)})")
    if pets_vis:
        e = min(pets_vis, key=lambda q: q.dist)
        _stat(am, "pet_hold")
        return Intent(mode="engage", goal=None, target_id=e.id, desired_range=100.0, urgency=0.4,
                      face=yaw_to(state.pos, e.pos), allow_fire=True, spare_ids=spare, reason=f"hold pets {len(ids)}")
    return None


# ----------------------------------------------------------------------------- bank and burst
def _bank(state: WorldState, threats: Threats, it: Intent, m, am, zp) -> Optional[Intent]:
    """The squad escalates on DEATHS ("more join as you thin the squad out"), not on damage. So do not kill one bot at
    a time (each kill is then paid for under one more hunter): wound several house bots down to a third of their HP
    while only the opening hunter is on us, keep them from regenerating with a single shot every few seconds, then
    finish them all within seconds. The kills are banked before any reinforcement has walked over, and the cubes of the
    whole burst (2 per kill) arrive at once."""
    P = B.P
    bk = am.setdefault("bank", {"phase": "bank", "W": {}, "t0": None, "last_fresh": state.t, "bursts": 0})
    am["bank_spare"] = []
    if bk["phase"] == "done" or state.mode_guess == "ffa" or zp.get("must_go"):
        return None
    t = state.t
    W = bk["W"]
    for ev in state.events:
        if ev.get("type") == "hit" and ev.get("target") in W:
            W[ev.get("target")]["t_hit"] = t
    thr = float(P["bank_hp"])
    vis = []
    for e in threats.enemies:
        if e.kind != "mech":
            continue
        tr = state.tracks.get(e.id)
        if tr is not None and tr.dead:
            W.pop(e.id, None)
            continue
        if e.hp is None or not e.max_hp:
            continue
        hpf = e.hp / max(1.0, e.max_hp)
        if e.id in W:
            W[e.id]["hpf"] = hpf
            if e.visible:
                W[e.id]["seen"] = t
            if hpf > thr + 0.2:
                W.pop(e.id, None)                 # regenerated out of reach: wound it again later
        elif e.visible and hpf <= thr:
            W[e.id] = {"t_hit": t, "hpf": hpf, "seen": t}
        if e.visible and e.los and e.dist < 210.0 and t - e.last_seen_t < 1.0:
            vis.append((e, hpf))
    for i in [i for i, w in W.items() if t - w["seen"] > 8.0 or (state.tracks.get(i) is not None and state.tracks[i].dead)]:
        W.pop(i, None)
    hpf_me = state.hp / max(1.0, state.max_hp)
    armed = (state.weapon_kinds() + [None, None])[1] is not None
    if bk["phase"] == "bank":
        if not armed and t < float(P["bank_unarmed_t"]):
            return None
        if W and bk["t0"] is None:
            bk["t0"] = t
        n_w = len(W)
        go = (n_w >= int(P["bank_n"]) or (n_w >= 1 and hpf_me < float(P["bank_bail_hp"]))
              or (n_w >= 2 and bk["t0"] is not None and t - bk["t0"] > float(P["bank_max_s"]))
              or (n_w >= 1 and t - bk["last_fresh"] > 10.0) or (n_w >= 1 and t > float(P["bank_until"])))
        if go:
            bk["phase"] = "burst"
            bk["bursts"] += 1
            bk["burst_t"] = t
            bk["burst_n"] = n_w
            _stat(am, "bank_burst_start")
        elif t > float(P["bank_until"]) + 20.0 or hpf_me < 0.3:
            bk["phase"] = "done"
            return None
    if bk["phase"] == "burst":
        if not W or t - bk.get("burst_t", t) > 40.0:
            bk["phase"] = "bank" if (bk["bursts"] < int(P["bank_cycles"]) and hpf_me > 0.6 and t < float(P["bank_until"])) else "done"
            bk["t0"] = None
            bk["last_fresh"] = t
            return None
        cand = [(hpf, e) for e, hpf in vis if e.id in W]
        if not cand:
            return None                                # wounded ones out of sight: base brain / seek brings us back
        hpf, e = min(cand, key=lambda q: (q[0], q[1].dist))
        _stat(am, "bank_burst")
        return Intent(mode="engage", goal=None, target_id=e.id, desired_range=B._desired_range(state, e), urgency=0.5,
                      face=yaw_to(state.pos, e.pos), allow_fire=True, reason=f"burst {e.id} {hpf:.2f} ({len(W)} banked)")
    # ---- bank phase: never kill; wound fresh ones, re-tag wounded ones before they regenerate (5 s)
    am["bank_spare"] = list(W.keys())
    retag = [(t - W[e.id]["t_hit"], e) for e, hpf in vis if e.id in W and hpf > 0.10 and t - W[e.id]["t_hit"] > float(P["bank_retag_s"])]
    fresh = [(hpf, e.dist, e) for e, hpf in vis if e.id not in W]
    tgt = None
    if retag:
        tgt = max(retag, key=lambda q: q[0])[1]
        why = "tag"
    elif fresh:
        tgt = min(fresh, key=lambda q: (round(q[0], 1), q[1]))[2]
        bk["last_fresh"] = t
        why = "wound"
    if tgt is None:
        return None
    spare = [e.id for e, _ in vis if e.id != tgt.id] + [i for i in W if i != tgt.id]
    _stat(am, "bank_" + why)
    return Intent(mode="engage", goal=None, target_id=tgt.id, desired_range=B._desired_range(state, tgt), urgency=0.5,
                  face=yaw_to(state.pos, tgt.pos), allow_fire=True, spare_ids=spare,
                  reason=f"{why} {tgt.id} ({len(W)} banked)")


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
    bk = am.get("bank") or {}
    pt = am.get("pet") or {}
    px = am.get("px") or {}
    if px:
        return {"stat": am.get("stat"), "px": {"n": px.get("n"), "done": px.get("done"), "gain": round(px.get("gain", 0.0))},
                "drops": am.get("drops_got", 0)}
    if pt:
        return {"stat": am.get("stat"), "pet": {"n": len(pt.get("ids") or []), "cash_t": pt.get("cash_t"), "cash_n": pt.get("cash_n")}}
    return {"stat": am.get("stat"), "drops": am.get("drops_got", 0), "drop_t": am.get("drop_t"),
            "bank": {"phase": bk.get("phase"), "bursts": bk.get("bursts"), "burst_t": bk.get("burst_t"),
                     "burst_n": bk.get("burst_n")} if bk else None}
