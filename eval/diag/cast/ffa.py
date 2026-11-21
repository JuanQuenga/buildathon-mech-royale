"""Per match in a cast capture: each mech's place, kills, dmg dealt/taken, loadout, first weapon, death, and hit rates
(fire vs hit events by weapon). Usage: ffa.py capture.jsonl [name-filter]"""
import json, sys, collections
flt = sys.argv[2] if len(sys.argv) > 2 else None
hdr = None; fires = collections.Counter(); hits = collections.Counter(); air_hits = collections.Counter()
def flush(res):
    if hdr is None: return
    names = {m['id']: m.get('name') for m in hdr.get('mechs', [])}
    print(f"--- seed {hdr.get('seed')}  ticks {res.get('ticks')}")
    for m in sorted(res['mechs'], key=lambda m: m['place']):
        if flt and flt.lower() not in (m['name'] or '').lower() and m['place'] > 3: continue
        i = m['id']
        hr = {w: f"{hits[(i,w)]}/{fires[(i,w)]}" for w in ('gun', 'laser', 'lightning', 'mortar') if fires[(i, w)]}
        print(f"{m['place']:2d} {m['name'][:18]:18s} k={m['kills']} dealt={m['damage_dealt']:5d} taken={m['damage_taken']:5d} "
              f"{'+'.join(x or '-' for x in m['loadout'])} fw={m['first_weapon_t']} cubes={m['cubes_max']} death={m['death_t']} "
              f"by={names.get(m['killed_by'])}/{m['killed_with']} eff={m.get('effects')} hits={hr} ups={m.get('upgrades')}")
for l in open(sys.argv[1]):
    try: d = json.loads(l)
    except Exception: continue
    ty = d.get('type')
    if ty == 'header':
        hdr = d; fires.clear(); hits.clear()
    elif ty == 'result':
        flush(d)
    elif 'ev' in d:
        for e in d['ev']:
            if e.get('e') == 'fire': fires[(e['id'], e.get('w'))] += 1
            elif e.get('e') == 'hit' and e.get('dst', 9999) < 1000: hits[(e['src'], e.get('w'))] += 1
