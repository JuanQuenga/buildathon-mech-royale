#!/usr/bin/env python3
"""Paired-seed comparison of two bot commits in the local proxy sim (squad and/or FFA mode).

    python3 eval/compare.py BASE CAND [--modes squad,ffa] [--seeds 0-23] [--jobs 8] [--log]

BASE/CAND: git refs (commit, tag, branch) or the word "example" for the kit's example bot. Each ref is checked out
into a temporary worktree so the shared working tree is never touched. Per mode, both bots play the same seeds;
the script prints mean (16 - place), the paired difference with a bootstrap 95% CI, death-cause breakdown,
missed replies / tracebacks, and with --log appends a row to eval/RESULTS.md.

The sim runner is invoked through RUNNER (env MECH_RUNNER overrides), formatted with
{bot} {mode} {seeds} {out} {jobs} {root}.
"""
import argparse
import json
import os
import random
import shlex
import statistics
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.environ.get("MECH_KIT", "/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/mech-royale/starter/mechfight-kit")
PY = os.environ.get("PY", "/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/venv/bin/python")
if not os.path.exists(PY):
    PY = sys.executable
RUNNER = os.environ.get("MECH_RUNNER",
                        PY + " {root}/sim/run_matches.py --quiet --mode {mode} --bot {bot} --seeds {seeds} --out {out} --jobs {jobs} --logs {logs} {extra}")
FFA_SPEC = os.environ.get("MECH_FFA", "bot*1,builtin:expert*5,builtin:hard*5,builtin:brawler*3,builtin:sniper*2")


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, text=True, capture_output=True, **kw).stdout.strip()


def worktree(ref, tmp):
    if ref == "example":
        return None, "example"
    sha = sh(["git", "-C", REPO, "rev-parse", "--short=10", ref])
    path = os.path.join(tmp, "wt-" + sha)
    if not os.path.exists(path):
        sh(["git", "-C", REPO, "worktree", "add", "-q", "--detach", path, sha])
    return path, sha


ENV = {"base": "", "cand": ""}


def bot_cmd(path, tag=""):
    if path is None:
        return f"{PY} -u {KIT}/python/example_bot.py"
    env = ENV.get(tag) or ""
    pre = f"env {env} " if env else ""
    return f"{pre}{PY} -u {path}/bot/main.py"


SIM_ROOT = REPO


def run(ref_path, mode, seeds, jobs, tmp, tag):
    """Returns one row per tracked-bot sample: seed, place, score, death_t, cause, kills, missed, late, tracebacks."""
    out = os.path.join(tmp, f"{tag}-{mode}.jsonl")
    logs = os.path.join(tmp, f"logs-{tag}-{mode}")
    sim_root = SIM_ROOT  # a committed sim (worktree) so both bots face the same opponents
    extra = f"--ffa {shlex.quote(FFA_SPEC)}" if mode == "ffa" else ""
    cmd = RUNNER.format(bot=shlex.quote(bot_cmd(ref_path, tag)), mode=mode, seeds=seeds, out=out, jobs=jobs, root=sim_root,
                        logs=logs, extra=extra)
    t0 = time.time()
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=sim_root)
    if p.returncode != 0:
        print(p.stdout[-2000:], p.stderr[-4000:], file=sys.stderr)
        raise SystemExit(f"runner failed for {tag} {mode}")
    tb = 0
    summaries = []
    for dp, _, fs in os.walk(logs):
        for fn in fs:
            try:
                with open(os.path.join(dp, fn), errors="replace") as f:
                    txt = f.read()
            except OSError:
                continue
            tb += txt.count("Traceback")
            for line in txt.splitlines():
                if line.startswith("stats {"):
                    try:
                        summaries.append(json.loads(line[6:]))
                    except ValueError:
                        pass
    def _print_summaries():
        if not summaries:
            return
        modes, guess, fb, p99 = {}, {}, 0, []
        for sm in summaries:
            b = sm.get("brain") or {}
            for k, v in (b.get("modes") or {}).items():
                modes[k] = modes.get(k, 0) + v
            g = b.get("mode_guess", "?")
            guess[g] = guess.get(g, 0) + 1
            fb += int(sm.get("fallbacks", 0) or 0)
            p99.append(float(sm.get("p99_ms", 0) or 0))
        tot = max(1, sum(modes.values()))
        print(f"    [{tag}] brain modes " + " ".join(f"{k}:{100 * v / tot:.0f}%" for k, v in sorted(modes.items(), key=lambda x: -x[1]))
              + f"  round guess at death {guess}  fallbacks {fb}  bot p99 max {max(p99):.1f}ms")
    rows = []
    with open(out) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if "error" in r:
                print(f"  sim error seed {r.get('seed')}: {r['error'][:300]}", file=sys.stderr)
                continue
            if "mechs" not in r:  # flat format: one row per tracked bot
                if "place" not in r:
                    continue
                rows.append({"seed": r["seed"], "place": r["place"], "score": 16 - r["place"], "death_t": r.get("death_t"),
                             "death_cause": r.get("death_cause") or "survived", "kills": r.get("kills", 0),
                             "missed_replies": r.get("missed_replies", 0), "late": r.get("late_replies", 0),
                             "cubes": r.get("cubes", 0), "zone_dmg": r.get("zone_dmg", 0),
                             "tracebacks": int(r.get("bot_stderr_tracebacks", 0) or 0)})
                continue
            for m in r.get("mechs") or []:
                if not m.get("tracked"):
                    continue
                cause = m.get("killed_with") or "survived"
                if cause == "zone":
                    cause = "zone"
                elif m.get("killed_by") is None and cause != "survived":
                    cause = "other:" + str(cause)
                rows.append({"seed": r["seed"], "place": m["place"], "score": 16 - m["place"], "death_t": m.get("death_t"),
                             "death_cause": cause, "kills": m.get("kills", 0), "missed_replies": m.get("missed", 0),
                             "late": m.get("late", 0), "cubes": m.get("cubes", 0), "zone_dmg": m.get("zone_dmg", 0)})
    _print_summaries()
    if rows and "tracebacks" not in rows[0]:
        rows[0]["tracebacks"] = tb
    return rows, time.time() - t0


