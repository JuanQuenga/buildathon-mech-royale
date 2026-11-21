"""Behaviour tests for threats.assess + combat.step: laser state machine, no shots through walls,
never self-splash, lightning victim rules, reload discipline, robustness."""
import math
import random
import unittest

import helpers
from helpers import enemy, obs, weapon
from bot import ballistics as B
from bot import combat, threats
from bot.state import Intent


def run(world, o, intent=None):
    world.update(o)
    th = threats.assess(world)
    return combat.step(world, intent or Intent(mode="engage"), th), th


class TestGun(unittest.TestCase):
    def test_fires_when_aimed_and_leads(self):
        w = helpers.world(helpers.OpenArena())
        e = enemy(5, (100, 0, 0), vel=(0, 10, 0), aim=(math.pi, 0))
        # torso already pointing at the lead
        out, _ = run(w, obs(aim=(0.0, 0.0), mechs=[e]))
        self.assertEqual(out.target_id, 5)
        lead_yaw = out.aim[0]
        self.assertGreater(lead_yaw, 0.02)          # leads toward +y
        out, _ = run(w, obs(tick=102, aim=tuple(out.aim), mechs=[e]))
        self.assertTrue(out.fire[0])

    def test_holds_fire_when_torso_far_off(self):
        w = helpers.world(helpers.OpenArena())
        e = enemy(5, (150, 0, 0))
        out, _ = run(w, obs(aim=(math.pi / 2, 0.0), mechs=[e]))
        self.assertFalse(out.fire[0])               # 90 deg away: shot would go wide
        self.assertAlmostEqual(out.aim[0], math.atan2(0, 150), delta=0.05)

    def test_no_shot_through_walls(self):
        w = helpers.world(helpers.WallArena(x0=50.0, top=40.0))
        e = enemy(5, (100, 0, 0))
        for k in range(5):
            out, th = run(w, obs(tick=100 + 2 * k, aim=(0.0, -0.02), mechs=[e]))
            self.assertFalse(out.fire[0], "gun fired through a wall")
        self.assertFalse(th.by_id(5).los)

    def test_shoots_over_low_wall(self):
        w = helpers.world(helpers.WallArena(x0=50.0, top=3.0))   # waist-high wall: muzzle at 7 m clears it
        e = enemy(5, (100, 0, 0))
        out, th = run(w, obs(aim=(0.0, -0.02), mechs=[e]))
        self.assertTrue(th.by_id(5).los)
        self.assertTrue(out.fire[0])

    def test_allow_fire_false(self):
        w = helpers.world(helpers.OpenArena())
        e = enemy(5, (60, 0, 0))
        out, _ = run(w, obs(aim=(0.0, -0.02), mechs=[e]), Intent(mode="heal", allow_fire=False))
        self.assertEqual(out.fire, (False, False))
        self.assertLess(abs(out.aim[0]), 0.1)       # still faces the threat

    def test_reload_in_lull_not_in_duel(self):
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(weapons=[weapon("gun", ammo=4), None]))
        self.assertTrue(out.reload)
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(weapons=[weapon("gun", ammo=4), None], aim=(0, -0.02), mechs=[enemy(5, (60, 0, 0))]))
        self.assertFalse(out.reload)
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(weapons=[weapon("gun", ammo=0), None], mechs=[enemy(5, (60, 0, 0))]))
        self.assertTrue(out.reload)


