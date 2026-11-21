# Public cast tools (real FFA Showdowns of the top-16 practice teams)

- `node cap.mjs live out.jsonl 7200` records `wss://watch.joinbuilders.org/live` (mechreplay/1 frames every 0.1 s,
  events, `result` records); `node cap.mjs state state.jsonl 7200` records the schedule/lineup feed. Node ≥ 22
  (built-in WebSocket). Showdowns air hourly; the lineup is the practice top 16 at the time (we are `poteto`).
- `python3 ffa.py out.jsonl [name]`: per match place, kills, damage, loadout, first weapon, killer, gun hits/fires.
- `python3 move.py out.jsonl`: per bot while firing: median speed, grounded-boost share, airborne share.
- `python3 lead.py out.jsonl`: do shooters lead? (projectile line vs target's actual and frozen positions; noisy).

Findings (11-21 05:30): top-16 bots boost 27–44 % of their firing time (2.3%, scorpion, kyoto-max, Mahalas,
tigerbyte); a few stand still. FFA places are decided by survival: winners deal 5–7k damage with 1–5 kills.