def score(r):
    if "score" in r:
        return float(r["score"])
    return 16.0 - float(r["place"])


def boot_ci(diffs, n=4000, seed=0):
    if not diffs:
        return (0.0, 0.0)
    rng = random.Random(seed)
    k = len(diffs)
    means = sorted(sum(rng.choice(diffs) for _ in range(k)) / k for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def causes(rows):
    c = {}
    for r in rows:
        k = str(r.get("death_cause") or r.get("cause") or ("survived" if r.get("place") == 1 else "unknown"))
        c[k] = c.get(k, 0) + 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("cand")
    ap.add_argument("--modes", default="squad,ffa")
    ap.add_argument("--seeds", default="0-23")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--log", action="store_true", help="append the result to eval/RESULTS.md")
    ap.add_argument("--env-a", default="", help="env assignments for the base bot, e.g. MECH_BRAIN=heal_below=0.7")
    ap.add_argument("--env-b", default="", help="env assignments for the candidate bot")
    ap.add_argument("--sim-ref", default="HEAD", help="commit whose sim/ to use (default HEAD; 'worktree' = the live tree)")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="mechcmp.")
    global SIM_ROOT
    ENV["base"], ENV["cand"] = a.env_a, a.env_b
    try:
        if a.sim_ref != "worktree":
            SIM_ROOT, ssha = worktree(a.sim_ref, tmp)
            print(f"sim from {ssha}")
        bp, bs = worktree(a.base, tmp)
        cp, cs = worktree(a.cand, tmp)
        lines = []
        for mode in a.modes.split(","):
            rb, tb = run(bp, mode, a.seeds, a.jobs, tmp, "base")
            rc, tc = run(cp, mode, a.seeds, a.jobs, tmp, "cand")
            sb, sc = {}, {}
            for r in rb:
                sb.setdefault(r["seed"], []).append(score(r))
            for r in rc:
                sc.setdefault(r["seed"], []).append(score(r))
            sb = {k: statistics.mean(v) for k, v in sb.items()}
            sc = {k: statistics.mean(v) for k, v in sc.items()}
            common = sorted(set(sb) & set(sc))
            diffs = [sc[s] - sb[s] for s in common]
            mb = statistics.mean(sb[s] for s in common) if common else float("nan")
            mc = statistics.mean(sc[s] for s in common) if common else float("nan")
            lo, hi = boot_ci(diffs)
            miss = sum(int(r.get("missed_replies", 0) or 0) for r in rc)
            tbk = sum(int(r.get("tracebacks", 0) or 0) for r in rc)
            alive_b = statistics.mean(float(r["death_t"] or 480) for r in rb) if rb else 0
            alive_c = statistics.mean(float(r["death_t"] or 480) for r in rc) if rc else 0
            print(f"[{mode}] n={len(common)}  base {bs} {mb:.2f}  cand {cs} {mc:.2f}  diff {mc - mb:+.2f} "
                  f"(95% CI {lo:+.2f}..{hi:+.2f})  [{tb:.0f}s/{tc:.0f}s]")
            print(f"    causes base {causes(rb)}")
            print(f"    causes cand {causes(rc)}  missed_replies={miss} tracebacks={tbk}")
            kb = statistics.mean(float(r.get("kills", 0) or 0) for r in rb) if rb else 0
            kc = statistics.mean(float(r.get("kills", 0) or 0) for r in rc) if rc else 0
            print(f"    kills/match base {kb:.2f} cand {kc:.2f}   time alive base {alive_b:.0f}s cand {alive_c:.0f}s")
            lines.append(f"| {time.strftime('%m-%d %H:%M')} | {bs} | {cs} | {mode} | {len(common)} | {mb:.2f} | {mc:.2f} | "
                         f"{mc - mb:+.2f} ({lo:+.2f}..{hi:+.2f}) | {causes(rc)} miss={miss} tb={tbk} |")
        if a.log:
            with open(os.path.join(REPO, "eval", "RESULTS.md"), "a") as f:
                for l in lines:
                    f.write(l + "\n")
    finally:
        for d in os.listdir(tmp):
            if d.startswith("wt-"):
                subprocess.run(["git", "-C", REPO, "worktree", "remove", "--force", os.path.join(tmp, d)], capture_output=True)


if __name__ == "__main__":
    main()
