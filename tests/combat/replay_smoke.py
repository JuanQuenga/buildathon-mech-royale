"""Run threats.assess + combat.step over the kit's recorded observation stream (smoke + timing).

usage: python3 tests/combat/replay_smoke.py [stream.jsonl.gz] [map_dir]
"""
import gzip, json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from bot import state as st, threats, combat  # noqa: E402

KIT = "/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/mech-royale/starter/mechfight-kit"
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KIT, "check/stream.jsonl.gz")
map_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "arena")
arena = None
try:
    from bot.arena import Arena
    t0 = time.perf_counter(); arena = Arena.load(map_dir); print("arena load %.2fs" % (time.perf_counter() - t0))
except Exception as ex:
    print("arena failed", ex)
S = None
times = []; cpu = []; fires = 0; n = 0; weps = {}
for line in gzip.open(path, "rt"):
    m = json.loads(line)
    if m.get("type") == "hello":
        S = st.WorldState(m, arena)
    elif m.get("type") == "obs":
        S.update(m)
        t0 = time.perf_counter()
        c0 = time.thread_time()
        th = threats.assess(S)
        out = combat.step(S, st.Intent(mode="engage"), th)
        cpu.append(time.thread_time() - c0)
        times.append(time.perf_counter() - t0)
        n += 1
        assert out.aim is not None and len(out.aim) == 2 and all(abs(x) < 10 for x in out.aim), out
        if any(out.fire):
            fires += 1
        weps[out.weapon] = weps.get(out.weapon, 0) + 1
times.sort()
cpu.sort()
print("obs", n, "fire decisions", fires, "weapons", weps)
print("combat+threats wall ms p50 %.3f p99 %.3f max %.3f" % (times[len(times)//2]*1e3, times[int(.99*len(times))]*1e3, times[-1]*1e3))
print("combat+threats cpu  ms p50 %.3f p99 %.3f max %.3f (thread CPU time: immune to other processes)" % (cpu[len(cpu)//2]*1e3, cpu[int(.99*len(cpu))]*1e3, cpu[-1]*1e3))
