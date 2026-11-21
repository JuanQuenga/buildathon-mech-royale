"""Fatal-fight anatomy: python3 fatal.py TRACE_DIR"""
import gzip, json, os, sys, collections, math
def load(p):
    with gzip.open(p, "rt") as f:
        return [json.loads(l) for l in f]
rows=[]
for fn in sorted(os.listdir(sys.argv[1])):
    if not fn.endswith(".gz"): continue
    recs = load(os.path.join(sys.argv[1], fn)); hdr=recs[0]; res=recs[-1]
    names={m["id"]:m["name"] for m in hdr["mechs"]}
    me=[i for i,n in names.items() if not n.startswith("house")][0]
    R={m["id"]:m for m in res["mechs"]}; dt=R[me]["death_t"]; place=R[me]["place"]
    if dt is None: continue
    hz=hdr["tick_hz"]
    hp=[];hits=[];dbg=[];myh=[];kills=[]
    pos={}
    for fr in recs:
        if "m" not in fr: continue
        t=fr["t"]/hz
        if t>dt+0.2: break
        for m in fr["m"]:
            if m[0]==me: hp.append((t,m[6],m[10],m[3],m[1],m[2]))
        pos[t]={m[0]:(m[1],m[2],m[3],m[6]) for m in fr["m"]}
        for ev in fr.get("ev",[]):
            if ev["e"]=="hit" and ev["dst"]==me: hits.append((ev["t"]/hz,ev["src"],ev["amt"],ev["w"],ev.get("rear",False)))
            if ev["e"]=="death" and ev.get("by")==me and ev["id"] in names: kills.append(ev["t"]/hz)
        if "dbg" in fr and str(me) in fr["dbg"]: dbg.append((t,fr["dbg"][str(me)].get("label","")))
    # last time at >=90% hp
    tfull=0
    for t,h,mx,*_ in hp:
        if h>=0.9*mx: tfull=t
    win=[h for h in hits if h[0]>=tfull]
    att=collections.Counter(); rear=0; tot=0
    for t,s,a,w,r in win:
        att[(names.get(s,s) if isinstance(s,int) else s)]+=a; tot+=a; rear+=a if r else 0
    k_in=len([k for k in kills if k>=tfull])
    # hp at kill times / heal cycles: count times hp dropped below 50% and recovered above 90%
    rec=0; low=False
    for t,h,mx,*_ in hp:
        if h<0.5*mx: low=True
        elif h>=0.9*mx and low: rec+=1; low=False
    modes=collections.Counter(l.split(" ")[0] for t,l in dbg if t>=tfull)
    lastlab=[l for t,l in dbg[-30::6]]
    z=hp[-1][3]
    rows.append((16-place,fn,round(dt),round(dt-tfull),len(att),dict(att),round(rear/max(1,tot),2),k_in,rec,round(z,1),dict(modes),lastlab))
for r in sorted(rows):
    print(r[:11]); print("     ", r[11])