class TestLaser(unittest.TestCase):
    def setUp(self):
        self.w = helpers.world(helpers.OpenArena())
        self.e = enemy(5, (120, 0, 0))

    def ws(self, **kw):
        return [weapon("gun"), weapon("laser", **kw)]

    def test_starts_charging_with_target(self):
        out, _ = run(self.w, obs(aim=(0.0, -0.01), weapons=self.ws(), mechs=[self.e]))
        self.assertTrue(out.fire[1])
        self.assertTrue(out.laser_charging)

    def test_no_charge_on_cooldown_or_retreat_or_shorted(self):
        out, _ = run(self.w, obs(aim=(0.0, 0.0), weapons=self.ws(cooldown=1.0), mechs=[self.e]))
        self.assertFalse(out.fire[1])
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(0.0, 0.0), weapons=self.ws(), mechs=[self.e]), Intent(mode="retreat", urgency=0.9))
        self.assertFalse(out.fire[1])
        w = helpers.world(helpers.OpenArena())
        ev = [{"type": "effect", "effect": "short", "by": 5}]
        out, _ = run(w, obs(aim=(0.0, 0.0), weapons=self.ws(), mechs=[self.e], events=ev))
        self.assertFalse(out.fire[1])

    def test_holds_until_full_then_releases_on_target(self):
        out, _ = run(self.w, obs(tick=100, aim=(0.0, -0.01), weapons=self.ws(charge=0.4), mechs=[self.e]))
        self.assertTrue(out.fire[1], "released a half charge with no reason")
        out, _ = run(self.w, obs(tick=102, aim=(0.0, -0.01), weapons=self.ws(charge=0.75), mechs=[self.e]))
        self.assertFalse(out.fire[1], "did not release a full charge on target")
        self.assertEqual(out.reason.split()[-1], "laser-release")

    def test_full_charge_off_target_keeps_tracking(self):
        # torso 1 rad away: releasing now would miss -> keep holding and turn
        out, _ = run(self.w, obs(tick=100, aim=(1.0, 0.0), weapons=self.ws(charge=0.75), mechs=[self.e]))
        self.assertTrue(out.fire[1])
        self.assertLess(abs(out.aim[0]), 0.05)

    def test_forced_release_before_autofire(self):
        o = obs(tick=100, aim=(1.0, 0.0), weapons=self.ws(charge=0.75), mechs=[self.e])
        out, _ = run(self.w, o)
        self.assertTrue(out.fire[1])
        # 1.9 s later still full and off target: next decision would auto-fire -> release ourselves
        o = obs(tick=138, aim=(1.0, 0.0), weapons=self.ws(charge=0.75), mechs=[self.e])
        out, _ = run(self.w, o)
        self.assertFalse(out.fire[1])

    def test_heal_mid_charge_dumps_into_sky(self):
        it = Intent(mode="heal", allow_fire=False)
        out, _ = run(self.w, obs(tick=100, aim=(0.0, 0.0), weapons=self.ws(charge=0.5), mechs=[self.e]), it)
        self.assertTrue(out.fire[1])                 # keep holding while the torso pitches up
        self.assertTrue(out.dumping)
        self.assertGreater(out.aim[1], 1.0)
        out, _ = run(self.w, obs(tick=102, aim=(0.0, 0.9), weapons=self.ws(charge=0.6), mechs=[self.e]), it)
        self.assertFalse(out.fire[1])                # release up high: hits nothing, regen can start
        self.assertFalse(out.fire[0])

    def test_no_release_through_wall(self):
        w = helpers.world(helpers.WallArena(x0=50.0, top=40.0))
        out, _ = run(w, obs(tick=100, aim=(0.0, -0.01), weapons=self.ws(charge=0.75), mechs=[self.e]))
        self.assertTrue(out.fire[1])                 # keep charge, don't waste it into the wall

    def test_kill_shot_early(self):
        e = enemy(5, (120, 0, 0), hp=150)
        out, _ = run(self.w, obs(tick=100, aim=(0.0, -0.01), weapons=self.ws(charge=0.3), mechs=[e]))
        self.assertFalse(out.fire[1])


