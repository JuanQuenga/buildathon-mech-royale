"""Intercept maths, mortar solver, slew, hit probability; replay cross-checks.

Run: python3 -m unittest discover -s tests/combat
"""
import collections
import math
import random
import unittest

import helpers  # noqa: F401  (sets sys.path)
from bot import ballistics as B


class TestIntercept(unittest.TestCase):
    def test_lead_hits_moving_target(self):
        rng = random.Random(1)
        for _ in range(500):
            o = (rng.uniform(-5, 5), rng.uniform(-5, 5), rng.uniform(0, 10))
            d = rng.uniform(10, 220)
            a = rng.uniform(-math.pi, math.pi)
            p = (o[0] + d * math.cos(a), o[1] + d * math.sin(a), rng.uniform(-5, 20))
            v = (rng.uniform(-20, 20), rng.uniform(-20, 20), rng.uniform(-3, 3))
            sol = B.lead_aim(o, p, v, 252.0)
            self.assertIsNotNone(sol)
            yaw, pitch, tf, ap = sol
            dvec = B.aim_dir(yaw, pitch)
            bullet = (o[0] + dvec[0] * 252 * tf, o[1] + dvec[1] * 252 * tf, o[2] + dvec[2] * 252 * tf)
            target = (p[0] + v[0] * tf, p[1] + v[1] * tf, p[2] + v[2] * tf)
            self.assertLess(math.dist(bullet, target), 1e-6 * d + 1e-6)

    def test_lead_with_gravity_target(self):
        o = (0, 0, 7)
        p, v, acc = (80, 10, 15), (0, 8, 6), (0, 0, -22)
        yaw, pitch, tf, ap = B.lead_aim(o, p, v, 252.0, 0.0, acc, iters=6)
        dvec = B.aim_dir(yaw, pitch)
        bullet = [o[i] + dvec[i] * 252 * tf for i in range(3)]
        target = [p[i] + v[i] * tf + 0.5 * acc[i] * tf * tf for i in range(3)]
        self.assertLess(math.dist(bullet, target), 0.05)

    def test_unreachable(self):
        # target faster than the bullet, running away
        self.assertIsNone(B.lead_aim((0, 0, 0), (100, 0, 0), (300, 0, 0), 252.0))

    def test_closest_approach(self):
        t, d = B.closest_approach((0, -100, 5), (0, 250, 0), (3, 0, 5))
        self.assertAlmostEqual(t, 0.4, places=6)
        self.assertAlmostEqual(d, 3.0, places=6)


class TestSlew(unittest.TestCase):
    def test_clamp_and_wrap(self):
        a = B.slew((3.0, 0.0), (-3.0, 0.5), 4.0, 3.0, 0.05)
        # shortest way from 3.0 to -3.0 is +0.283 across pi; clamp to 0.2
        self.assertAlmostEqual(B.wrap(a[0] - 3.2), 0.0, places=9)
        self.assertAlmostEqual(a[1], 0.15, places=9)
        b = B.slew((0.0, 0.0), (0.05, 2.0), 4.0, 3.0, 0.1)
        self.assertAlmostEqual(b[0], 0.05)
        self.assertAlmostEqual(b[1], 0.3)
        c = B.slew((0.0, 1.2), (0.0, 2.0), 4.0, 3.0, 0.1)
        self.assertAlmostEqual(c[1], 1.3)   # pitch limit

    def test_replay_slew_limits(self):
        """Replay: |d yaw| per 0.1 s never exceeds turn_rate(x gyros 1.3) * 0.1 + rounding; pitch 0.3."""
        h, frames = helpers.load_replay()
        if not frames:
            self.skipTest("replay not available")
        prev = {}
        mx_y = mx_p = 0.0
        for fr in frames:
            for m in fr["m"]:
                if m[0] in prev and fr["t"] - prev[m[0]][0] == 2:
                    pm = prev[m[0]][1]
                    mx_y = max(mx_y, abs(B.wrap(m[4] - pm[4])))
                    mx_p = max(mx_p, abs(m[5] - pm[5]))
                prev[m[0]] = (fr["t"], m)
        self.assertLessEqual(mx_y, 4 * 1.3 * 0.1 + 0.011)
        self.assertLessEqual(mx_p, 3 * 0.1 + 0.011)
        self.assertGreater(mx_p, 0.29)   # the clamp is actually reached


