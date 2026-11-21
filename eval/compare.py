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
                        PY + " {root}/sim/run_matches.py --bot {bot} --mode {mode} --seeds {seeds} --out {out} --jobs {jobs}")


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


def bot_cmd(path):
    if path is None:
        return f"{PY} -u {KIT}/python/example_bot.py"
    return f"{PY} -u {path}/bot/main.py"


def run(ref_path, mode, seeds, jobs, tmp, tag):
    out = os.path.join(tmp, f"{tag}-{mode}.jsonl")
    sim_root = REPO  # always use the CURRENT sim so both bots face the same opponents
    cmd = RUNNER.format(bot=shlex.quote(bot_cmd(ref_path)), mode=mode, seeds=seeds, out=out, jobs=jobs, root=sim_root)
    t0 = time.time()
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=sim_root)
    if p.returncode != 0:
        print(p.stdout[-2000:], p.stderr[-4000:], file=sys.stderr)
        raise SystemExit(f"runner failed for {tag} {mode}")
    rows = []
    with open(out) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
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
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--log", action="store_true", help="append the result to eval/RESULTS.md")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="mechcmp.")
    try:
        bp, bs = worktree(a.base, tmp)
        cp, cs = worktree(a.cand, tmp)
        lines = []
        for mode in a.modes.split(","):
            rb, tb = run(bp, mode, a.seeds, a.jobs, tmp, "base")
            rc, tc = run(cp, mode, a.seeds, a.jobs, tmp, "cand")
            sb = {r["seed"]: score(r) for r in rb}
            sc = {r["seed"]: score(r) for r in rc}
            common = sorted(set(sb) & set(sc))
            diffs = [sc[s] - sb[s] for s in common]
            mb = statistics.mean(sb[s] for s in common) if common else float("nan")
            mc = statistics.mean(sc[s] for s in common) if common else float("nan")
            lo, hi = boot_ci(diffs)
            miss = sum(int(r.get("missed_replies", 0) or 0) for r in rc)
            tbk = sum(int(r.get("bot_stderr_tracebacks", r.get("tracebacks", 0)) or 0) for r in rc)
            print(f"[{mode}] n={len(common)}  base {bs} {mb:.2f}  cand {cs} {mc:.2f}  diff {mc - mb:+.2f} "
                  f"(95% CI {lo:+.2f}..{hi:+.2f})  [{tb:.0f}s/{tc:.0f}s]")
            print(f"    causes base {causes(rb)}")
            print(f"    causes cand {causes(rc)}  missed_replies={miss} tracebacks={tbk}")
            kb = statistics.mean(float(r.get("kills", 0) or 0) for r in rb) if rb else 0
            kc = statistics.mean(float(r.get("kills", 0) or 0) for r in rc) if rc else 0
            print(f"    kills/match base {kb:.2f} cand {kc:.2f}")
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