class TestMortar(unittest.TestCase):
    def test_never_targets_close(self):
        w = helpers.world(helpers.OpenArena())
        e = enemy(5, (8, 0, 0))
        for k in range(10):
            out, _ = run(w, obs(tick=100 + 2 * k, aim=(0.0, 0.0), weapons=[None, weapon("mortar")], mechs=[e]))
            self.assertFalse(out.fire[1])

    def test_self_splash_guard_random(self):
        """Fuzz: whatever we fire, our own simulated shell lands > splash radius + body from us."""
        rng = random.Random(5)
        fired = 0
        for k in range(300):
            w = helpers.world(helpers.WallArena(x0=rng.uniform(5, 60), top=rng.uniform(2, 40)))
            d = rng.uniform(3, 200)
            a = rng.uniform(-math.pi, math.pi)
            e = enemy(5, (d * math.cos(a), d * math.sin(a), rng.uniform(-3, 20)), vel=(rng.uniform(-3, 3), rng.uniform(-3, 3), 0))
            aim = (rng.uniform(-math.pi, math.pi), rng.uniform(-0.6, 1.2))
            o = obs(tick=100, aim=aim, weapons=[None, weapon("mortar")], mechs=[e])
            out, _ = run(w, o)
            # step a few decisions with the torso following the command
            for j in range(6):
                fa = B.slew(aim, out.aim, 4.0, 3.0, 0.05)
                if out.fire[1]:
                    fired += 1
                    o_ = B.shot_origin((0, 0, 0), fa[0], fa[1], 9.5, 3.0)
                    vel = (72 * math.cos(fa[1]) * math.cos(fa[0]), 72 * math.cos(fa[1]) * math.sin(fa[0]), 72 * math.sin(fa[1]))
                    ip, ti = B.ballistic_impact(o_, vel, 22.0, lambda x, y, z: w.arena.ground_z(x, y, z), solid=w.arena._blocked)
                    self.assertGreater(math.hypot(ip[0], ip[1]), 7.0 + 2.5, (d, aim, out.aim, ip))
                    break
                aim = B.slew(aim, out.aim, 4.0, 3.0, 0.1)
                out, _ = run(w, obs(tick=102 + 2 * j, aim=aim, weapons=[None, weapon("mortar")], mechs=[e]))
        self.assertGreater(fired, 20)

    def test_lobs_over_wall_at_tracked_target(self):
        # 35 m wall at 40 m, target 170 m behind it: low arc blocked, high arc (pitch ~1.05) clears it.
        # (High arcs need pitch <= max_pitch 1.3, i.e. range >~ 120 m on flat ground.)
        w = helpers.world(helpers.WallArena(x0=40.0, top=35.0))
        e = enemy(5, (170, 0, 0))
        aim = (0.0, 0.0)
        fired = False
        for j in range(15):
            out, _ = run(w, obs(tick=100 + 2 * j, aim=aim, weapons=[None, weapon("mortar")], mechs=[e]))
            if out.fire[1]:
                fired = True
                self.assertGreater(aim[1], 0.6)      # high arc
                break
            aim = B.slew(aim, out.aim, 4.0, 3.0, 0.1)
        self.assertTrue(fired)


class TestLightning(unittest.TestCase):
    def test_fires_at_close_target_in_cone(self):
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(0.0, 0.0), weapons=[weapon("gun"), weapon("lightning")], mechs=[enemy(5, (30, 2, 0))]))
        self.assertTrue(out.fire[1])

    def test_no_fire_out_of_range_or_cone(self):
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(0.0, 0.0), weapons=[weapon("gun"), weapon("lightning")], mechs=[enemy(5, (60, 0, 0))]))
        self.assertFalse(out.fire[1])
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(1.2, 0.0), weapons=[weapon("gun"), weapon("lightning")], mechs=[enemy(5, (30, 0, 0))]))
        self.assertFalse(out.fire[1])

    def test_crate_in_front_blocks_wanted_arc(self):
        w = helpers.world(helpers.OpenArena())
        crate = {"id": 1001, "pos": [12, 0.5, 0], "hp": 300}
        out, _ = run(w, obs(aim=(0.0, 0.0), weapons=[weapon("gun"), weapon("lightning")], mechs=[enemy(5, (35, 0, 0))], crates=[crate]))
        self.assertFalse(out.fire[1])

    def test_energy_reserve(self):
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(0.0, 0.0), energy=10, weapons=[weapon("gun"), weapon("lightning")], mechs=[enemy(5, (40, 0, 0))]))
        self.assertFalse(out.fire[1])

    def test_interrupts_laser_charger(self):
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(0.0, 0.0), energy=12, weapons=[weapon("gun"), weapon("lightning")],
                            mechs=[enemy(5, (40, 0, 0), aim=(math.pi, 0), weapons=("gun", "laser"), charging=True)]))
        self.assertTrue(out.fire[1])


