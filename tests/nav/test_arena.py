"""Nav/geometry tests (stdlib unittest + numpy).  Run from the repo root:

    python -m unittest discover -s tests/nav -v

Hand-picked segments against known map features, replay consistency, planning and timing guards.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from bot.arena import Arena  # noqa: E402

REPLAY = os.environ.get("MECH_REPLAY", os.path.join(ROOT, "..", "..", "mech-royale", "starter", "mechanics-v2-16.jsonl.gz"))
A = None


def setUpModule():
    global A
    A = Arena.load(os.path.join(ROOT, "arena"))


class TestHeights(unittest.TestCase):
    def test_terrain_bilinear_matches_grid(self):
        # vertex values are exact; midpoints are the average of the four corners
        h00 = A.height(-100.0, 50.0)
        self.assertAlmostEqual(h00, float(A.H[50 + 334, -100 + 513]), places=4)
        mid = A.height(-99.5, 50.5)
        avg = float(A.H[384:386, 413:415].mean())
        self.assertAlmostEqual(mid, avg, places=4)

    def test_ground_z_roof_vs_street(self):
        # tall western tower (prism 69): roof when z_hint is above it, terrain beside it
        x, y = (-464.0 + -454.5) / 2, (-55.5 + -47.0) / 2
        self.assertTrue(A._inside_prism(69, x, y))
        self.assertAlmostEqual(A.ground_z(x, y, 80.0), A.p_top[69], places=3)
        self.assertLess(A.ground_z(x, y, 0.0), 5.0)

    def test_ground_z_under_elevated_bridge(self):
        x, y = -116.2, -32.1     # bridge 4 deck: base 6.59 top 8.59, terrain ~ -4.8
        self.assertAlmostEqual(A.ground_z(x, y, -4.0), A.height(x, y), places=3)
        self.assertAlmostEqual(A.ground_z(x, y, 9.0), 8.59, places=2)

    def test_surface_on_roof(self):
        x, y = (-464.0 + -454.5) / 2, (-55.5 + -47.0) / 2
        self.assertGreater(A.surface(x, y), 60.0)


class TestSegments(unittest.TestCase):
    def test_tall_building_blocks_and_clears_above(self):
        y = (-55.5 + -47.0) / 2
        self.assertFalse(A.shot_clear((-480.0, y, 10.0), (-440.0, y, 10.0)))
        self.assertTrue(A.shot_clear((-480.0, y, 80.0), (-440.0, y, 80.0)))

    def test_under_bridge_clear_through_deck_blocked(self):
        x = -116.2
        g = A.height(x, -32.1)
        # horizontal line under the deck (feet + 3 m), crossing the whole bridge footprint
        self.assertTrue(A._edges_hit(x, -45.0, g + 3.0, x, -20.0, g + 3.0, _ids_of(4)) is False)
        # same line at deck height: hits the deck side faces
        self.assertTrue(A._edges_hit(x, -45.0, 7.5, x, -20.0, 7.5, _ids_of(4)))
        # steep line entering above the deck and leaving below it without touching a side in range
        self.assertTrue(A._edges_hit(x, -36.0, 14.0, x, -28.0, 2.0, _ids_of(4)))

    def test_sliver_wall_blocks(self):
        # prism 250: 11 m long, < 2 m wide, base 3.18 top 10.19 (missed by 1 m rasters)
        ids = _ids_of(250)
        self.assertTrue(A._edges_hit(450.0, 205.0, 6.0, 450.0, 213.0, 6.0, ids))
        self.assertFalse(A._edges_hit(450.0, 205.0, 11.0, 450.0, 213.0, 11.0, ids))

    def test_terrain_occludes(self):
        # find a terrain bump: a 60 m line whose middle is >= 3 m above both ends
        import numpy as np
        H = A.H
        found = None
        for j in range(40, H.shape[0] - 40, 37):
            for i in range(40, H.shape[1] - 70, 23):
                a, b, m = H[j, i], H[j, i + 60], H[j, i + 30]
                if m > max(a, b) + 3.0:
                    found = (i, j, a, b)
                    break
            if found:
                break
        self.assertIsNotNone(found)
        i, j, a, b = found
        x0, y0 = A.x0 + i, A.y0 + j
        p, q = (x0, y0, float(a) + 0.5), (x0 + 60.0, y0, float(b) + 0.5)
        self.assertTrue(A._terrain_hit(*p, *q))
        hi = float(H[j, i:i + 61].max()) + 2.0
        self.assertFalse(A._terrain_hit(x0, y0, hi, x0 + 60.0, y0, hi))

    def test_trees_block_sight_not_shots(self):
        y, z = -45.67, 15.0           # tree 1117: crown radius 14 m around (351.5, -45.7)
        a, b = (330.0, y, z), (373.0, y, z)
        self.assertTrue(A._trees_block(*a, *b, A._cells_on_seg(a[0], a[1], b[0], b[1])))
        self.assertFalse(A._seg_blocked(a, b, trees=False) and not A._seg_blocked(a, b, trees=True))
        # shots ignore the canopy: if nothing solid is in the way, shot_clear is True while los is False
        if not A._seg_blocked(a, b, trees=False):
            self.assertTrue(A.shot_clear(a, b))
            self.assertFalse(A.los(a, b))

    def test_symmetry_random(self):
        import random
        rng = random.Random(7)
        n = 0
        while n < 150:
            x, y = rng.uniform(-480, 530), rng.uniform(-310, 360)
            if not A.walkable(x, y):
                continue
            a = (x, y, A.surface(x, y) + 7.0)
            ang = rng.uniform(0, 6.283)
            d = rng.uniform(5, 180)
            bx, by = x + d * math.cos(ang), y + d * math.sin(ang)
            if not A.in_bounds(bx, by):
                continue
            b = (bx, by, A.surface(bx, by) + 4.5)
            self.assertEqual(A._seg_blocked(a, b), A._seg_blocked(b, a), (a, b))
            n += 1


class TestReplay(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(REPLAY), "replay not available")
    def test_mechs_never_inside_solids(self):
        bad = 0
        n = 0
        with gzip.open(REPLAY, "rt") as f:
            f.readline()
            for line in f:
                fr = json.loads(line)
                for m in fr.get("m", []):
                    x, y, z = m[1], m[2], m[3]
                    for hz in (1.0, 4.5, 8.0):
                        n += 1
                        # prisms only (terrain sampling noise at feet level is not a collision)
                        for k in A._prisms_at(x, y):
                            if A.p_base[k] + 0.05 < z + hz < A.p_top[k] - 0.05 and A._inside_prism(k, x, y):
                                bad += 1
                                break
        self.assertEqual(bad, 0, f"{bad}/{n} body samples inside prisms")

    @unittest.skipUnless(os.path.exists(REPLAY), "replay not available")
    def test_server_beams_agree_with_shot_clear(self):
        """Laser beams / lightning arcs in the replay are server-traced: clear up to their end, and a beam
        that stopped early (no hit, < range) stopped at a prism or the terrain."""
        n = stops = 0
        with gzip.open(REPLAY, "rt") as f:
            f.readline()
            for line in f:
                for e in json.loads(line).get("ev", []):
                    if e["e"] not in ("laser", "zap"):
                        continue
                    pts = [e["from"], e["to"]] if e["e"] == "laser" else e["path"]
                    for a, b in zip(pts, pts[1:]):
                        L = math.dist(a, b)
                        if L < 1:
                            continue
                        u = [(b[i] - a[i]) / L for i in range(3)]
                        self.assertTrue(A.shot_clear(a, [b[i] - u[i] * 0.6 for i in range(3)]), (a, b))
                        n += 1
                        if e["e"] == "laser" and not e.get("hits") and L < 279:
                            stops += 1
                            beyond = [b[i] + u[i] * 1.0 for i in range(3)]
                            self.assertTrue(not A.shot_clear(a, beyond) or abs(b[2] - A.height(b[0], b[1])) < 0.1)
        self.assertGreater(n, 50)
        self.assertGreater(stops, 5)

    @unittest.skipUnless(os.path.exists(REPLAY), "replay not available")
    def test_grounded_mechs_on_baked_surface(self):
        errs = []
        with gzip.open(REPLAY, "rt") as f:
            f.readline()
            for i, line in enumerate(f):
                if i % 3:
                    continue
                fr = json.loads(line)
                for m in fr.get("m", []):
                    if m[8] & 1:
                        errs.append(abs(m[3] - A.ground_z(m[1], m[2], m[3] + 0.5)))
        errs.sort()
        self.assertLess(errs[int(0.99 * len(errs))], 0.35)


class TestPlanning(unittest.TestCase):
    def test_plan_and_walk_lines(self):
        s, g = (238.7, -5.3, A.surface(238.7, -5.3)), (-154.8, 7.4, A.surface(-154.8, 7.4))
        A._searches.clear()
        st, wps = A.plan_full(s, g, budget_ms=1e4)
        self.assertEqual(st, "ok")
        self.assertLess(math.dist(wps[-1][:2], g[:2]), 1.0)
        prev = s
        for w in wps:
            if w[3] == "walk":
                self.assertTrue(A.walk_line(prev[0], prev[1], w[0], w[1]), (prev, w))
            prev = w
        L = A.path_len(s, g, budget_ms=1e4)
        self.assertGreater(L, math.dist(s[:2], g[:2]))
        self.assertLess(L, 1.6 * math.dist(s[:2], g[:2]))

    def test_stadium_bowl_needs_a_jet(self):
        s = (-280.0, 120.0, A.surface(-280.0, 120.0))
        g = (-120.0, 10.0, A.surface(-120.0, 10.0))
        self.assertFalse(A.walkable(s[0], s[1]))          # not on the main ground component
        A._searches.clear()
        st, wps = A.plan_full(s, g, budget_ms=1e4)
        self.assertEqual(st, "ok")
        self.assertTrue(any(w[3] == "jet" for w in wps))
        A._searches.clear()
        st2, _ = A.plan_full(s, g, budget_ms=1e4, jet_cap=0.0)
        self.assertEqual(st2, "fail")

    def test_walk_line_through_building_fails(self):
        y = (-55.5 + -47.0) / 2
        self.assertFalse(A.walk_line(-480.0, y, -440.0, y))

    def test_plan_budget_is_respected(self):
        A._searches.clear()
        s, g = (500.0, -300.0, 0.0), (-450.0, 350.0, 0.0)
        t = time.perf_counter()
        A.plan(s, g, budget_ms=2.0)
        self.assertLess((time.perf_counter() - t) * 1000, 15.0)   # budget + smoothing, generous for CI noise
        # resumable: repeated calls finish it
        for _ in range(200):
            st, _ = A.plan_nodes(s, g, 0, 2.0)
            if st != "pending":
                break
        self.assertEqual(st, "ok")

    def test_cover_is_hidden(self):
        pos = (-200.0, -60.0, A.surface(-200.0, -60.0))
        thr = (-150.0, -100.0, A.surface(-150.0, -100.0))
        c = A.nearest_cover(pos, thr, 60.0, budget_ms=50)
        if c is not None:
            self.assertTrue(A._verified_hidden(c, [thr], 1.0))
            self.assertLessEqual(math.dist(c[:2], pos[:2]), 60.5)


class TestReach(unittest.TestCase):
    def test_reach_spot_for_items_near_walls_and_on_roofs(self):
        import random
        rng = random.Random(3)
        n = found = 0
        while n < 100:
            x, y = rng.uniform(-480, 530), rng.uniform(-310, 360)
            c = A.clearance(x, y)
            if 0.3 < c < 2.4 and A.surface(x, y) - A.height(x, y) < 0.5:
                z = A.height(x, y) + 0.1
                r = A.reach_spot((x, y, z), 3.5, 4.0)
                n += 1
                if r is not None:
                    found += 1
                    self.assertLessEqual(math.hypot(r[0] - x, r[1] - y), 3.5)
                    self.assertLessEqual(abs(r[2] - z), 4.0)
                    self.assertTrue(A.standable(r[0], r[1]))
        self.assertGreaterEqual(found, 95)
        # roof item -> roof spot (same level), not the street below
        y = (-55.5 + -47.0) / 2
        r = A.reach_spot((-459.0, y, A.p_top[69]), 3.5, 4.0)
        self.assertIsNotNone(r)
        self.assertGreater(r[2], A.p_top[69] - 1.0)


class TestTiming(unittest.TestCase):
    def test_shot_clear_speed(self):
        import random
        rng = random.Random(3)
        segs = []
        while len(segs) < 300:
            x, y = rng.uniform(-480, 530), rng.uniform(-310, 360)
            if A.walkable(x, y):
                a = rng.uniform(0, 6.283)
                d = rng.uniform(10, 200)
                segs.append(((x, y, A.surface(x, y) + 7), (x + d * math.cos(a), y + d * math.sin(a), A.surface(x, y) + 4.5)))
        A._los_cache.clear()
        t = time.perf_counter()
        for a, b in segs:
            A._seg_blocked(a, b)
        us = (time.perf_counter() - t) / len(segs) * 1e6
        self.assertLess(us, 250.0)


def _ids_of(k):
    import numpy as np
    return np.nonzero(A.EP == k)[0].astype(np.int32)


if __name__ == "__main__":
    unittest.main()
