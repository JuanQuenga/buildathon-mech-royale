#!/usr/bin/env python3
"""Deadline-guard test: our bot with a policy that randomly hangs (60-400 ms) or raises.
    python3 <kit>/check/check.py -- python3 -u eval/slow_bot.py    -> must still PASS with 0 missed replies
"""
import os
import random
import sys
import time

ROOT = os.environ.get("MECH_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bot import brain, main  # noqa: E402

_orig = brain.choose_intent
_rng = random.Random(1)


def slow(state, threats):
    r = _rng.random()
    if r < 0.05:
        time.sleep(_rng.choice([0.06, 0.12, 0.4]))
    elif r < 0.10:
        x = 0
        for i in range(400000):  # pure-Python busy loop holding the GIL in slices
            x += i
    elif r < 0.13:
        raise RuntimeError("injected failure")
    return _orig(state, threats)


brain.choose_intent = slow
main.main()