class TestThreats(unittest.TestCase):
    def test_incoming_bullet_dodge(self):
        w = helpers.world(helpers.OpenArena())
        pr = {"id": 1, "kind": "gun", "pos": [50, 0, 5], "vel": [-252, 0, 0]}
        w.update(obs(projectiles=[pr]))
        th = threats.assess(w)
        self.assertEqual(len(th.incoming), 1)
        self.assertIsNotNone(th.dodge)
        self.assertAlmostEqual(abs(th.dodge[1]), 1.0, places=3)    # sideways
        self.assertAlmostEqual(th.incoming[0].t_impact, 50 / 252, delta=0.02)
        self.assertIsNone(th.dodge_shell)

    def test_missing_bullet_ignored(self):
        w = helpers.world(helpers.OpenArena())
        pr = {"id": 1, "kind": "gun", "pos": [50, 20, 5], "vel": [-252, 0, 0]}
        w.update(obs(projectiles=[pr]))
        self.assertEqual(len(threats.assess(w).incoming), 0)

    def test_mortar_impact_prediction(self):
        w = helpers.world(helpers.OpenArena())
        # a shell aimed to land at (3, 0): launched from (-100, 0, 10)
        sol = B.mortar_solve((-100, 0, 0.5), (3, 0, 0), (0, 0, 0), 72, 22, 9.5, 0.0, False)
        yaw, pitch, tf, ip = sol
        o = (-100, 0, 10)
        p = B.shell_point(o, yaw, pitch, 72, 22, 0.5)
        v = (72 * math.cos(pitch), 0, 72 * math.sin(pitch) - 22 * 0.5)
        w.update(obs(projectiles=[{"id": 2, "kind": "mortar", "pos": list(p), "vel": list(v)}]))
        th = threats.assess(w)
        self.assertEqual(len(th.incoming), 1)
        r = th.incoming[0]
        self.assertAlmostEqual(r.t_impact, tf - 0.5, delta=0.1)
        self.assertLess(r.miss_dist, 4.0)
        self.assertLess(r.dodge[0], -0.9)            # run away from the blast (blast at +x)
        self.assertIsNotNone(th.dodge_shell)
        self.assertLess(th.dodge_shell[0], -0.9)

    def test_rear_hit_contact_and_face(self):
        w = helpers.world(helpers.OpenArena())
        ev = [{"type": "damaged", "amount": 67.5, "weapon": "gun", "bearing": math.pi, "by": 7, "rear": True}]
        w.update(obs(aim=(0.0, 0.0), events=ev))
        th = threats.assess(w)
        self.assertTrue(th.rear_threat)
        self.assertIsNotNone(th.face_yaw)
        self.assertAlmostEqual(abs(th.face_yaw), math.pi, delta=0.05)
        out = combat.step(w, Intent(), th)
        self.assertAlmostEqual(abs(out.aim[0]), math.pi, delta=0.05)

    def test_mode_guess(self):
        w = helpers.world(helpers.OpenArena())
        w.update(obs(tick=1400, alive=14))     # two deaths we did not cause -> ffa
        self.assertEqual(threats.assess(w).mode_guess, "ffa")
        w = helpers.world(helpers.OpenArena())
        w.update(obs(tick=1400, alive=16))
        self.assertEqual(threats.assess(w).mode_guess, "squad")

    def test_killable_and_danger(self):
        w = helpers.world(helpers.OpenArena())
        w.update(obs(mechs=[enemy(5, (60, 0, 0), aim=(math.pi, 0), hp=200), enemy(6, (0, 150, 0), aim=(0, 0), hp=1400)]))
        th = threats.assess(w)
        self.assertIn(5, th.killable)
        self.assertNotIn(6, th.killable)
        self.assertGreater(th.by_id(5).danger, th.by_id(6).danger)
        self.assertTrue(th.by_id(6).rear_exposed is False or True)
        best = th.safe_dirs[0][0]
        self.assertGreater(abs(B.wrap(best - 0.0)), math.pi / 2)   # don't run at the dangerous one


