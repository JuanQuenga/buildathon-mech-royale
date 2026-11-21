"""print a per-second log of our bot vs its attackers: python3 duel.py TRACE [t0 t1]"""
import gzip, json, sys, math, collections
recs=[json.loads(l) for l in gzip.open(sys.argv[1],'rt')]
hdr=recs[0]; names={m["id"]:m["name"] for m in hdr["mechs"]}
me=[i for i,n in names.items() if not n.startswith("house")][0]
t0=float(sys.argv[2]) if len(sys.argv)>2 else 0; t1=float(sys.argv[3]) if len(sys.argv)>3 else 1e9
hz=hdr["tick_hz"]; acc=collections.defaultdict(float); lab=""; sec=None
for fr in recs:
    if "m" not in fr: continue
    t=fr["t"]/hz
    for ev in fr.get("ev",[]):
        if ev["e"]=="hit" and (ev["dst"]==me or ev["src"]==me) and ev["dst"] in names:
            k=("in" if ev["dst"]==me else "out")+("R" if ev.get("rear") else "")
            acc[k]+=ev["amt"]; acc["n"+k]+=1
        if ev["e"]=="fire" and ev["id"]==me: acc["shots"]+=1
        if ev["e"]=="death" and ev["id"] in names: acc["DEATH %s by %s"%(ev["id"],ev["by"])]=1
    if "dbg" in fr and str(me) in fr["dbg"]: lab=fr["dbg"][str(me)].get("label","")
    if t<t0 or t>t1: continue
    if sec is None or int(t)!=sec:
        sec=int(t)
        M={m[0]:m for m in fr["m"]}
        if me not in M: print("dead"); break
        mm=M[me]
        near=sorted(((math.hypot(m[1]-mm[1],m[2]-mm[2]),m) for i,m in M.items() if i!=me))[:3]
        eng=fr.get("eng",[])
        ns=" ".join(f"{names[m[0]].split(':')[1][:2]}{m[0]}{'*' if m[0] in eng else ''}@{d:.0f}m hp{m[6]} z{m[3]:.0f}" for d,m in near)
        print(f"{t:6.1f} hp{mm[6]:5}/{mm[10]} e{mm[7]:5} z{mm[3]:5.1f} w{mm[11]},{mm[12]} | {ns} | {dict((k,round(v)) for k,v in acc.items())} | {lab}")
        acc=collections.defaultdict(float)