class TestMortar(unittest.TestCase):
    def sim_shell(self, pos, yaw, pitch, v=72.0, g=22.0, tube=9.5, offset=3.0, ground=0.0, target=None):
        """Server model verified on the replay: shell at time tau = origin + v tau - g tau^2 / 2."""
        o = B.shot_origin(pos, yaw, pitch, tube, offset)
        t = 0.0
        best = None
        while t < 7.0:
            t += 0.005
            p = B.shell_point(o, yaw, pitch, v, g, t)
            if target is not None:
                tp = target(t)
                d = math.dist(p, tp)
                if best is None or d < best[0]:
                    best = (d, t)
            if p[2] <= ground and t > 0.05:
                return p, t, best
        return p, t, best

    def test_static_targets_low_and_high(self):
        rng = random.Random(2)
        for _ in range(200):
            d = rng.uniform(20, 225)
            a = rng.uniform(-math.pi, math.pi)
            tgt = (d * math.cos(a), d * math.sin(a), rng.uniform(-5, 15))
            for high in (False, True):
                sol = B.mortar_solve((0, 0, 0), tgt, (0, 0, 0), 72.0, 22.0, 9.5, 3.0, high)
                if sol is None:
                    continue
                yaw, pitch, tf, ip = sol
                _, _, best = self.sim_shell((0, 0, 0), yaw, pitch, ground=-100, target=lambda t: tgt)
                self.assertLess(best[0], 0.3, (d, high, best))
                self.assertAlmostEqual(best[1], tf, delta=0.05)

    def test_moving_target_lead(self):
        rng = random.Random(3)
        for _ in range(100):
            d = rng.uniform(40, 180)
            a = rng.uniform(-math.pi, math.pi)
            p0 = (d * math.cos(a), d * math.sin(a), 0.0)
            v = (rng.uniform(-8, 8), rng.uniform(-8, 8), 0.0)
            sol = B.mortar_solve((0, 0, 0), p0, v, 72.0, 22.0, 9.5, 3.0, False, iters=8)
            if sol is None:
                continue
            yaw, pitch, tf, ip = sol
            _, _, best = self.sim_shell((0, 0, 0), yaw, pitch, ground=-100,
                                        target=lambda t: (p0[0] + v[0] * t, p0[1] + v[1] * t, 0.0))
            self.assertLess(best[0], 0.5)

    def test_out_of_range(self):
        self.assertIsNone(B.mortar_solve((0, 0, 0), (400, 0, 0), (0, 0, 0), 72.0, 22.0, 9.5))

    def test_replay_shells_follow_model(self):
        """Every replay mortar shell launched while the shooter's aim was steady follows
        origin(feet + 9.5 up, 3 cos(pitch) out) + v tau - g tau^2/2 with tau from the decision tick."""
        h, frames = helpers.load_replay()
        if not frames:
            self.skipTest("replay not available")
        fmap = {fr["t"]: fr for fr in frames}
        shells = collections.defaultdict(list)
        for fr in frames:
            for p in fr["p"]:
                if p[1] == 1:
                    shells[p[0]].append((fr["t"], p[2], p[3], p[4]))
        fires = [(e["t"], e["id"]) for fr in frames for e in fr.get("ev", []) if e["e"] == "fire" and e.get("w") == "mortar"]
        n = 0
        worst = 0.0
        for ft, mid in fires:
            if ft - 1 not in fmap or ft + 1 not in fmap:
                continue
            m0 = [m for m in fmap[ft - 1]["m"] if m[0] == mid]
            m1 = [m for m in fmap[ft + 1]["m"] if m[0] == mid]
            if not m0 or not m1:
                continue
            m0, m1 = m0[0], m1[0]
            if abs(B.wrap(m1[4] - m0[4])) > 0.02 or abs(m1[5] - m0[5]) > 0.02:
                continue
            cands = [tr for tr in shells.values() if tr[0][0] == ft + 1 and math.dist(tr[0][1:3], m1[1:3]) < 15]
            if not cands:
                continue
            yaw, pitch = m1[4], m1[5]
            feet = [(m0[i] + m1[i]) / 2 for i in (1, 2, 3)]
            o = B.shot_origin(feet, yaw, pitch, 9.5, 3.0)
            for (F, x, y, z) in cands[0][:20]:
                tau = (F - (ft - 1)) * 0.05
                p = B.shell_point(o, yaw, pitch, 72.0, 22.0, tau)
                worst = max(worst, math.dist(p, (x, y, z)))
            n += 1
        self.assertGreater(n, 5)
        # residual dominated by the replay's 0.01 rad aim rounding (0.005 rad * 72 m/s * 1 s ~ 0.4 m)
        self.assertLess(worst, 1.0)


class TestHitProb(unittest.TestCase):
    def test_monotone_and_bounds(self):
        sig = math.radians(0.6)
        p50 = B.hit_probability(0, 0, 50, 2.5, 9, sig)
        p200 = B.hit_probability(0, 0, 200, 2.5, 9, sig)
        self.assertGreater(p50, 0.99)
        self.assertGreater(p50, p200)
        self.assertGreater(p200, 0.6)
        self.assertLess(B.hit_probability(5, 0, 100, 2.5, 9, sig), 0.05)

    def test_spread_matches_monte_carlo(self):
        rng = random.Random(4)
        sig = math.radians(0.6)
        d = 180.0
        hits = 0
        n = 20000
        for _ in range(n):
            ex = math.tan(rng.gauss(0, sig)) * d
            ey = math.tan(rng.gauss(0, sig)) * d
            hits += abs(ex) < 2.8 and abs(ey) < 4.8
        self.assertAlmostEqual(hits / n, B.hit_probability(0, 0, d, 2.5, 9, sig), delta=0.02)


class TestLaserDamage(unittest.TestCase):
    def test_curve(self):
        self.assertAlmostEqual(B.laser_damage(0.75, 315, 0.75, 0.35, 0.15), 315)
        self.assertAlmostEqual(B.laser_damage(0.0, 315, 0.75, 0.35, 0.15), 315 * (0.35 + 0.65 * 0.2))
        self.assertAlmostEqual(B.laser_damage(5.0, 315, 0.75, 0.35, 0.15), 315)


if __name__ == "__main__":
    unittest.main()
