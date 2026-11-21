#!/usr/bin/env python3
"""Scenario tests for the brain (zone timing, heal, fight choice, inventory, upgrades). Standard library only.

    python3 eval/test_brain.py
"""
import copy
import gzip
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
KIT = os.environ.get("MECH_KIT", "/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/mech-royale/starter/mechfight-kit")

from bot import brain, state as st  # noqa: E402
from bot.state import EnemyThreat, Threats  # noqa: E402


def fixture():
    p = os.path.join(KIT, "check", "stream.jsonl.gz")
    if not os.path.exists(p):
        p = os.path.join(ROOT, "sim", "data", "stream.jsonl.gz")
    with gzip.open(p, "rt") as f:
        msgs = [json.loads(l) for l in f if l.strip()]
    return msgs[0], [m for m in msgs if m.get("type") == "obs"]


HELLO, OBS = fixture()


def mk(pos=(0, 0, 0), t=30.0, zone=None, hp=1400, mechs=(), events=(), weapons=None, offer=None, pickups=(), in_zone=True):
    o = copy.deepcopy(OBS[50])
    o["tick"], o["t"] = int(t * 20), t
    o["self"]["pos"] = list(pos)
    o["self"]["vel"] = [0, 0, 0]
    o["self"]["hp"] = hp
    o["self"]["in_zone"] = in_zone
    if weapons is not None:
        o["self"]["weapons"] = weapons
    o["mechs"] = list(mechs)
    o["events"] = list(events)
    o["pickups"] = list(pickups)
    o["crates"], o["cubes"], o["projectiles"], o["sounds"], o["beams"], o["drops"] = [], [], [], [], [], []
    o["offer"] = offer
    o["zone"] = zone or {"center": [0, 0], "radius": 560, "next_center": [0, 0], "next_radius": 380,
                         "shrink_start": 60, "shrink_end": 110, "dps": 20}
    return o


def run(obs_list, threats_fn=None):
    s = st.WorldState(HELLO, None)
    it = None
    for o in obs_list:
        s.update(o)
        th = threats_fn(s) if threats_fn else Threats()
        it = brain.choose_intent(s, th)
    return s, it


def test_inside_next_circle_no_rotate():
    s, it = run([mk(pos=(10, 10, 0))])
    assert it.mode != "rotate", it


def test_far_outside_next_circle_rotates_in_time():
    # 400 m from the next centre (radius 140), shrink ends in 25 s: ~ 260+ m to walk at 11.7 m/s -> must go now
    z = {"center": [0, 0], "radius": 500, "next_center": [0, 0], "next_radius": 140, "shrink_start": 40, "shrink_end": 75, "dps": 35}
    s, it = run([mk(pos=(400, 0, 0), t=50, zone=z)])
    assert it.mode == "rotate", it
    assert it.goal is not None and math.hypot(it.goal[0], it.goal[1]) < 140, it.goal


def test_rotate_not_too_early():
    # 200 m out, radius 140 next, shrink ends at 200 s, t=30: lots of slack -> not rotating yet
    z = {"center": [0, 0], "radius": 560, "next_center": [0, 0], "next_radius": 140, "shrink_start": 150, "shrink_end": 200, "dps": 20}
    s, it = run([mk(pos=(200, 0, 0), t=30, zone=z)])
    assert it.mode != "rotate", it
    zp = s.scratch["brain"]["zp"]
    assert zp["slack"] > 60, zp


def test_outside_zone_rotates():
    z = {"center": [0, 0], "radius": 100, "next_center": [0, 0], "next_radius": 50, "shrink_start": 10, "shrink_end": 300, "dps": 60}
    s, it = run([mk(pos=(150, 0, 0), t=50, zone=z, in_zone=False)])
    assert it.mode == "rotate" and it.urgency >= 0.8, it


def test_exit_time_moving_edge():
    z = {"center": [0, 0], "radius": 200, "next_center": [0, 0], "next_radius": 100, "shrink_start": 100, "shrink_end": 200, "dps": 35}
    s, _ = run([mk(pos=(150, 0, 0), t=90, zone=z)])
    te = brain._exit_time(s, s.pos)
    assert abs(te - 150) < 0.5, te   # radius 200->100 over 100 s passes 150 at t=150


def test_heal_when_low_and_alone():
    s, it = run([mk(pos=(0, 0, 0), hp=500)])
    assert it.mode == "heal" and not it.allow_fire, it


def threat(id_, pos, hp=1400, weapons=("gun",), dist=None, attacker=False, s=None):
    d = dist if dist is not None else math.dist(pos, (0, 0, 0))
    return EnemyThreat(id=id_, kind="mech", pos=pos, vel=(0, 0, 0), hp=hp, max_hp=1400, weapons=list(weapons), dist=d,
                       visible=True, last_seen_t=s.t if s else 0, los=True, can_hit_me=True)


def test_retreat_when_outnumbered():
    def th(s):
        es = [threat(i, (40 + i, 0, 0), s=s) for i in range(1, 5)]
        return Threats(enemies=es, attackers=[1, 2, 3, 4])
    mechs = [{"id": i, "kind": "mech", "pos": [40 + i, 0, 0], "vel": [0, 0, 0], "aim": [math.pi, 0], "hp": 1400, "max_hp": 1400, "weapons": ["gun"]} for i in range(1, 5)]
    ev = [{"type": "damaged", "amount": 45, "weapon": "gun", "bearing": 0.0, "by": i} for i in range(1, 5)]
    s, it = run([mk(hp=700, mechs=mechs, events=ev)], th)
    assert it.mode == "retreat", it


def test_engage_weak_attacker():
    def th(s):
        return Threats(enemies=[threat(1, (40, 0, 0), hp=300, s=s)], attackers=[1])
    mechs = [{"id": 1, "kind": "mech", "pos": [40, 0, 0], "vel": [0, 0, 0], "aim": [math.pi, 0], "hp": 300, "max_hp": 1400, "weapons": ["gun"]}]
    ev = [{"type": "damaged", "amount": 45, "weapon": "gun", "bearing": 0.0, "by": 1}]
    s, it = run([mk(hp=1200, mechs=mechs, events=ev)], th)
    assert it.mode == "engage" and it.target_id == 1, it


def test_take_secondary_and_upgrade_pick():
    o = mk(pickups=[{"id": 8005, "kind": "lightning", "pos": [1, 1, 0]}],
           offer={"id": 1, "expires": 40, "choices": [{"id": "sensors"}, {"id": "plating"}, {"id": "gyros"}]})
    s = st.WorldState(HELLO, None)
    s.update(o)
    it = brain.choose_intent(s, Threats())
    inv = brain.inventory(s, it)
    assert inv.take == 8005 and inv.pick == 1, inv


def test_swap_mortar_for_laser():
    ws = copy.deepcopy(OBS[50]["self"]["weapons"])
    ws[1] = {"kind": "mortar", "cooldown": 0, "stats": {}}
    o = mk(weapons=ws, pickups=[{"id": 8009, "kind": "laser", "pos": [1, 0, 0]}])
    s = st.WorldState(HELLO, None)
    s.update(o)
    inv = brain.inventory(s, brain.choose_intent(s, Threats()))
    assert inv.take == 8009 and inv.drop == 1, inv


def main():
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:
                fails += 1
                print("FAIL", name, repr(e))
    print("FAILED" if fails else "ALL PASS")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
