#!/usr/bin/env python3
"""Policy-crash test: the policy process hard-exits at ticks 200, 400 and 600 (os._exit, like an OOM kill).
    python3 <kit>/check/check.py -- python3 -u eval/crash_bot.py   -> must PASS with 0 missed replies
"""
import os
import sys

ROOT = os.environ.get("MECH_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bot import brain, main  # noqa: E402

_orig = brain.choose_intent


def crashy(state, threats):
    if state.tick in (200, 400, 600):
        os._exit(3)
    return _orig(state, threats)


brain.choose_intent = crashy
main.main()
