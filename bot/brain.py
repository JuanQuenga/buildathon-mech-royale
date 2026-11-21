"""Objectives, intent, inventory and upgrades. OWNER: integrator. (v0: example-bot behaviour.)"""
from __future__ import annotations

from .state import Intent, InvOut, Threats, WorldState, dist2d


def init(state: WorldState) -> None:
    pass


def choose_intent(state: WorldState, threats: Threats) -> Intent:
    z = state.zone
    goal = None
    if z:
        goal = (z["next_center"][0], z["next_center"][1], state.pos[2])
    vis = [e for e in threats.mechs() if e.visible]
    mode = "engage" if vis else "rotate"
    return Intent(mode=mode, goal=goal, urgency=0.0 if state.me.get("in_zone", True) else 1.0)


def inventory(state: WorldState, intent: Intent) -> InvOut:
    out = InvOut()
    if state.obs.get("offer"):
        out.pick = 0
    reach = state.cfg.get("loot", {}).get("pickup_radius", 4)
    if state.weapon(1) is None:
        for p in state.obs.get("pickups") or []:
            if p.get("kind") != "gun" and dist2d(p["pos"], state.pos) < reach and abs(p["pos"][2] - state.pos[2]) < 4:
                out.take = p["id"]
                break
    return out
