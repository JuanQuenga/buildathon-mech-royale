# Mech Royale bot (Builders Buildathon, Nov 20–22 2026)

A bot that pilots one mech in the 16-mech `mechfight/1` battle royale. Python 3.13, one process, JSON lines on
stdin/stdout. Build with the top-level `Dockerfile`.

```
docker build -t mech-bot .
python3 check/check.py --map-dir /arena -- docker run --rm -i --network none --cpus 1 --memory 512m \
  --memory-swap 512m --pids-limit 128 --cap-drop ALL --read-only --tmpfs /tmp:rw,size=64m \
  --user 65534:65534 -v "$PWD/arena:/arena:ro" mech-bot      # check.py is from the organisers' kit
```

## Layout

| Path | What |
| --- | --- |
| `bot/main.py` | protocol loop, worker-thread deadline guard, action assembly |
| `bot/state.py` | shared world state and interface types |
| `bot/brain.py` | objectives (zone, loot, fights, healing), inventory, upgrades, squad-vs-FFA detection |
| `bot/arena.py`, `bot/navigate.py` | map geometry, line of sight, path planning, movement |
| `bot/threats.py`, `bot/combat.py` | threat tracking, projectile dodging, aiming and firing |
| `sim/` | local proxy simulator used for evaluation (not part of the image) |
| `eval/` | paired-seed comparisons, timing stress test, results log |
| `docs/INTERFACES.md` | module contract |

## Credits, libraries, prior code

- All code in this repository was written during the hackathon weekend (from Nov 20 2026). No pre-weekend code.
- **Organiser-provided starter kit** (`mechfight-kit`, Builders Buildathon): the map files in `arena/v2/`
  (`world.json`, `terrain.i16`) are copied unchanged from the kit. The protocol loop in `bot/main.py` follows the
  design of the kit's `python/mechfight.py` wrapper (reader thread, newest-observation rule) but is our own code;
  the initial placeholder behaviour mirrored the kit's `python/example_bot.py`. The kit's `check/check.py` is
  used for testing and is not shipped.
- Libraries: Python standard library, [NumPy](https://numpy.org) 2.5.5 (BSD-3-Clause). Base image
  `python:3.13-slim` (pinned by digest).

## License

MIT — see `LICENSE`.