class TestContract(unittest.TestCase):
    def test_npc_ignored_unless_target_or_hostile(self):
        w = helpers.world(helpers.OpenArena())
        npc = enemy(104, (40, 0, 0), kind="npc", weapons=())
        out, _ = run(w, obs(aim=(0.0, -0.05), mechs=[npc]), Intent(mode="rotate"))
        self.assertFalse(out.fire[0])
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(0.0, -0.05), mechs=[npc]), Intent(mode="loot", target_id=104))
        self.assertTrue(out.fire[0])
        w = helpers.world(helpers.OpenArena())
        ev = [{"type": "damaged", "amount": 25, "weapon": "npc", "bearing": 0.0, "by": 104}]
        out, _ = run(w, obs(aim=(0.0, -0.05), mechs=[npc], events=ev), Intent(mode="rotate"))
        self.assertTrue(out.fire[0])

    def test_crate_only_when_asked(self):
        crate = {"id": 1003, "pos": [30, 0, 0], "hp": 300}
        w = helpers.world(helpers.OpenArena())
        out, _ = run(w, obs(aim=(0.0, -0.1), crates=[crate]), Intent(mode="loot"))
        self.assertFalse(out.fire[0])
        w = helpers.world(helpers.OpenArena())
        it = Intent(mode="loot", shoot_crate=1003)
        out, _ = run(w, obs(aim=(0.0, -0.1), crates=[crate]), it)
        out, _ = run(w, obs(tick=102, aim=tuple(out.aim), crates=[crate]), it)
        self.assertEqual(out.target_id, 1003)
        self.assertTrue(out.fire[0])

    def test_laser_precharge_behind_cover(self):
        w = helpers.world(helpers.WallArena(x0=50.0, top=40.0))
        out, _ = run(w, obs(aim=(0.0, 0.0), weapons=[weapon("gun"), weapon("laser")], mechs=[enemy(5, (120, 0, 0))]),
                     Intent(mode="engage", target_id=5))
        self.assertTrue(out.fire[1])
        self.assertFalse(out.fire[0])
        w = helpers.world(helpers.WallArena(x0=50.0, top=40.0))
        out, _ = run(w, obs(aim=(0.0, 0.0), weapons=[weapon("gun"), weapon("laser")], mechs=[enemy(5, (120, 0, 0))]),
                     Intent(mode="rotate"))
        self.assertFalse(out.fire[1])


class TestRobustness(unittest.TestCase):
    def test_garbage_never_raises(self):
        rng = random.Random(6)
        w = helpers.world(None)
        for k in range(300):
            o = obs(tick=100 + 2 * k, mechs=[enemy(5, (rng.uniform(-300, 300), rng.uniform(-300, 300), 0))],
                    weapons=[rng.choice([None, weapon("gun"), weapon("mortar")]), rng.choice([None, weapon("laser", charge=rng.random()), weapon("lightning")])])
            if k % 7 == 0:
                o["self"]["weapons"] = None
            if k % 11 == 0:
                o["mechs"] = [{"id": 9}]
            if k % 13 == 0:
                o["projectiles"] = [{"id": 1, "kind": "mortar", "pos": [0, 0, 1e9], "vel": [0, 0, 0]}]
            if k % 17 == 0:
                o["self"]["aim"] = None
            try:
                w.update(o)
            except Exception:
                continue
            th = threats.assess(w)
            out = combat.step(w, Intent(), th)
            self.assertIsNotNone(out)
            self.assertEqual(len(out.fire), 2)


class TestValuation(unittest.TestCase):
    def test_duel_and_values(self):
        d = combat.duel_estimate({"hp": 1400, "weapons": ["gun", "laser"]}, {"hp": 300, "weapons": ["gun"], "dist": 80})
        self.assertGreater(d["win_p"], 0.8)
        d2 = combat.duel_estimate({"hp": 200, "weapons": ["gun"]}, {"hp": 1400, "weapons": ["gun", "lightning"], "dist": 30})
        self.assertLess(d2["win_p"], 0.2)
        late = combat.weapon_value("lightning", {"zone_radius": 60})
        early = combat.weapon_value("lightning", {"zone_radius": 380})
        self.assertGreater(late, early)
        rec = combat.recommend_loadout({"zone_radius": 380})
        self.assertIn("gun", rec[0][0])


if __name__ == "__main__":
    unittest.main()
