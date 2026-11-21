"""Real showdowns: opening (first 30 s) damage taken/dealt, secondary by 15 s, vs final place."""
import json, sys, collections, statistics as S
seen=set(); rows=[]
for f in sys.argv[1:]:
    hdr=None
    for l in open(f):
        d=json.loads(l)
        if d.get('type')=='header':
            hdr=d; show=all((b or '').startswith('docker') for b in d.get('bots',[])); tk=collections.Counter(); dl=collections.Counter(); wt={}
        elif hdr is None or not show: continue
        elif d.get('type')=='result':
            if hdr['seed'] in seen: continue
            seen.add(hdr['seed'])
            for m in d['mechs']:
                rows.append((m['place'], m['name'], tk[m['id']], dl[m['id']], m['first_weapon_t'], m['death_t'], m['kills']))
        elif 'ev' in d:
            for e in d['ev']:
                if e.get('e')=='hit' and e['t']<=600 and e.get('dst',9999)<1000:
                    tk[e['dst']]+=e.get('amt',0); dl[e['src']]+=e.get('amt',0)
print('matches', len(seen))
for lab, sel in [('top4', lambda r: r[0]<=4), ('5-10', lambda r: 5<=r[0]<=10), ('11-16', lambda r: r[0]>=11)]:
    R=[r for r in rows if sel(r)]
    fw=sum(1 for r in R if r[4] is not None and r[4]<=15)/len(R)
    print(f"{lab}: n={len(R)} opening dmg taken med={S.median(r[2] for r in R):.0f} dealt med={S.median(r[3] for r in R):.0f} secondary<=15s={fw:.2f} died<30s={sum(1 for r in R if r[5] and r[5]<30)/len(R):.2f}")
early=[r for r in rows if r[5] and r[5]<30]
print('early deaths', len(early), 'of', len(rows), '; their opening dealt med', S.median(r[3] for r in early))
print('poteto', [r for r in rows if r[1]=='poteto'])
