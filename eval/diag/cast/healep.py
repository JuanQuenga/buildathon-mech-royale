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
            if cur and cur['frames']: yield cur
            cur={'hdr':r,'frames':[]}
        elif 'm' in r and cur is not None: cur['frames'].append(r)
    if cur and cur['frames']: yield cur
who=sys.argv[2:]
for mt in matches(sys.argv[1]):
    hdr=mt['hdr']; mechs=hdr['mechs']
    if isinstance(mechs,str): mechs=ast.literal_eval(mechs)
    name={m['id']:m['name'] for m in mechs}
    ids=[i for i,n in name.items() if any(w.lower() in n.lower() for w in who)]
    print("== match seed", hdr.get('seed'), "frames", len(mt['frames']), "watch", [name[i] for i in ids])
    for me in ids:
        ep=None; eps=[]; prev=None; last_taken=-1e9; last_dealt=-1e9; hist=[]
        for fr in mt['frames']:
            t=fr['t']/20.0
            pos={m[0]:m for m in fr['m']}
            for e in fr.get('ev',[]) or []:
                if e.get('e')=='hit':
                    if e.get('dst')==me: last_taken=t
                    if e.get('src')==me: last_dealt=t
            if me not in pos or pos[me][6]<=0: break
            m=pos[me]
            if prev is not None:
                dh=m[6]-prev[6]
                regen = dh>0 and abs(m[10]-prev[10])<1 and dh<25
                if regen:
                    if ep is None:
                        ep={'t0':t,'hp0':prev[6],'max':m[10],'gain':0.0,'dist':0.0,'near':[],'los':0,'n':0,'since_taken':t-last_taken,'since_dealt':t-last_dealt,'x0':m[1],'y0':m[2]}
                    ep['gain']+=dh; ep['n']+=1
                    ep['dist']+=math.hypot(m[1]-prev[1],m[2]-prev[2])
                    others=[(math.hypot(o[1]-m[1],o[2]-m[2]),o) for i,o in pos.items() if i!=me and i in name and o[6]>0]
                    if others:
                        d,o=min(others,key=lambda q:q[0]); ep['near'].append(d)
                        try:
                            if ar.los((o[1],o[2],o[3]+8.0),(m[1],m[2],m[3]+4.5)): ep['los']+=1
                        except Exception: pass
                elif ep is not None and dh<0:
                    ep['t1']=t; ep['hp1']=prev[6]; eps.append(ep); ep=None
            prev=m
        if ep is not None: ep['t1']=t; ep['hp1']=prev[6]; eps.append(ep)
        big=[e for e in eps if e['gain']>=100]
        print(f"  {name[me]}: {len(big)} heal episodes >=100 HP, total {sum(e['gain'] for e in big):.0f}")
        for e in big:
            nr=sorted(e['near'])[len(e['near'])//2] if e['near'] else -1
            print(f"    t={e['t0']:6.1f}-{e['t1']:6.1f} ({e['t1']-e['t0']:4.1f}s) hp {e['hp0']:5.0f}->{e['hp1']:5.0f}/{e['max']:.0f} rate {e['gain']/max(0.1,e['n']*0.1):5.1f}/s moved {e['dist']:5.0f} m  nearest enemy median {nr:4.0f} m  nearest-has-LOS {e['los']/max(1,e['n']):.2f}  started {e['since_taken']:.1f}s after last hit taken, {e['since_dealt']:.1f}s after last dealt")
