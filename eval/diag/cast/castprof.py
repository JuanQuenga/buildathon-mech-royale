import json, sys, math, collections, ast
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
from bot.arena import Arena
ar=Arena.load(os.path.join(ROOT, 'arena'))
def matches(path):
    cur=None
    for l in open(path):
        l=l.strip()
        if not l: continue
        try: r=json.loads(l)
        except Exception: continue
        ty=r.get('type')
        if ty=='header':
            if cur and cur.get('done'): yield cur
            cur={'hdr':r,'frames':[],'done':False}
        elif ty=='result':
            if cur: cur['res']=r; cur['done']=True
        elif 'm' in r and cur is not None:
            cur['frames'].append(r)
    if cur and cur.get('done'): yield cur
agg=collections.defaultdict(lambda: collections.defaultdict(float))
ups=collections.defaultdict(collections.Counter)
def prof(mt):
    hdr=mt['hdr']; mechs=hdr['mechs']
    if isinstance(mechs,str): mechs=ast.literal_eval(mechs)
    name={m['id']:m['name'] for m in mechs}
    st={i:dict(life=0.0,regen=0.0,dealt=0.0,taken=0.0,still=0.0,air=0.0,wall=0.0,kills=0,drops=0,cubes=0,fast=0.0,heal_ep=0,hitd=[],tookd=[],prev=None,ep=0.0,frames=0,rear_taken=0.0,slow=0.0,fighting=0.0,last_combat=-1e9) for i in name}
    places=None
    for fr in mt['frames']:
        t=fr['t']/20.0
        pos={m[0]:m for m in fr['m']}
        for e in fr.get('ev',[]) or []:
            k=e.get('e')
            if k=='hit':
                s,d,a=e.get('src'),e.get('dst'),e.get('amt',0)
                if s in st and d in st:
                    st[s]['dealt']+=a; st[d]['taken']+=a
                    st[s]['last_combat']=t; st[d]['last_combat']=t
                    if e.get('rear'): st[d]['rear_taken']+=a
                    if s in pos and d in pos:
                        dd=math.hypot(pos[s][1]-pos[d][1],pos[s][2]-pos[d][2]); st[s]['hitd'].append(dd); st[d]['tookd'].append(dd)
                elif d in st and s is not None: st[d]['taken']+=a; st[d]['last_combat']=t
            elif k=='death':
                if e.get('by') in st and e.get('id') in st: st[e['by']]['kills']+=1
            elif k=='drop' and e.get('op')=='take' and e.get('by') in st: st[e['by']]['drops']+=1
            elif k=='upgrade' and e.get('id') in st: ups[name[e['id']]][e.get('up')]+=1
            elif k=='end': places=e.get('places')
        for i,m in pos.items():
            if i not in st: continue
            s=st[i]
            hp,maxhp=m[6],m[10]
            if hp<=0: continue
            s['life']=t; s['frames']+=1; s['cubes']=m[9]
            pv=s['prev']
            if pv is not None:
                dx,dy=m[1]-pv[1],m[2]-pv[2]; sp=math.hypot(dx,dy)/0.1
                if sp<1.0: s['still']+=0.1
                if sp<6.5: s['slow']+=0.1
                if sp>14: s['fast']+=0.1
                if not (int(m[8])&1): s['air']+=0.1
                dh=hp-pv[6]
                if dh>0 and abs(maxhp-pv[10])<1 and dh<25:   # regen tick (45 HP/s -> 4.5 per frame; nanites up to 11.5)
                    s['regen']+=dh; s['ep']+=dh
                else:
                    if s['ep']>=150: s['heal_ep']+=1
                    if dh<=0: s['ep']=0.0
                if t-s['last_combat']<3.0: s['fighting']+=0.1
                try:
                    if ar.clearance(m[1],m[2])<6.0: s['wall']+=0.1
                except Exception: pass
            s['prev']=m
    if places is None and mt.get('res'):
        places=mt['res'].get('places')
    for i,s in st.items():
        a=agg[name[i]]; L=max(1.0,s['life'])
        a['n']+=1; a['life']+=L; a['regen']+=s['regen']; a['dealt']+=s['dealt']; a['taken']+=s['taken']; a['still']+=s['still']; a['air']+=s['air']; a['wall']+=s['wall']
        a['kills']+=s['kills']; a['drops']+=s['drops']; a['cubes']+=s['cubes']; a['fast']+=s['fast']; a['heal_ep']+=s['heal_ep']; a['slow']+=s['slow']; a['fighting']+=s['fighting']; a['rear']+=s['rear_taken']
        if places: a['place']+=places[i] if isinstance(places,list) and i<len(places) else 0
        a.setdefault('hitd',[]); 
        if s['hitd']: a['hitd_sum']+=sorted(s['hitd'])[len(s['hitd'])//2]; a['hitd_n']+=1
        if s['tookd']: a['tookd_sum']+=sorted(s['tookd'])[len(s['tookd'])//2]; a['tookd_n']+=1
nm=0
for p in sys.argv[1:]:
    for mt in matches(p):
        nm+=1; prof(mt)
print("matches",nm)
rows=sorted(agg.items(), key=lambda kv: kv[1]['place']/max(1,kv[1]['n']))
print(f"{'bot':18s} n place life kills dealt/s taken/s regen/match heal_ep drops cubes still slow<6.5 fast>14 air wall<6m fight% hit_rng took_rng rear%")
for nme,a in rows:
    n=a['n']; L=a['life']
    print(f"{nme[:18]:18s} {int(n)} {a['place']/n:5.1f} {L/n:5.0f} {a['kills']/n:4.1f} {a['dealt']/L:6.1f} {a['taken']/L:6.1f} {a['regen']/n:8.0f} {a['heal_ep']/n:6.1f} {a['drops']/n:5.2f} {a['cubes']/n:5.1f} {a['still']/L:5.2f} {a['slow']/L:6.2f} {a['fast']/L:6.2f} {a['air']/L:5.2f} {a['wall']/L:6.2f} {a['fighting']/L:5.2f} {a['hitd_sum']/max(1,a['hitd_n']):6.0f} {a['tookd_sum']/max(1,a['tookd_n']):6.0f} {a['rear']/max(1,a['taken']):5.2f}")
print()
for nme,_ in rows[:8]:
    print(nme, dict(ups[nme].most_common(8)))
