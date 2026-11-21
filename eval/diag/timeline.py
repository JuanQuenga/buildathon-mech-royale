"""Per-match squad timelines from sim traces: python3 timeline.py TRACE_DIR [--detail]"""
import gzip, json, os, sys, collections, math

def load(p):
    with gzip.open(p, "rt") as f:
        return [json.loads(l) for l in f]

def analyse(p):
    recs = load(p)
    hdr = recs[0]; res = recs[-1]
    names = {m["id"]: m["name"] for m in hdr["mechs"]}
    me = [i for i, n in names.items() if not n.startswith("house")][0]
    tick_hz = hdr["tick_hz"]
    frames = [r for r in recs if "m" in r]
    hits_on_me = []  # (t, src, amt, w)
    my_hits = []
    deaths = []  # (t, id, by)
    eng_t = []   # (t, n_eng)
    hp_t = []
    last_eng = None
    first_eng = {}
    seen_frac = [0, 0]
    pos_me = []
    for fr in frames:
        t = fr["t"] / tick_hz
        for ev in fr.get("ev", []):
            if ev["e"] == "hit" and ev["dst"] == me:
                hits_on_me.append((ev["t"] / tick_hz, ev["src"], ev["amt"], ev["w"]))
            elif ev["e"] == "hit" and ev["src"] == me and ev["dst"] in names:
                my_hits.append((ev["t"] / tick_hz, ev["dst"], ev["amt"], ev["w"]))
            elif ev["e"] == "death" and ev["id"] in names:
                deaths.append((ev["t"] / tick_hz, ev["id"], ev["by"]))
        if "eng" in fr:
            n = len(fr["eng"])
            for h in fr["eng"]:
                first_eng.setdefault(h, t)
            if n != last_eng:
                eng_t.append((round(t, 1), n)); last_eng = n
            seen_frac[0] += 1 if fr.get("seen") else 0
            seen_frac[1] += 1
        for m in fr["m"]:
            if m[0] == me:
                hp_t.append((t, m[6], m[10], m[9], m[12]))
                pos_me.append((t, m[1], m[2], m[3]))
    R = {m["id"]: m for m in res["mechs"]}
    mr = R[me]
    dt = mr["death_t"]
    kills = [(t, i) for t, i, by in deaths if by == me]
    other_house_deaths = [(t, i, by) for t, i, by in deaths if i != me and by != me and (dt is None or t < dt)]
    # attackers in last 15 s before death
    att = collections.Counter()
    if dt is not None:
        for t, s, a, w in hits_on_me:
            if t > dt - 15:
                att[s] += a
    # time we spent engaged by >=2 bots who actually hit us
    out = dict(seed=hdr["seed"], me=me, place=mr["place"], pts=16 - mr["place"] if mr["place"] else None,
               death_t=dt, killed_by=mr["killed_by"], killed_with=mr["killed_with"], kills=len(kills),
               kill_t=[round(t) for t, _ in kills], other_deaths_before=[(round(t), names[i].split(":")[-1], by) for t, i, by in other_house_deaths],
               attackers_last15=len(att), att_names=[names.get(s, s).split(":")[-1] if isinstance(s, int) else s for s in att],
               eng=eng_t[:12], seen_frac=round(seen_frac[0] / max(1, seen_frac[1]), 2),
               cubes=mr["cubes"], loadout=mr["loadout"], dmg_dealt=mr["damage_dealt"], dmg_taken=mr["damage_taken"],
               hp_samples=[(round(t), h) for (t, h, mx, c, s1) in hp_t[::200]],
               first_hit=round(hits_on_me[0][0], 1) if hits_on_me else None)
    # all deaths in match (with --full)
    out["all_deaths"] = sorted((round(t), names[i].split(":")[-1], ("ME" if by == me else ("zone" if by is None else (names.get(by, by) if isinstance(by, int) else by)))) for t, i, by in deaths if i != me)
    return out

if __name__ == "__main__":
    d = sys.argv[1]
    rows = [analyse(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith(".gz")]
    json.dump(rows, open(os.path.join(d, "..", "timelines.json"), "w"), default=str)
    for r in sorted(rows, key=lambda r: r["pts"] or 0):
        print(f"s{r['seed']:>2} pts {r['pts']:>2} death {r['death_t'] and round(r['death_t'])!s:>4} kills {r['kills']} at {r['kill_t']} "
              f"by {r['killed_with']} att15={r['attackers_last15']}{r['att_names']} firsthit {r['first_hit']} seen {r['seen_frac']} cubes {r['cubes']} {r['loadout']} "
              f"other<{[x for x in r['other_deaths_before']]}")
