#!/usr/bin/env python3
"""Build synthetic check.py streams that stress the bot (large observations, late zone, offers, drops, events).

    python3 eval/make_stress_stream.py <kit>/check/stream.jsonl.gz out_dir/

Writes:
  stress_big.jsonl.gz    600 obs: 15 visible mechs + 12 npcs, 80 projectiles, 40 pickups, 36 crates, 30 cubes,
                         40 sounds, 10 beams, many events, offers, 3 drops, late-game zone phases, moving self.
  stress_late.jsonl.gz   600 obs: small final zones (radius 25 -> 0), self outside the zone, under fire.
Feed them to check.py with --stream to measure latency and schema validity on worst-case inputs.
"""
import copy
import gzip
import json
import math
import os
import random
import sys


def load(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(l) for l in f if l.strip()]


def big_obs(base, tick, rng, late=False):
    o = copy.deepcopy(base)
    o["tick"] = tick
    o["t"] = tick / 20.0
    o["alive"] = 16 if not late else 3
    me = o["self"]
    ang = tick / 200.0
    cx, cy = -20.0, 0.0
    me["pos"] = [cx + 80 * math.cos(ang), cy + 80 * math.sin(ang), 0.5]
    me["vel"] = [-8 * math.sin(ang), 8 * math.cos(ang), 0]
    me["hp"] = max(50.0, 1400 - (tick % 400) * 3)
    me["cubes"] = (tick // 100) % 12
    me["in_zone"] = not late
    me["weapons"][1] = rng.choice([
        {"kind": "laser", "cooldown": 0, "charge": 0.2, "stats": {"damage": 315, "charge": 0.75, "min_charge": 0.15, "min_frac": 0.35, "hold_s": 2, "cooldown": 1.65, "range": 280, "pierce": 0, "charge_turn_mult": 1, "cookoff": 0.6}},
        {"kind": "lightning", "cooldown": 0, "stats": {"damage": 60, "cooldown": 0.25, "range": 45, "cone_deg": 30, "chain": 2, "chain_range": 14, "chain_falloff": 0.7, "energy": 3, "short_s": 2}},
        {"kind": "mortar", "cooldown": 1.0, "stats": {"damage": 200, "splash": 160, "splash_radius": 7, "splash_edge": 0.3, "cooldown": 2.6, "speed": 72, "gravity": 22, "ttl": 7, "knock": 16, "knock_up": 9, "drain": 45}},
        None])
    mechs = []
    for i in range(16):
        if i == me["id"]:
            continue
        a = rng.uniform(-math.pi, math.pi)
        d = rng.uniform(10, 190)
        p = [me["pos"][0] + d * math.cos(a), me["pos"][1] + d * math.sin(a), rng.uniform(-2, 30)]
        mechs.append({"id": i, "kind": "mech", "pos": p, "vel": [rng.uniform(-12, 12), rng.uniform(-12, 12), 0],
                      "aim": [rng.uniform(-3, 3), 0], "hp": rng.uniform(100, 1400), "max_hp": 1400, "cubes": rng.randint(0, 5),
                      "weapons": rng.sample(["gun", "laser", "mortar", "lightning"], 2), "charging": rng.random() < 0.2})
    for i in range(12):
        p = [rng.uniform(-400, 400), rng.uniform(-300, 300), rng.uniform(-2, 10)]
        mechs.append({"id": 100 + i, "kind": "npc", "pos": p, "vel": [1, 0, 0], "aim": [0, 0], "hp": 350, "max_hp": 350})
    o["mechs"] = mechs
    o["projectiles"] = []
    for i in range(80):
        k = rng.choice(["gun", "gun", "mortar", "npc"])
        p = [me["pos"][0] + rng.uniform(-150, 150), me["pos"][1] + rng.uniform(-150, 150), rng.uniform(0, 40)]
        dx, dy = me["pos"][0] - p[0], me["pos"][1] - p[1]
        n = math.hypot(dx, dy) or 1
        sp = {"gun": 252, "mortar": 72, "npc": 90}[k]
        o["projectiles"].append({"id": 300 + i + tick * 100, "kind": k, "pos": p, "vel": [dx / n * sp, dy / n * sp, rng.uniform(-10, 10)]})
    o["pickups"] = [{"id": 8000 + i, "kind": rng.choice(["laser", "mortar", "lightning"]),
                     "pos": [rng.uniform(-400, 400), rng.uniform(-300, 300), rng.uniform(-5, 30)]} for i in range(40)]
    o["crates"] = [{"id": 1000 + i, "pos": [rng.uniform(-400, 400), rng.uniform(-300, 300), rng.uniform(-5, 30)], "hp": 300} for i in range(36)]
    o["cubes"] = [{"id": 5000 + i, "pos": [rng.uniform(-400, 400), rng.uniform(-300, 300), rng.uniform(-5, 30)]} for i in range(30)]
    o["sounds"] = [{"kind": rng.choice(["gun", "step", "laser", "mortar", "explosion", "lightning", "boost", "death"]),
                    "bearing": rng.uniform(-3.1, 3.1), "dist": rng.choice(["near", "mid", "far"]), "age": 0.05} for _ in range(40)]
    o["beams"] = [{"by": rng.randint(0, 15), "kind": rng.choice(["laser", "lightning"]),
                   "path": [[rng.uniform(-300, 300), rng.uniform(-300, 300), 7] for _ in range(3)], "age": 0.1} for _ in range(10)]
    ev = []
    for _ in range(12):
        ev.append({"type": "damaged", "amount": rng.choice([45, 60, 200, 315]), "weapon": rng.choice(["gun", "laser", "mortar", "lightning"]),
                   "bearing": rng.uniform(-3, 3), "by": rng.randint(0, 15), "rear": rng.random() < 0.3})
    if late:
        ev.append({"type": "damaged", "amount": 26, "weapon": "zone", "bearing": None, "by": None})
    ev.append({"type": "hit", "target": rng.randint(0, 15), "amount": 45, "weapon": "gun"})
    if tick % 50 == 0:
        ev.append({"type": "kill", "target": rng.randint(0, 15)})
        ev.append({"type": "pickup", "cubes": me["cubes"]})
        ev.append({"type": "take_failed", "id": 8001, "reason": "range"})
    o["events"] = ev
    o["drops"] = [{"id": 20000 + i, "pos": [rng.uniform(-100, 100), rng.uniform(-100, 100), 0], "radius": 8,
                   "lands_in": max(0.0, 10 - i * 5), "capture_s": 4, "progress": 1.0, "holder": None} for i in range(3)]
    if late:
        r = max(0.0, 25 - (tick % 600) / 20.0)
        o["zone"] = {"center": [cx, cy], "radius": 25, "next_center": [cx + 3, cy - 2], "next_radius": 0,
                     "shrink_start": tick / 20.0 - 2, "shrink_end": tick / 20.0 + 20, "dps": 260}
    else:
        o["zone"] = {"center": [cx, cy], "radius": 240, "next_center": [cx + 30, cy - 20], "next_radius": 140,
                     "shrink_start": tick / 20.0 - 5, "shrink_end": tick / 20.0 + 30, "dps": 60}
    o["offer"] = None if tick % 120 > 40 else {"id": tick // 120, "expires": tick / 20.0 + 3, "choices": [
        {"id": "armor", "name": "Reactive armor", "desc": "-8% damage taken"},
        {"id": "nanites", "name": "Repair nanites", "desc": "+60% regen"},
        {"id": "gun_rate", "name": "Rotary feed", "desc": "+15% gun rate"}]}
    return o


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    msgs = load(src)
    hello, end = msgs[0], msgs[-1]
    base = [m for m in msgs if m.get("type") == "obs"][100]
    for name, late in (("stress_big", False), ("stress_late", True)):
        rng = random.Random(7 if late else 3)
        lines = [hello] + [big_obs(base, 2000 + 2 * i, rng, late) for i in range(600)] + [end]
        p = os.path.join(out, name + ".jsonl.gz")
        with gzip.open(p, "wt") as f:
            for m in lines:
                f.write(json.dumps(m, separators=(",", ":")) + "\n")
        print(p, max(len(json.dumps(m)) for m in lines), "bytes max line")


if __name__ == "__main__":
    main()
