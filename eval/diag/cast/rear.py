import json, sys, collections
tot = collections.Counter(); rear = collections.Counter(); place = collections.defaultdict(list); hdr=None
dmg_by_place = collections.defaultdict(lambda: [0, 0])
cur_t = collections.Counter(); cur_r = collections.Counter()
for f in sys.argv[1:]:
    for l in open(f):
        d = json.loads(l)
        if d.get('type') == 'header':
            hdr = d; names = {m['id']: m['name'] for m in d['mechs']}; cur_t.clear(); cur_r.clear()
            show = all((b or '').startswith('docker') for b in d.get('bots', []))
        elif d.get('type') == 'result' and hdr is not None and show:
            for m in d['mechs']:
                n = m['name']; a = dmg_by_place['top4' if m['place'] <= 4 else ('mid' if m['place'] <= 10 else 'low')]
                a[0] += cur_t[m['id']]; a[1] += cur_r[m['id']]
                tot[n] += cur_t[m['id']]; rear[n] += cur_r[m['id']]; place[n].append(m['place'])
        elif 'ev' in d and hdr is not None:
            for e in d['ev']:
                if e.get('e') == 'hit' and e.get('dst', 9999) < 1000:
                    cur_t[e['dst']] += e.get('amt', 0)
                    if e.get('rear'): cur_r[e['dst']] += e.get('amt', 0)
for k, (a, b) in dmg_by_place.items(): print(k, 'rear share of damage taken %.2f' % (b / max(1, a)))
for n in sorted(tot, key=lambda n: sum(place[n]) / len(place[n])):
    print(f"{n[:18]:18s} matches={len(place[n])} mean_place={sum(place[n])/len(place[n]):5.1f} rear_share={rear[n]/max(1,tot[n]):.2f}")
