"""navigate.step robustness + zone helpers.  python -m unittest discover -s tests/nav -v"""
from __future__ import annotations

import math
import os
import random
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from bot import navigate  # noqa: E402
from bot.arena import Arena  # noqa: E402
from bot.state import EnemyThreat, Intent, ProjectileRisk, Threats, WorldState  # noqa: E402

A = None


def setUpModule():
    global A
    A = Arena.load(os.path.join(ROOT, "arena"))


def make_state(pos, arena, t=10.0, tick=200, energy=80.0, grounded=True, zone=None):
    st = WorldState({"config": {"mech": {"walk_speed": 11.7, "boost_speed": 19.5}}, "slot": 0, "seed": 1}, arena)
    obs = {"type": "obs", "tick": tick, "t": t, "alive": 10,
           "self": {"id": 0, "pos": list(pos), "vel": [0, 0, 0], "aim": [0, 0], "hp": 1000, "max_hp": 1400,
                    "energy": energy, "max_energy": 100, "grounded": grounded, "cubes": 0, "upgrades": [],
                    "in_zone": True, "weapons": [None, None], "stats": {"walk_speed": 11.7, "boost_speed": 19.5}},
           "mechs": [{"id": 5, "kind": "mech", "pos": [pos[0] + 40, pos[1], pos[2]], "vel": [0, 0, 0], "aim": [3.14, 0]}],
           "zone": zone or {"center": [41.3, -72.8], "radius": 560, "next_center": [-23.7, 2.2], "next_radius": 380,
                            "shrink_start": 60, "shrink_end": 110, "dps": 20}}
    st.update(obs)
    return st


def valid(out):
    mx, my = out.move
    return math.isfinite(mx) and math.isfinite(my) and math.hypot(mx, my) <= 1.0 + 1e-6 and \
        isinstance(out.boost, bool) and isinstance(out.jump, bool)


class TestStepRobust(unittest.TestCase):
    def test_fuzz(self):
        rng = random.Random(5)
        modes = ["rotate", "loot", "engage", "retreat", "heal", "hold", "capture"]
        worst = 0.0
        for i in range(400):
            ar = A if i % 7 else None
            pos = (rng.uniform(-600, 650), rng.uniform(-400, 450), rng.uniform(-10, 80))
            if i % 3 == 0:
                pos = (pos[0], pos[1], float("nan")) if i % 9 == 0 else pos
            st = make_state(pos, ar, t=rng.uniform(0, 400), tick=i * 2, energy=rng.uniform(0, 100),
                            grounded=rng.random() < 0.8)
            goal = None
            r = rng.random()
            if r < 0.6:
                goal = (rng.uniform(-600, 650), rng.uniform(-400, 450), rng.uniform(-10, 80))
            elif r < 0.7:
                goal = (float("nan"), 0.0, 0.0)
            it = Intent(mode=rng.choice(modes), goal=goal, target_id=rng.choice([None, 5, 99]),
                        desired_range=rng.choice([None, 30.0, 120.0]), urgency=rng.random(),
                        allow_boost=rng.random() < 0.7, avoid=[(pos[0] + 10, pos[1], 0.0)] if rng.random() < 0.3 else [],
                        max_speed=rng.choice([None, 4.5]))
            th = Threats()
            if rng.random() < 0.3:
                th.dodge = (rng.uniform(-1, 1), rng.uniform(-1, 1))
                th.incoming = [ProjectileRisk(id=1, kind="gun", t_impact=0.2, miss_dist=0.5, dodge=th.dodge)]
            if rng.random() < 0.3:
                th.enemies = [EnemyThreat(id=5, kind="mech", pos=(pos[0] + 40, pos[1], 0.0), vel=(0, 0, 0), hp=900,
                                          max_hp=1400, weapons=["gun"], dist=40.0, visible=True, last_seen_t=st.t)]
            t0 = time.perf_counter()
            out = navigate.step(st, it, th)
            worst = max(worst, time.perf_counter() - t0)
            self.assertTrue(valid(out), (i, pos, goal, out))
            if it.max_speed is not None and goal is not None and all(math.isfinite(v) for v in goal):
                self.assertLessEqual(math.hypot(*out.move), 4.5 / 11.7 + 1e-6)

    def test_never_jets_in_air_without_a_hop(self):
        st = make_state((100.0, 0.0, 30.0), A, grounded=False, energy=90)
        it = Intent(mode="rotate", goal=(100.0, 100.0, 0.0), urgency=0.9)
        out = navigate.step(st, it, Threats())
        self.assertFalse(out.boost)

    def test_hold_returns_zero_move(self):
        st = make_state((100.0, 0.0, A.surface(100.0, 0.0)), A)
        out = navigate.step(st, Intent(mode="hold", goal=None), Threats())
        self.assertEqual(out.move, (0.0, 0.0))


class TestZone(unittest.TestCase):
    def test_edge_time_and_safe_route(self):
        z = {"center": [0.0, 0.0], "radius": 200.0, "next_center": [50.0, 0.0], "next_radius": 100.0,
             "shrink_start": 60.0, "shrink_end": 110.0, "dps": 20}
        # point inside next circle: never outside this phase
        self.assertEqual(navigate.edge_time(z, (50.0, 10.0), 0.0), math.inf)
        # point inside the current circle but outside the next: edge reaches it during the shrink
        te = navigate.edge_time(z, (-150.0, 0.0), 0.0)
        self.assertTrue(60.0 <= te <= 110.0, te)
        (cx, cy), r = navigate.zone_circle_at(z, te)
        self.assertAlmostEqual(math.hypot(-150.0 - cx, 0.0 - cy), r, delta=0.5)
        st = make_state((-150.0, 0.0, A.surface(-150.0, 0.0)), A, t=20.0, zone=z)
        sr = navigate.safe_route(st)
        p = sr["point"]
        self.assertLessEqual(math.hypot(p[0] - 50.0, p[1]), 100.0)
        self.assertTrue(A.walkable(p[0], p[1]))
        self.assertLess(sr["leave_by"], te)
        self.assertGreater(sr["eta"], 0.0)


class TestZoneField(unittest.TestCase):
    def test_field_matches_astar(self):
        cx, cy, r = 100.0, -50.0, 135.0
        f = A.zone_field(cx, cy, r)
        for _ in range(5000):
            if A.flood_advance(f, 5.0):
                break
        self.assertTrue(f.done)
        rng = random.Random(1)
        n = 0
        while n < 15:
            x, y = rng.uniform(-480, 530), rng.uniform(-310, 360)
            if not A.walkable(x, y) or math.hypot(x - cx, y - cy) < r + 20:
                continue
            c = A.flood_cost(f, x, y, A.surface(x, y))
            if c is None:        # beyond max_cost
                continue
            n += 1
            ux, uy = cx - x, cy - y
            d = math.hypot(ux, uy)
            px, py = cx - ux / d * (r - 2), cy - uy / d * (r - 2)
            L = A.path_len((x, y, A.surface(x, y)), (px, py, A.surface(px, py)), budget_ms=1e5)
            self.assertLessEqual(c, L * 1.12 + 8.0)        # never much worse than walking to the nearest point
            self.assertGreaterEqual(c, d - r - 6.0)        # never shorter than the straight line
        self.assertEqual(A.flood_cost(f, cx, cy), 0.0)


if __name__ == "__main__":
    unittest.main()
