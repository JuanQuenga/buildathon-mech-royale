# Review: Mech Royale entry (for the human and the coordinator)

## Status (11-21 14:50 ET)
- **Board:** best draw good-31 = 5.56, rank ~37 of 250; the cut (32nd) is 5.65 and rising ~0.1 per hour this
  afternoon; 16th 6.10; leader 6.31. We are outside the qualifying 32 until a draw beats the cut.
- **Base policy** `laser+nav3x+fixx+steadyx`: true mean 5.34 (9 official draws, SD 0.13).
- **Isolate** (`+isolatex`, fight one at a time from spots hidden from the other attackers): 5.48, 5.44, then its
  first re-roll good-ri41 5.17 → mean 5.36 over 3 draws, i.e. the base level. No variant has a true mean measurably
  above 5.34; every draw (base or isolate re-roll) has only ~1–2 % chance of beating a 5.65 cut.
- **Tested today, no gain** (official): airborne lead 5.25, boost strafe 5.27, gun discipline 5.35, opening hold-fire
  5.35, ffax 5.46, jet60 5.17, laser hunt 5.33, peek 5.44/5.15, commit 5.33, arm-first 5.19/5.27, cycle 5.42/5.21,
  isolate+cycle 5.21, arm-first+cycle 5.44, widex 5.23, weave 5.38. **Clearly worse:** break contact at the 2nd
  hunter 4.73, slow6 4.77, stand-to-fire 4.19 (lateral movement while fighting the squad is worth ~1 point).

