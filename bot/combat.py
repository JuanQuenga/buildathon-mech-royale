"""Aim and fire. OWNER: combat. Integrator placeholder with the agreed signature (example-bot behaviour)."""
from __future__ import annotations

import math

from .state import CombatOut, Intent, Threats, WorldState


def step(state: WorldState, intent: Intent, threats: Threats) -> CombatOut:
    x, y, z = state.pos
    vis = [e for e in threats.enemies if e.visible and e.kind == "mech"]
    if intent.target_id is not None:
        t = threats.by_id(intent.target_id)
        if t is not None and t.visible:
            vis = [t]
    if not vis or not intent.allow_fire:
        yaw = intent.face if intent.face is not None else (state.me.get("aim") or [0, 0])[0]
        return CombatOut(aim=(yaw, 0.0))
    e = min(vis, key=lambda e: e.dist)
    p = e.pos
    aim = (math.atan2(p[1] - y, p[0] - x), math.atan2(p[2] - z - 2.5, math.hypot(p[0] - x, p[1] - y)))
    return CombatOut(aim=aim, fire=(True, True), target_id=e.id)
