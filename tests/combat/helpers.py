"""Shared fixtures for combat tests: config, fake arenas, observation builders. Standard library only."""
from __future__ import annotations

import copy
import gzip
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from bot import state as st  # noqa: E402

KIT = "/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/mech-royale/starter"
REPLAY = os.path.join(KIT, "mechanics-v2-16.jsonl.gz")
STREAM = os.path.join(KIT, "mechfight-kit/check/stream.jsonl.gz")

_CFG = None


def config():
    """The real hello.config from the kit stream if present, else a copy of the documented defaults."""
    global _CFG
    if _CFG is None:
        try:
            with gzip.open(STREAM, "rt") as f:
                _CFG = json.loads(f.readline())["config"]
        except Exception:
            _CFG = {
                "mech": {"radius": 2.5, "height": 9, "eye_height": 8, "muzzle_height": 7, "hp": 1400, "walk_speed": 11.7,
                         "turn_rate": 4, "pitch_rate": 3, "min_pitch": -0.7, "max_pitch": 1.3, "gravity": 22,
                         "rear_mult": 1.5, "regen_delay": 5},
                "weapons": {"gun": {"damage": 45, "cooldown": 0.24, "speed": 252, "range": 230, "spread_deg": 0.6, "mag": 12, "reload": 2.4},
                            "mortar": {"damage": 200, "splash": 160, "splash_radius": 7, "splash_edge": 0.3, "cooldown": 2.6,
                                       "speed": 72, "gravity": 22, "ttl": 7, "knock": 16, "knock_up": 9, "drain": 45},
                            "laser": {"damage": 315, "charge": 0.75, "min_charge": 0.15, "min_frac": 0.35, "hold_s": 2,
                                      "cooldown": 1.65, "range": 280, "cookoff": 0.6},
                            "lightning": {"damage": 60, "cooldown": 0.25, "range": 45, "cone_deg": 30, "chain": 2,
                                          "chain_range": 14, "chain_falloff": 0.7, "energy": 3, "short_s": 2}},
                "cubes": {"damage_per_cube": 0.04, "stat_cap": 10, "size_per_cube": 0.05},
                "crates": {"hp": 300, "radius": 1.4, "height": 2.4},
                "npc": {"radius": 1.8, "height": 3.5, "damage": 25},
                "sound": {"bearing_noise_deg": 7},
            }
    return copy.deepcopy(_CFG)


def weapon(kind, **kw):
    cfg = config()["weapons"][kind]
    w = {"kind": kind, "cooldown": 0.0, "stats": dict(cfg)}
    if kind == "gun":
        w.update(ammo=12, reload=0)
    if kind == "laser":
        w.update(charge=0)
    w.update(kw)
    return w


def mech_stats():
    m = config()["mech"]
    s = dict(m)
    return s


def obs(tick=100, pos=(0, 0, 0), vel=(0, 0, 0), aim=(0.0, 0.0), weapons=None, mechs=(), projectiles=(), crates=(),
        events=(), beams=(), sounds=(), hp=1400, energy=100, cubes=0, alive=16):
    return {
        "type": "obs", "tick": tick, "t": tick / 20.0, "alive": alive,
        "self": {"id": 0, "pos": list(pos), "vel": list(vel), "aim": list(aim), "hp": hp, "max_hp": 1400,
                 "energy": energy, "max_energy": 100, "grounded": True, "cubes": cubes, "upgrades": [], "in_zone": True,
                 "weapons": weapons if weapons is not None else [weapon("gun"), None], "stats": mech_stats()},
        "mechs": list(mechs), "projectiles": list(projectiles), "crates": list(crates), "cubes": [], "pickups": [],
        "sounds": list(sounds), "beams": list(beams), "events": list(events), "drops": [],
        "zone": {"center": [0, 0], "radius": 560, "next_center": [0, 0], "next_radius": 380, "shrink_start": 60,
                 "shrink_end": 110, "dps": 20}, "offer": None,
    }


def enemy(i, pos, vel=(0, 0, 0), aim=(0.0, 0.0), hp=1400, weapons=("gun",), charging=False, kind="mech", cubes=0):
    return {"id": i, "kind": kind, "pos": list(pos), "vel": list(vel), "aim": list(aim), "hp": hp, "max_hp": 1400 if kind == "mech" else 350,
            "cubes": cubes, "weapons": list(weapons), "charging": charging}


def world(arena=None):
    return st.WorldState({"type": "hello", "slot": 0, "seed": 1, "config": config()}, arena)


class OpenArena:
    """Flat ground at z=0, nothing blocks."""
    calls = 0

    def height(self, x, y):
        return 0.0

    def ground_z(self, x, y, z_hint=None):
        return 0.0

    def los(self, a, b):
        return True

    def shot_clear(self, a, b):
        OpenArena.calls += 1
        return True


class WallArena(OpenArena):
    """Infinite wall occupying x in [x0, x0 + 2], from the ground up to `top`."""

    def __init__(self, x0=50.0, top=30.0):
        self.x0, self.top = x0, top

    def _blocked(self, a, b):
        lo, hi = self.x0, self.x0 + 2.0
        if (a[0] < lo and b[0] < lo) or (a[0] > hi and b[0] > hi):
            return False
        # sample the segment inside the slab
        n = 40
        for k in range(n + 1):
            f = k / n
            x = a[0] + (b[0] - a[0]) * f
            z = a[2] + (b[2] - a[2]) * f
            if lo <= x <= hi and z <= self.top:
                return True
        return False

    def shot_clear(self, a, b):
        return not self._blocked(a, b)

    def los(self, a, b):
        return not self._blocked(a, b)

    def ground_z(self, x, y, z_hint=None):
        if self.x0 <= x <= self.x0 + 2.0 and (z_hint is None or z_hint >= self.top):
            return self.top
        return 0.0


def load_replay():
    if not os.path.exists(REPLAY):
        return None, []
    f = gzip.open(REPLAY, "rt")
    h = json.loads(f.readline())
    frames = []
    for line in f:
        fr = json.loads(line)
        if "t" in fr and "m" in fr:
            frames.append(fr)
    return h, frames