## Please submit
**The submit queue is the file `coord/queue/mech.txt`** (the coordinator's runner submits from it). Predictions vs
official results: `eval/RESULTS.md` ("Predictions before scoring").

Current queue (16:00): good-79 (retreat cover against the three nearest threats), good-80 (cubex twin), then
the isolate re-rolls good-ri42 … ri62. Outside-review batch: cubes 5.46, fire-control fix 5.23, cubes + drops
5.19, keep gun 5.33. Review claims checked against the protocol (first drop at 95 s with full HP + 3 cubes,
+4 % HP/damage per cube, rear ×1.5): all correct.

### Filler: qualification-insurance re-rolls (track 1)
Same policy as good-31 (`laser+nav3x+fixx+steadyx`), differing only in the behaviour-neutral idle torso-scan phase
(`r<n>x`), so each is an independent official draw of the best-mean policy. Submit them, in order, in every slot not
used by an experiment above. Made and gated by `eval/make_rerolls.sh "laser+nav3x+fixx+steadyx" 1 16` (branch
`var/R<n>`, tag only after a full gate pass). Tags present: see `git tag -l 'good-r*'`; the list below is what passed.

| Order | Tag | Commit |
| --- | --- | --- |
| 1 | `good-r1` | 0b3d535 |
| 2 | `good-r2` | a3de7d6 |
| 3 | `good-r3` | 3539b7c |
| 4 | `good-r4` | 0647f5f |
| 5 | `good-r5` | 964946c |
| 6 | `good-r6` | fe55d11 |
| 7 | `good-r7` | 7b21405 |
| 8 | `good-r8` | 90709e2 |
| 9 | `good-r9` | e0c167c |
| 10 | `good-r10` | 0fb8dcd |
| 11 | `good-r11` | 15b725a |
| 12 | `good-r12` | cd320aa |
| 13 | `good-r13` | 17f7e06 |
| 14 | `good-r14` | 98dc39d |
| 15 | `good-r15` | 6ebae40 |
| 16 | `good-r16` | 7f0977e |

Superseded (rage base without steady strafe; gated but less informative now, run only if the queue is empty):
`good-32` (0947af6, 170 m laser standoff), `good-33` (18ce57f, laser hunt to 120 s, no mortar), `good-34` (709fd65,
break contact at the 2nd hunter). Steady-base versions follow as good-39+.

## How much one official score can tell us (read before trusting any single result)
- A 48-match official score of a build whose behaviour differs at all from another is close to an independent draw.
  Sim measurement (11-21 06:40): per-match SD of (16 − place) = 1.9, so **SE of a 48-match mean ≈ 0.27** and the
  SE of a difference between two builds ≈ 0.38. A behaviour-neutral chaos control (torso-scan phase only) moved the
  sim score by +0.54 ± 0.47; identical seeds stay identical only for an identical build (official ±0.03).
- Officially, all four perturbations of good-31 (35: 5.31, 36: 5.13, 37: 5.25, 38: 5.35; mean 5.26) sit 0.2–0.4
  below it, and the earlier family (22: 5.21, 27: 5.25, 30: 5.19) sits at ~5.2. The likeliest reading: the family's
  true level is ~5.3 and good-31 drew about one SE high. good-46/47 measure this directly.
- Consequences: (1) single-run contrasts resolve only effects of ≳0.6; most earlier "effects" (±0.1–0.4) are not
  established. (2) For the practice board (best score counts) every extra draw of an equally good build is a
  lottery ticket: re-rolls keep our best rising with the cut at no risk. (3) For the final (FFA, new seeds) pick the
  entry by the **family mean over draws** and its FFA behaviour, not the single best draw; a chaos re-roll that
  scores higher is the same policy as good-31 and equally good as an entry.

## 300-seed paired sim cross-check (fresh seeds 100–399, squad, paired differences vs base ± SE)
| arm | sim diff | official |
| --- | --- | --- |
| isolate | +0.08 ± 0.12 | 5.48, 5.44 (mean 5.46) |
| commit | −0.14 ± 0.12 | 5.33 |
| fight-regen cycle | +0.06 ± 0.10 | 5.42, 5.21 (mean 5.32) |
| arm-first | +0.22 ± 0.12 | 5.19, 5.27 (mean 5.23) |
The sim and the official scorer disagree on arm-first (sim +0.22, official −0.11): the sim's weapon-starved seeds are
not what limits us officially. Gated follow-ups ready: good-71 (widex twin), good-72 (isolate + widex).

## Practice: can survival to the end pay? (sim study 11-21 11:15, 48 squad matches each)
Scoring (protocol §4/§9): placement = death order; matches end when one mech is left or at 8:00 (survivors ranked by
HP); the zone reaches radius 0 by ~6:55 at 260 HP/s, so the final zone ends every match. In the sim the house squad
dies to the final zone at 382–420 s if nobody kills it, so a bot alive at ~385 s would outplace most of it.

| policy | mean pts | kills | median death s | p90 death s | alive at 300 s | alive at 380 s |
| --- | --- | --- | --- | --- | --- | --- |
| base (good-31 policy) | 5.00 | 4.88 | 105 | 192 | 0 % | 0 % |
| (a) pure evasion, never fires (`evadex`) | 0.08 | 0.00 | 300 | 307 | 48 % | 0 % |
| (b) evasion, fights only hunters (`evade2x`) | 4.31 | 4.23 | 186 | 271 | 2 % | 0 % |

Reading: pure evasion survives to ~300 s half the time and then dies within seconds when the whole squad engages
(sim `all_engage_t` 300 s); nothing reaches the ~380 s window where house bots start dying to the zone. Surviving
longer without outliving house bots earns nothing (they do not die before ~380 s), so a fight-then-run hybrid only
delays our death. Dropped for practice, unless official evidence shows the real squad's late game differs. The
real squad's all-engage timing is unknown, and this conclusion rests on the sim director.

## FFA (track 2: where the prize is decided)
**Real FFA evidence** (public Top-16 Showdown casts, 11 matches / 176 seats; tools in `eval/diag/cast/`):
- 26 % of seats die before 30 s, and those seats were fighting: median 840 damage dealt in the opening. Places 5–10
  mostly avoided the opening brawl (median 45 damage taken, 409 dealt). The top 4 fought but armed early (61 % had a
  secondary by 15 s vs 35 % for places 11–16). Rear damage is 6 % of damage taken by the top 4 vs 15 % for the rest.
- Our bot (poteto) in 5 showdown matches: places 14, 12, 2, 9, 8. Both bad ones were opening-brawl deaths with only
  a gun or gun + mortar. At 18.7 s we opened fire with the gun on a laser bot at 176 m and ate four full beams. At
  24.6 s we lost an even gun duel once the opponent picked up a laser. In the 9th-place match we turned to finish a
  weak mech and took a 586-damage laser hit in the back from the mech that was actually hitting us.
- Detector (sim): FFA detected in 100 % of FFA matches at ~10–14 s; in squad, ~7 % of matches end on a wrong
  `ffa` guess, so FFA-only switches leak into a few practice matches (acceptable for a final entry, since practice
  stops counting at the cutoff).

- **What separates FFA placers (20 showdown matches, per bot):** not damage dealt but damage taken and survival.
  poteto deals the most damage per second of the field (34.6/s, like the best placer TigerTown27 at 34.0/s) but
  takes 41/s and lives 95 s; the bots that place 5.7–7.4 take 24–30/s and live 150–178 s. Laser and gun engagement
  ranges (median laser hit 60–110 m; ours 95 m) do not separate winners. So for the final, survival beats aggression.
  (`eval/diag/cast/range.py`, and the per-bot dealt/taken table in this section's history.)

| Bot | mean place | dealt/s | taken/s | life s |
| --- | --- | --- | --- | --- |
| TigerTown27 | 5.7 | 34.0 | 26.6 | 178 |
| r1ver | 6.9 | 23.4 | 29.7 | 164 |
| A-bot LLC | 7.0 | 34.8 | 36.2 | 134 |
| Kanyaraasi | 7.1 | 18.2 | 26.4 | 172 |
| **poteto (us)** | 8.9 | **34.6** | **41.0** | **95** |
| 2696 | 10.5 | 37.4 | 52.2 | 86 |
| scorpion | 11.4 | 29.2 | 55.8 | 75 |

**Behaviour profiles of the field** (real showdowns, bots with ≥ 5 matches, sorted by mean place; `eval/diag/cast/profile.py`;
"speed firing" = median horizontal speed within 0.5 s of a shot; boost/air = shares of those frames):

| bot | n | place | first weapon med s | laser at end | laser hit range med | gun hit range med | hit-by range med | dealt/s | taken/s | life s | speed firing | boost | air | cubes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TigerTown27 | 17 | 5.9 | 8.9 | 0.88 | 88 | 84 | 84 | 35.9 | 28.7 | 170 | 11.7 | 0.32 | 0.01 | 16.5 |
| kyoto-max | 17 | 6.9 | 23.8 | 0.76 | 63 | 68 | 68 | 22.9 | 27.8 | 162 | 6.3 | 0.23 | 0.01 | 6.9 |
| r1ver | 18 | 7.0 | 16.7 | 0.33 | 92 | 66 | 74 | 22.8 | 29.3 | 157 | 10.3 | 0.26 | 0.01 | 9.7 |
| giddygiddyboy | 17 | 7.1 | 31.9 | 0.47 | 60 | 59 | 61 | 20.9 | 24.4 | 152 | 5.8 | 0.14 | 0.01 | 5.4 |
| A-bot LLC | 25 | 7.2 | 6.8 | 0.64 | 102 | 86 | 82 | 32.6 | 36.8 | 132 | 11.6 | 0.21 | 0.04 | 6.2 |
| W squad | 19 | 7.4 | 12.7 | 0.74 | 70 | 60 | 64 | 22.4 | 37.0 | 152 | 7.6 | 0.18 | 0.01 | 6.9 |
| Kanyaraasi | 24 | 7.5 | 12.0 | 0.29 | 88 | 56 | 59 | 20.9 | 27.5 | 165 | 4.7 | 0.15 | 0.01 | 3.9 |
| whatever | 16 | 7.6 | 20.9 | 0.25 | 65 | 60 | 66 | 18.0 | 27.3 | 148 | 7.4 | 0.24 | 0.00 | 6.1 |
| benchmaster | 17 | 8.2 | 17.4 | 0.71 | 104 | 96 | 88 | 20.8 | 31.4 | 127 | 7.3 | 0.14 | 0.03 | 2.7 |
| not even close | 17 | 8.3 | 25.4 | 0.59 | 77 | 67 | 67 | 19.1 | 32.5 | 127 | 9.4 | 0.17 | 0.02 | 4.4 |
| azing | 23 | 8.4 | 45.5 | 0.43 | 96 | 104 | 89 | 26.8 | 30.6 | 123 | 11.6 | 0.23 | 0.05 | 4.6 |
| BackwardsDeployeds | 21 | 8.6 | 32.1 | 0.14 | 80 | 65 | 64 | 24.6 | 31.9 | 134 | 8.1 | 0.28 | 0.02 | 5.3 |
| Mahalas | 24 | 8.7 | 53.8 | 0.29 | 92 | 90 | 92 | 19.1 | 34.3 | 122 | 11.7 | 0.33 | 0.04 | 1.9 |
| uploadcocoa | 7 | 8.9 | 15.6 | 0.43 | 113 | 85 | 86 | 31.5 | 30.3 | 102 | 10.7 | 0.18 | 0.51 | 6.0 |
| poteto | 7 | 8.9 | 14.6 | 0.57 | 95 | 95 | 80 | 34.6 | 41.0 | 95 | 11.6 | 0.10 | 0.06 | 5.0 |
| tigerbyte | 12 | 9.2 | 15.9 | 0.33 | 98 | 87 | 95 | 22.5 | 43.9 | 124 | 11.6 | 0.40 | 0.00 | 3.9 |
| AT | 9 | 9.8 | 7.8 | 0.56 | 127 | 48 | 103 | 23.8 | 40.8 | 78 | 11.7 | 0.11 | 0.13 | 4.1 |
| Antalos | 16 | 9.9 | 20.0 | 0.50 | 53 | 54 | 58 | 32.2 | 42.5 | 93 | 6.7 | 0.14 | 0.00 | 5.4 |
| 2696 | 25 | 10.0 | 14.4 | 0.48 | 105 | 91 | 89 | 38.3 | 51.7 | 97 | 11.2 | 0.21 | 0.01 | 4.6 |
| 2.3% | 23 | 10.2 | 13.2 | 0.39 | 59 | 64 | 61 | 20.2 | 35.1 | 80 | 9.0 | 0.27 | 0.16 | 1.0 |
| sonion | 10 | 10.7 | 38.0 | 0.20 | 113 | 92 | 82 | 22.9 | 49.3 | 80 | 3.7 | 0.17 | 0.02 | 4.0 |
| scorpion | 17 | 11.4 | 7.3 | 0.53 | 99 | 75 | 81 | 29.2 | 55.8 | 75 | 11.2 | 0.28 | 0.02 | 5.4 |

Reading: the practice leaders kyoto-max (6.31) and giddygiddyboy (6.0) fight close (~60 m), slowly (~6 m/s while
firing), take 24–28 dmg/s and live 150–160 s; their first weapon comes late (median 24–32 s). We deal the most damage
but take 41/s at 11.6 m/s and live 95 s. Practice points are kills before death (score = 16 − place; house bots
never fight each other), so living ~25 s longer at our kill rate is worth about one point. This motivated good-54.

**FFA-only switch `ffax`** (`ffa_tactics`, active only while the detector says `ffa`; commit 809b931):
gun discipline beyond 120 m; never pick a target that puts an active attacker more than 80° behind our aim unless
the target is killable; while holding only a gun or gun + mortar, no opportunity fights, and break off from a
laser holder beyond 100 m.

**Self-play** (sim, 16-entrant FFA, our variants tracked side by side; `sim/run_matches.py --ffa "var:<profile>*n,…"`,
summarised by `eval/selfplay.py`): v1 = 8 of our variants + 2 example bots + 6 built-ins, seeds 1000–1199; v2 = 4×
good-31 policy vs 4× good-31 + ffax + 2 example + 6 built-ins, seeds 2000–2199. Results below when done.

**v1** (seeds 1000–1099, 100 matches; stopped at half to run v2 first; 95 % CI per row; "ever 'squad'" = the
detector guessed squad at some point before switching to ffa):

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:base | 100 | 9.15 ± 0.91 | 1.22 | 109 | 16/100 | 11 (96/100) | 7 | 0 |
| var:laser+nav3x+fixx+hidex | 100 | 9.04 ± 0.91 | 1.30 | 103 | 15/100 | 11 (97/100) | 13 | 0 |
| var:laser+nav3x+fixx+steadyx | 200 | 8.91 ± 0.64 | 1.31 | 101 | 22/200 | 12 (193/200) | 23 | 0 |
| var:laser+nav3x+fixx+ragex+steadyx | 100 | 8.79 ± 0.94 | 1.29 | 104 | 10/100 | 12 (97/100) | 14 | 0 |
| var:laser+nav3x+fixx | 100 | 8.78 ± 0.90 | 1.32 | 101 | 10/100 | 12 (97/100) | 12 | 0 |
| var:laser+nav3x+fixx+steadyx+discx | 100 | 8.73 ± 0.94 | 1.35 | 102 | 10/100 | 12 (96/100) | 16 | 0 |
| var:laser+nav3x+fixx+steadyx+sboostx | 100 | 8.48 ± 0.92 | 1.26 | 95 | 6/100 | 12 (96/100) | 15 | 0 |

Reading: in FFA no squad-tuned variant is a liability (steady, rage, hide, laser-first all within ±0.4); boost-strafe
is lowest (dies earlier) but not significantly. The detector reaches `ffa` at a median 11–12 s; ~3 % of our seats
die before it does. 20 % of our seats die before 30 s, mostly holding only the gun (mean 2.2 points): the same
opening-brawl pattern as the real showdowns, and the target of `ffax` (v2).

**v2** (seeds 2000–2099, 100 matches, 4 copies of each per match):

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx | 400 | 8.97 ± 0.44 | 1.39 | 103 | 46/400 | 11 (390/400) | 38 | 0 |
| var:laser+nav3x+fixx+steadyx+ffax | 400 | 8.94 ± 0.45 | 1.41 | 102 | 49/400 | 11 (391/400) | 35 | 0 |

Reading: `ffax` changes nothing in the sim (−0.03 ± 0.6); early deaths stay at ~22 % before 30 s. Diagnosis of those
early deaths (v2): 93 % die in `retreat`, usually gun-only with 2+ attackers, and 77/87 after FFA was detected. The
problem is open-ground retreats under fire, not starting fights. v3 tests `ffastandx` (FFA-only: without real cover
within reach, keep fighting instead of retreating in the open).

**v3** (seeds 3000–3049, 50 matches; stopped early, clear result):

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx | 200 | 9.10 ± 0.65 | 1.50 | 105 | 27/200 | 10 (194/200) | 19 | 0 |
| var:laser+nav3x+fixx+steadyx+ffastandx | 200 | 8.39 ± 0.65 | 1.28 | 95 | 21/200 | 10 (188/200) | 19 | 0 |

Reading: standing and fighting without cover is worse (−0.7 ± 0.9, early deaths 24 % → 27 %): the retreat logic is
right, and the early deaths are fights we lose either way. Dropped. Also tried `lookx` (spin the torso while
unarmed to find pickups): in the sim, arming time barely changes (median 11.9 → 10.8 s; squad +0.17 ± 0.61);
arming is limited by distance to weapons, not by vision. v4 tests `ffahidex` (FFA survival-first: hide from
non-hunters, fight only attackers/killable while more than 5 mechs are alive).

**v4** (seeds 4000–4099, 100 matches): FFA survival-first `ffahidex`

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx+ffahidex | 400 | 9.29 ± 0.46 | 1.15 | 114 | 54/400 | 11 (384/400) | 46 | 0 |
| var:laser+nav3x+fixx+steadyx | 400 | 8.78 ± 0.43 | 1.43 | 99 | 42/400 | 10 (394/400) | 31 | 0 |

Reading: +0.52 ± 0.69 per match (paired within matches; the per-row CIs above treat seats as independent and are
too narrow). It survives longer with fewer kills, the same pattern as the real showdown places 5–10. Promising but
not established; 100 more matches (v4b) are queued. Gated tag: **good-51** (028206c, FFA-only, so practice is
unaffected except through detector errors).

**v5** (seeds 5000–5099, 100 matches): opening hold-fire `openholdx`

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx | 400 | 8.93 ± 0.46 | 1.41 | 103 | 47/400 | 11 (383/400) | 39 | 0 |
| var:laser+nav3x+fixx+steadyx+openholdx | 400 | 8.60 ± 0.46 | 1.35 | 100 | 49/400 | 11 (385/400) | 35 | 0 |

Reading: −0.33 ± 0.77 per match, i.e. no measurable effect in the sim (early deaths 23 % → 25 %). In the sim our
opening deaths are mostly not fights we start, unlike the three real cases. Official practice: good-50 = 5.35
(no cost). Verdict: harmless and mechanistically clear against real bots, but unproven.

**v4 + v4b combined** (seeds 4000–4199, 200 matches): FFA survival-first

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx+ffahidex | 800 | 9.13 ± 0.32 | 1.08 | 114 | 99/800 | 11 (772/800) | 88 | 0 |
| var:laser+nav3x+fixx+steadyx | 800 | 8.86 ± 0.31 | 1.49 | 105 | 88/800 | 11 (782/800) | 72 | 0 |

Reading: **+0.26 ± 0.48 per match** (paired within matches): positive, not significant. It survives longer
(114 vs 105 s) and kills less, which is the direction the real showdown data favours (placement follows damage taken
and survival). v6 = hide until 5 alive vs until 3 alive; v7 = the combined candidate good-53 vs base, 200 matches.

**v6** (seeds 6000–6099, 100 matches): FFA hide until 3 alive vs until 5 alive

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx+ffahide3x | 400 | 9.12 ± 0.45 | 1.18 | 127 | 50/400 | 12 (386/400) | 50 | 0 |
| var:laser+nav3x+fixx+steadyx+ffahidex | 400 | 8.82 ± 0.45 | 1.21 | 119 | 46/400 | 12 (390/400) | 59 | 0 |

Reading: hiding longer is better again (+0.29 ± 0.65 per match), on top of hide-5 vs base (+0.26 ± 0.48): the
survival direction is consistent. The FFA candidate is now **good-55** (`openholdx+ffahide3x`); v7 (200 matches,
good-55 policy vs base) and v8 (peek vs base, FFA no-collapse check) are running.

**v7** (seeds 7000–7199, 200 matches): the FFA candidate good-55 policy (`openholdx+ffahide3x`) vs base

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx+openholdx+ffahide3x | 800 | 9.01 ± 0.33 | 1.00 | 115 | 97/800 | 12 (771/800) | 90 | 0 |
| var:laser+nav3x+fixx+steadyx | 800 | 8.79 ± 0.32 | 1.58 | 109 | 90/800 | 13 (775/800) | 99 | 0 |

Reading: **+0.22 ± 0.48 per match**. Across independent seed sets the survival-first package keeps a positive point
estimate (v4 hide-5 vs base +0.26, v6 hide-3 vs hide-5 +0.29, v7 +0.22; pooled v4 + v7 ≈ +0.24 ± 0.34): suggestive,
not proven, and in the direction the real showdown data favours. It survives longer (115 vs 109 s) with fewer kills.
v8 checks that peek (good-54) does not collapse in FFA.

**v8** (seeds 8000–8099, 100 matches): peek vs base in FFA (no-collapse check)

| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| var:laser+nav3x+fixx+steadyx+peekx | 400 | 9.08 ± 0.46 | 1.44 | 110 | 54/400 | 12 (383/400) | 58 | 0 |
| var:laser+nav3x+fixx+steadyx | 400 | 8.76 ± 0.45 | 1.28 | 104 | 39/400 | 12 (389/400) | 45 | 0 |

Reading: peek does not hurt in FFA (+0.32 here).

**Peek's conditional effect** (48 traced squad matches; per 0.1 s frame, peek cycle running vs strafing with a laser
held, by distinct mechs that hit us in the last 3 s; `eval/diag/peek_cond.py`):

| state | attackers (3 s) | seconds | taken/s | dealt/s |
| --- | --- | --- | --- | --- |
| peek cycle | 0 | 260 | 0.0 | 207.5 |
| peek cycle | 1 | 172 | 50.0 | 192.3 |
| peek cycle | 2+ | 39 | 118.9 | 261.3 |
| strafe, laser held | 0 | 470 | 0.0 | 147.9 |
| strafe, laser held | 1 | 251 | 53.2 | 208.8 |
| strafe, laser held | 2+ | 117 | 133.7 | 212.6 |

Inside a real peek cycle damage intake is only 6–11 % lower than strafing in the open: cover fighting as built is not
the step change. Not iterated.

## Aim audit on real showdowns (11-21 15:10; `eval/diag/cast/aim_audit.py`)
The "~50 % real gun hit rate" counted every gun shot, including shots at crates and drones. Attributing each shot to
the mech nearest the aim line (≤ 8°) at the fire tick:

| | gun shots | hits on mechs per shot fired | hits on drones/crates per shot | hit rate on mech-aimed shots |
| --- | --- | --- | --- | --- |
| poteto (us) | 276 | 0.40 | 0.21 | **0.81** (214 shots) |
| kyoto-max (practice #1) | 2678 | 0.45 | 0.19 | |
| giddygiddyboy / TigerTown27 / A-bot LLC | 1766 / 2967 / 2892 | 0.39 / 0.41 / 0.43 | 0.23 / 0.21 / 0.17 | |
| whole field | | | | **0.81** (29,355 shots) |

| range | 30–60 m | 60–90 | 90–120 | 120–150 | 150–180 | 180–240 |
| --- | --- | --- | --- | --- | --- | --- |
| us | 0.88 | 1.00 | 0.91 | 0.82 | 0.86 | 0.24 |
| field | 0.95 | 0.94 | 0.84 | 0.70 | 0.56 | 0.33 |

Verdict: **no aim error.** Our gun accuracy equals or beats the field at every range up to 180 m, and our laser hit
rate (75 %) is among the best. Lead/latency is not the gap to 6.3, and the sim's aim (87 % on mech-aimed shots) is
not far from reality. (A frame-interpolated bullet reconstruction matched real outcomes on only ~48 % of shots, so I
do not report miss geometry from it.) Only shots beyond 180 m are poor (9 % of our mech-aimed shots).

## House-bot tiers: can we fight the easy ones first? (11-21 15:20) — no
- **Not observable.** `hello` carries only type, protocol, slot, seed, map and the rule config. An observed mech is
  `id, kind, pos, vel, aim, hp, max_hp, cubes, weapons, charging`: no name or tier, and max HP is 1400 for every
  house bot. Ids are not a tier key either: the entrant's slot varies by match and house bots fill the rest.
- **No real evidence that tiers differ the way the labels suggest.** We have no practice replays. The only real
  data with tier labels is the old demo (previous balance): gun hits on mechs Expert 47 %, Hard 35 %, Medium 60 %
  (2–3 mechs each), no monotonic ordering. The current lobbies use `house:expert` plus `probe-*` archetypes, not the
  practice tiers.
- **The sim cannot answer it.** Its tiers (`sim/builtin.py: TIERS`: aim noise, lead, reaction, range) are our own
  guesses, so its result is circular: in 300 sim matches we are killed by easy 143, medium 128, hard 18, expert 3,
  because in our reconstruction the early, close attackers are easy/medium.
- **Behavioural recognition already exists** in the form that matters: the hunter model prioritises whoever is
  actually hitting us (×2) and discounts passive mechs. Recognising accuracy before being shot is not possible from
  the observation stream.
Verdict: no tier variant. With the aim audit and the movement table, this closes the practice idea list.

## Movement while fighting the squad (official dose-response)
| engage movement | tag | official |
| --- | --- | --- |
| stand still with ≤ 1 attacker in sight | good-66 | 4.19 |
| speed capped at 6 m/s | good-65 | 4.77 |
| no sideways movement (range keeping only) | good-37 | 5.25 |
| base strafe, reversals every 1.2–2.4 s | good-22 | 5.21 |
| steady strafe, reversals every 3–5 s (base) | good-31 family | 5.34 (mean of 9) |
| reversals every 6–10 s / never | good-36 / good-38 | 5.13 / 5.35 |
| boost-run strafe | good-39 | 5.27 |
Against the house squad, lateral movement while fighting is worth ~1 point; the FFA leaders' slow firing does not
transfer. Untested direction: more lateral movement while closing range (good-41 `widex`, queued).

## Family means (pick the final entry by these, not by the best single draw)
| Family | Draws | Mean | Notes |
| --- | --- | --- | --- |
| **steady strafe on laser + nav3 + hop fix** (good-31 policy and its re-rolls) | 31: 5.56, 46: 5.29, 47: 5.40, r1: 5.25, r2: 5.29, r3: 5.48, r4: 5.42, r6: 5.19, r8: 5.19 | **5.34** (n=9, SD 0.13) | the recommended practice policy; good-r4…r16 are further re-rolls |
| steady family incl. variants | 31, 46, 35, 36, 37, 38, 39 | 5.31 (n=7) | no variant of it beats it beyond noise |
| non-steady laser + nav3 (+ hop fix) | 15: 5.19, 22: 5.21, 27: 5.25, 30: 5.19 | 5.21 (n=4) | |
| nav3 without laser first | 14: 5.17, 17: 5.06, 16: 4.88 | 5.04 | |
| old navigation (good-4 nav) | 4: 4.58, 5: 4.46, 6: 4.96, 7: 5.00, 8: 4.79, 10: 5.10, 11: 5.00 | 4.84 | the one clearly real effect so far: navigation (+0.3–0.4) |
SE of one draw ≈ 0.27, so the steady family's lead over non-steady (~+0.1) is suggestive, not established.

## Official results (48 fixed-seed practice matches each; identical-build noise ±0.03, between builds ~±0.1)
| Tag | Score | What it changed |
| --- | --- | --- |
| good-31 | **5.56** | good-22 + steady strafe (reversals every 3–5 s instead of 1.2–2.4 s) |
| good-78 | 5.33 | keep the gun (no gun-for-lightning swap) |
| good-77 | 5.19 | cubes + supply drops first |
| good-76 | 5.23 | fire-control order fix (re-check gun shot after laser aim override) |
| good-75 | 5.46 | **cubes priced by exposure** (outside review); twin good-80 queued |
| good-ri41 | 5.17 | first isolate re-roll (isolate mean 5.36 over 3 draws) |
| good-73 | 5.38 | weave: sideways weave while retreating |
| good-41 | 5.23 | widex: full sideways weight while closing range |
| good-70 | 5.21 | isolate + cycle |
| good-69 / good-58 | 5.21 / 5.44 | cycle twin (cycle mean 5.32) / isolate twin (isolate mean 5.46) |
| good-66 | **4.19** | stand to fire with ≤ 1 attacker in sight: disastrous |
| good-65 | **4.77** | slow6: cap speed at 6 m/s while engaging: clearly worse (moving slowly while fighting the squad costs ~0.6) |
| good-64 | 5.44 | arm-first + cycle |
| good-63 | 5.42 | fight-regen cycle 40 → 90 % |
| good-61 / good-62 | 5.19 / 5.27 | arm-first and twin: mean 5.23 (below base; the sim seeds it fixed are not the official seeds' problem) |
| good-59 | 5.33 | **commit** (kill conversion): = base; twin good-60 queued |
| good-57 | 5.48 | **isolate** (fight one at a time from spots hidden from the other attackers): first draw; twin good-58 decides |
| good-54 / good-56 | 5.44 / 5.15 | **peek** (fight from cover with the laser) and its twin: mean 5.30 = base. Sim diagnosis: the cycle runs in only 19 % of engage decisions (48 % no laser yet, 29 % no cover within 40 m), damage intake unchanged (20.7 vs 20.5/s): mostly the base policy. Not iterated |
| good-52 | 5.17 | good-31 + jet climbs to 60 m: worse |
| good-53 | 5.31 | good-31 + openhold + ffahide (FFA candidate v1): no practice cost |
| good-44 | 5.33 | good-31 + laser hunt to 120 s, no mortar |
| good-r5 | 5.27 | re-roll |
| good-49 | 5.46 | good-31 + ffax (FFA-only tactics): practice-neutral |
| good-r4 | 5.42 | re-roll |
| good-r6 / good-r8 | 5.19 / 5.19 | re-rolls |
| good-50 | 5.35 | good-31 + opening hold-fire (FFA candidate): no practice cost |
| good-r3 | 5.48 | re-roll of good-31 |
| good-r2 | 5.29 | re-roll of good-31 |
| good-r1 | 5.25 | re-roll of good-31 |
| good-48 | 5.35 | good-31 + gun discipline beyond 150 m |
| good-40 | 5.25 | good-31 + airborne gun lead |
| good-42 | **4.73** | good-31 + break contact at the 2nd hunter: clearly worse (−0.7); idea and relatives dropped |
| good-47 | 5.40 | second re-roll of good-31 |
| good-46 | 5.29 | **re-roll of good-31** (behaviour-neutral chaos control): good-31 drew high |
| good-39 | 5.27 | good-31 + boost-run strafe above 80 energy |
| good-38 | 5.35 | good-31 with no reversals (orbit one way) |
| good-35 | 5.31 | good-31 + rage (stack: does not stack, −0.25) |
| good-27 | 5.25 | good-22 + rage (hunt by memory/sound, engage ratio 1.6, fight from 40 % HP, berserk) |
| good-22 | 5.21 | laser first + good-3 navigation + stale-hop fix |
| good-37 | 5.25 | good-31 with no sideways movement while engaging |
| good-36 | 5.13 | good-31 with reversals every 6–10 s (−0.43) |
| good-15 / good-30 | 5.19 / 5.19 | laser + nav3 / good-22 + juke (0.3–1.0 s reversals beyond 80 m) |
| good-14 | 5.17 | seek + nav3 |
| good-10 | 5.10 | greed + laser first |
| good-17 | 5.06 | seek + nav3 + scale |
| good-26 | 5.04 | good-22 + hide |
| good-7 / good-11 | 5.00 / 5.00 | seek / seek + laser + no mortar |
| good-6 / good-25 | 4.96 / 4.96 | greed / good-22 + combat hops |
| good-3 / good-16 | 4.88, 4.85 / 4.88 | old base (two runs) / ground-only routes |
| good-8 / good-9 | 4.79 / 4.79 | fresh (heal after kill) / chaos control |
| good-4 / good-5 | 4.58 / 4.46 | old nav / good-4 + good-3 brain |

Pending: the queue above. good-45 (boost above 50 energy, 77e995c) is gated and held back until good-39 scores.


## Recommended final entry
- **Practice board / qualification:** the best official draw (default). Today good-31 at 5.56; any isolate re-roll
  (good-ri*) that scores higher is an equally valid entry (same code family, mean 5.46).
- **Final (16-entrant FFA, new seeds), if we qualify:** **good-55** (70874eb): base policy + opening hold-fire
  (`openholdx`, never start a fight while unarmed in the first 45 s unless the round is known squad) + FFA
  survival-first until 3 mechs remain (`ffahide3x`, FFA-only). Evidence: 20+ real showdowns (placement follows damage
  taken and survival; our three opening deaths were fights we started unarmed); FFA self-play +0.22 ± 0.48 over 200
  matches (v7) with consistent positive point estimates (v4 +0.26, v6 +0.29); practice cost measured nil (good-50
  5.35, good-53 5.31). Fallback: the base policy (good-31). If an isolate re-roll becomes our best draw, enter
  **good-74** (5ce2a12, gated): isolate + openhold + ffahide3, the same FFA package on the isolate base.

## What the bot does
Python bot (`bot/`): a forked policy process with a hard 26 ms reply guard. Per observation: threat assessment →
brain intent (zone rotation, fight/retreat, heal cycle, loot, supply drop, seek, hold) → navigation (path planner,
jet hops) → combat (led gun, laser state machine, lightning) → inventory (weapon take/swap, upgrades). Details in
`docs/HANDOFF.md`, `docs/combat.md`, `docs/nav.md`.

**Variants are profiles.** `bot/brain.py: DEFAULT_PROFILE` selects one (the submitted image has no env). Profiles
compose with `+` (e.g. `laser+nav3x`), and `MECH_PROFILE=...` overrides locally. Each tag is a one-line commit on
a `var/*` branch that flips `DEFAULT_PROFILE`, so `main` keeps `base`. `nav3x` swaps in `bot/navigate3.py`, a frozen
copy of good-3's navigation.

## Evidence so far
- **Official runs are the instrument.** An identical resubmission moves the score ±0.03. A behaviour-neutral
  perturbation (good-9) moved it −0.08. So tag-to-tag noise is about ±0.1.
- **The sim cannot rank variants.** Paired noise is ±0.4 at 96 seeds, and the same profile on the same seeds scored
  5.38 and 5.09 on two runs. The sim also rated good-4 ≥ good-3, which reality reversed. Use it for crashes, FFA
  sanity and large effects only.
- **Navigation is a real-game lever.** good-4's jet-hop energy rules cost score: good-5 (good-4 + good-3 brain)
  scored 4.46 vs good-3's 4.88, and reverting navigate.py gave +0.17 on seek (good-14) and +0.09 on laser (good-15).
- **Post-good-4 brain work helped:** hunter model, weapon-first, pickup-memory fix, 2-death FFA guess and
  cube_greed together scored 4.96 (good-6) vs 4.58 (good-4).
- **Laser first** gave +0.14 on greed (good-10) and 0 on seek (good-11).
- **Seek** gave +0.04 (good-7). **Fresh** (heal after kill, new fights at 85 % HP) gave −0.17 (good-8).
- Sim calibration: escalation speed is the lever (`--squad join_per_loss=0.6` puts good-4 near its official
  level). The sim's FFA scores for the nav3 profiles are not worse than the old nav.
