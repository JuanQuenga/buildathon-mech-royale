"""Movement. OWNER: nav. Integrator placeholder with the agreed signature (example-bot behaviour)."""
from __future__ import annotations

import math

from .state import Intent, NavOut, Threats, WorldState


def step(state: WorldState, intent: Intent, threats: Threats) -> NavOut:
    if intent.goal is None:
        return NavOut()
    x, y, _ = state.pos
    gx, gy = intent.goal[0], intent.goal[1]
    d = math.hypot(gx - x, gy - y)
    if d < 2:
        return NavOut(eta=0.0)
    yaw = math.atan2(gy - y, gx - x)
    return NavOut(move=(math.cos(yaw), math.sin(yaw)), boost=intent.urgency > 0.7 and state.energy > 30,
                  jump=state.tick % 40 == 0, eta=d / max(1.0, state.stat("walk_speed", 11.7)))
