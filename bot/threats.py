"""Threat assessment. OWNER: combat. Integrator placeholder with the agreed signature."""
from __future__ import annotations

from .state import EnemyThreat, Threats, WorldState, dist3d


def assess(state: WorldState) -> Threats:
    out = Threats()
    for tr in state.tracks.values():
        if tr.dead or state.t - tr.last_seen_t > 5.5:
            continue
        d = dist3d(tr.pos, state.pos)
        out.enemies.append(EnemyThreat(id=tr.id, kind=tr.kind, pos=tr.pos, vel=tr.vel, hp=tr.hp, max_hp=tr.max_hp,
                                       weapons=tr.weapons, dist=d, visible=tr.visible_now, last_seen_t=tr.last_seen_t,
                                       los=tr.visible_now, can_hit_me=tr.visible_now and d < 230,
                                       charging=tr.charging, danger=0.0))
    out.attackers = sorted({by for (t, a, by, w) in state.damage_log if by is not None and t >= state.t - 3})
    return out
