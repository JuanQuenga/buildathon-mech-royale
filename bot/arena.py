"""Map geometry, sight/shot tests and path planning. OWNER: nav.

Design (details and timings in docs/nav.md):

* Solids come straight from world.json: every prism ring/hole edge goes into a 16 m uniform grid. A segment
  test gathers the edges of the cells the segment crosses (DDA), then runs one vectorised 2D segment/edge
  intersection; a crossing at a height inside [base, top] is a wall hit. Two rare cases are handled exactly
  in Python: a segment that passes through a thin slab (bridge deck) without touching a side face inside its
  height range, and an endpoint inside a solid. Terrain is sampled every 1 m (bilinear) only where the
  segment dips below the per-cell terrain maximum.
* Trees affect vision only (`los`, `can_see`): crowns are ellipsoids with optical density
  `rules.canopyDensity` per metre; sight is blocked when exp(-density * chord) < `rules.canopyBlockT`.
  Trunks (cylinders up to the crown base) block sight. Shots ignore trees.
* Navigation uses bot/navbake.npz (tools/nav/bake.py): a 1 m surface/clearance/walkable grid and a 4 m
  lattice graph per mech size class. `plan` is a budgeted, resumable reverse weighted A* (searches are kept per
  goal, so repeated calls with a moving start finish the search across ticks), then string-pulled with
  vectorised walk-line checks. Without the bake every nav query degrades to straight lines.

Every public method is exception-safe from the caller's point of view only by convention: callers wrap
calls (main.py does); methods here avoid raising on bad input where cheap.
"""
from __future__ import annotations

import hashlib
import heapq
import json
import math
import os
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

Vec3 = Sequence[float]

HERE = os.path.dirname(os.path.abspath(__file__))
CELL = 16.0                      # solid/tree grid cell (m)
STEP_UP = 1.2
SQ2 = math.sqrt(2.0)
DIRS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
REV = (4, 5, 6, 7, 0, 1, 2, 3)   # index of the opposite direction


def _log(*a):
    try:
        print("[arena]", *a, file=sys.stderr, flush=True)
    except Exception:
        pass


def size_scale(cubes: float) -> float:
    return 1.0 + 0.05 * max(0.0, float(cubes or 0))


class _Search:
    """Resumable reverse weighted A* from a goal node toward a (moving) start node on one size class."""
    __slots__ = ("goal", "k", "target", "open", "g", "parent", "closed", "done_fail", "expanded", "t_last")

    def __init__(self, goal: int, k: int, target: int):
        self.goal, self.k, self.target = goal, k, target
        self.open: list = []
        self.g: Dict[int, float] = {goal: 0.0}
        self.parent: Dict[int, int] = {goal: -1}
        self.closed: set = set()
        self.done_fail = False
        self.expanded = 0
        self.t_last = 0.0


class Arena:
    W_ASTAR = 1.4                 # heuristic weight (bounded-suboptimal, much faster)
    MAX_SEARCHES = 10

    # ------------------------------------------------------------------ loading
    def __init__(self):
        self.ok_nav = False
        self.last_raw_path: List[Tuple[float, float]] = []
        self.last_goal_snapped = True
        self.stats = {"plan_calls": 0, "plan_ms_max": 0.0, "seg_calls": 0}
        self._searches: Dict[Tuple[int, int], _Search] = {}
        self._los_cache: Dict[tuple, bool] = {}
        self._cache_tick = None

    @classmethod
    def load(cls, map_dir: str, bake_path: Optional[str] = None) -> "Arena":
        t0 = time.perf_counter()
        a = cls()
        wpath = None
        for cand in (os.path.join(map_dir, "v2", "world.json"), os.path.join(map_dir, "world.json")):
            if os.path.exists(cand):
                wpath = cand
                break
        if wpath is None:
            raise FileNotFoundError(f"world.json not under {map_dir}")
        with open(wpath, "rb") as f:
            raw = f.read()
        a.world_sha1 = hashlib.sha1(raw).hexdigest()
        w = json.loads(raw)
        a._load_terrain(w, os.path.join(os.path.dirname(wpath), w["terrain"].get("file", "terrain.i16")))
        a._load_solids(w)
        a._load_trees(w)
        t1 = time.perf_counter()
        try:
            cands = [bake_path] if bake_path else [os.path.join(HERE, "navbake.npz"), "/app/cache/navbake.npz"]
            for c in cands:
                if c and os.path.exists(c):
                    a._load_bake(c)
                    break
        except Exception as e:  # pragma: no cover - degraded mode
            _log("nav bake failed, straight-line nav only:", repr(e))
            a.ok_nav = False
        a.load_s = time.perf_counter() - t0
        _log(f"loaded in {a.load_s * 1000:.0f} ms (geometry {1000 * (t1 - t0):.0f} ms, nav={'yes' if a.ok_nav else 'NO'})")
        return a

    def _load_terrain(self, w, path):
        t = w["terrain"]
        self.nx, self.ny = int(t["nx"]), int(t["ny"])
        self.x0, self.y0 = float(t["minX"]), float(t["minY"])
        self.step = float(t.get("step", 1.0))
        sc = float(t.get("scale", 0.01))
        self.H = (np.fromfile(path, "<i2").reshape(self.ny, self.nx).astype(np.float32) * sc)
        self._Hl = self.H.ravel().tolist()        # python floats: fast scalar bilinear
        b = w["bounds"]
        self.bounds = (float(b["minX"]), float(b["maxX"]), float(b["minY"]), float(b["maxY"]))
        rules = w.get("rules") or {}
        self.canopy_density = float(rules.get("canopyDensity", 0.35))
        self.canopy_block_t = float(rules.get("canopyBlockT", 0.25))
        # grid for solids/trees/terrain maxima
        self.gx0, self.gy0 = self.x0, self.y0
        self.GX = int(math.ceil(self.nx * self.step / CELL)) + 1
        self.GY = int(math.ceil(self.ny * self.step / CELL)) + 1
        tmax = np.full((self.GY, self.GX), -1e9, np.float32)
        c = int(CELL / self.step)
        for gj in range(self.GY):
            j0, j1 = gj * c, min(self.ny, gj * c + c + 1)
            if j0 >= self.ny:
                continue
            row = self.H[j0:j1]
            for gi in range(self.GX):
                i0, i1 = gi * c, min(self.nx, gi * c + c + 1)
                if i0 < self.nx:
                    tmax[gj, gi] = row[:, i0:i1].max()
        self.cell_tmax = tmax.ravel().tolist()

    def _load_solids(self, w):
        prisms = w.get("prisms") or []
        self.prisms = prisms
        self.p_base = [float(p["base"]) for p in prisms]
        self.p_top = [float(p["top"]) for p in prisms]
        self.p_kind = [p.get("kind", "building") for p in prisms]
        self.p_rings = []      # list of lists of (xs, ys) python lists (ring first, then holes)
        self.p_bbox = []
        ax, ay, bx, by, pid = [], [], [], [], []
        for k, p in enumerate(prisms):
            rings = [p["ring"]] + list(p.get("holes") or [])
            rl = []
            for r in rings:
                xs, ys = [float(v) for v in r[0::2]], [float(v) for v in r[1::2]]
                rl.append((xs, ys))
                n = len(xs)
                for i in range(n):
                    j = (i + 1) % n
                    ax.append(xs[i]); ay.append(ys[i]); bx.append(xs[j]); by.append(ys[j]); pid.append(k)
            self.p_rings.append(rl)
            xs0, ys0 = rl[0]
            self.p_bbox.append((min(xs0), min(ys0), max(xs0), max(ys0)))
        self.EAX, self.EAY = np.array(ax), np.array(ay)
        self.EBX, self.EBY = np.array(bx), np.array(by)
        self.EP = np.array(pid, np.int32)
        self.EBASE = np.array(self.p_base)[self.EP] if len(pid) else np.zeros(0)
        self.ETOP = np.array(self.p_top)[self.EP] if len(pid) else np.zeros(0)
        # edge -> cells (supercover by dense sampling)
        cell_edges: Dict[int, list] = {}
        cell_prisms: Dict[int, set] = {}
        for e in range(len(ax)):
            L = math.hypot(bx[e] - ax[e], by[e] - ay[e])
            n = int(L / (CELL * 0.25)) + 2
            seen = set()
            for s in range(n):
                f = s / (n - 1)
                c = self._cell_of(ax[e] + (bx[e] - ax[e]) * f, ay[e] + (by[e] - ay[e]) * f)
                if c >= 0 and c not in seen:
                    seen.add(c)
                    cell_edges.setdefault(c, []).append(e)
        # prisms whose footprint bbox overlaps a cell (for endpoint-inside tests)
        for k, (x0, y0, x1, y1) in enumerate(self.p_bbox):
            i0, j0 = self._cell_ij(x0, y0)
            i1, j1 = self._cell_ij(x1, y1)
            for gj in range(max(0, j0), min(self.GY, j1 + 1)):
                for gi in range(max(0, i0), min(self.GX, i1 + 1)):
                    cell_prisms.setdefault(gj * self.GX + gi, set()).add(k)
        self.cell_edges = [None] * (self.GX * self.GY)
        self.cell_maxtop = [-1e9] * (self.GX * self.GY)
        self.cell_minbase = [1e9] * (self.GX * self.GY)
        for c, es in cell_edges.items():
            arr = np.array(sorted(es), np.int32)
            self.cell_edges[c] = arr
            self.cell_maxtop[c] = float(self.ETOP[arr].max())
            self.cell_minbase[c] = float(self.EBASE[arr].min())
        self.cell_prisms = [tuple(sorted(cell_prisms.get(c, ()))) for c in range(self.GX * self.GY)]

    def _load_trees(self, w):
        tr = w.get("trees") or {}
        fields = tr.get("fields") or []
        data = tr.get("data") or []
        nf = len(fields)
        self.n_trees = 0
        self.cell_trees = [None] * (self.GX * self.GY)
        if not nf or not data:
            return
        T = np.asarray(data, float).reshape(-1, nf)
        col = {f: i for i, f in enumerate(fields)}
        g = lambda name, d=0.0: T[:, col[name]] if name in col else np.full(len(T), d)  # noqa: E731
        self.TX, self.TY, self.TZ = g("x"), g("y"), g("z")
        self.TH, self.CR, self.CB, self.TR = g("height"), g("crownR"), g("crownBase"), g("trunkR", 0.3)
        self.CX = g("crownX") if "crownX" in col else self.TX
        self.CY = g("crownY") if "crownY" in col else self.TY
        self.CZ = self.TZ + 0.5 * (self.CB + self.TH)
        self.CHZ = np.maximum(0.5, 0.5 * (self.TH - self.CB))
        self.n_trees = len(T)
        cells: Dict[int, list] = {}
        for t in range(self.n_trees):
            r = max(self.CR[t], 0.5) + 0.5
            for x, y in ((self.CX[t], self.CY[t]), (self.TX[t], self.TY[t])):
                for dx in (-r, r):
                    for dy in (-r, r):
                        c = self._cell_of(x + dx, y + dy)
                        if c >= 0:
                            cells.setdefault(c, set()).add(t)
        for c, s in cells.items():
            self.cell_trees[c] = np.array(sorted(s), np.int32)

    def _load_bake(self, path):
        z = np.load(path)
        meta = json.loads(bytes(z["meta"]).decode())
        if meta.get("world_sha1") != self.world_sha1:
            _log("WARNING: nav bake was built for a different world.json; using it anyway")
        if (meta["nx"], meta["ny"]) != (self.nx, self.ny):
            raise ValueError("bake grid mismatch")
        self.meta = meta
        self.G = z["g"].astype(np.float32) / 100.0
        self._Gl = self.G.ravel().tolist()
        self.KIND = z["kind"]
        self._Kb = self.KIND.tobytes()
        self.CEIL = z["ceil"]
        self.DW = z["dwall"]
        self._DWb = self.DW.tobytes()
        self.WALK = z["walk"]
        self._Wb = self.WALK.tobytes()
        self.COMP = z["comp"]
        self.block = int(meta["block"])
        self.scales = list(meta["scales"])
        self.r_plan = list(meta["r_plan"])
        node, em = z["node"], z["emask"]
        self.K = node.shape[0]
        self.BY, self.BX = node.shape[1], node.shape[2]
        self.node_off = [node[k].tobytes() for k in range(self.K)]
        self.emask = [em[k].tobytes() for k in range(self.K)]
        # node world positions + clearance penalty, per class
        B = self.block
        self.NXY = []
        self.NPEN = []
        dwl = self.DW
        for k in range(self.K):
            off = node[k].astype(np.int32)
            has = off != 255
            bj, bi = np.nonzero(has)
            ox, oy = off[has] & 15, off[has] >> 4
            fi, fj = bi * B + ox, bj * B + oy
            xs = np.full(self.BX * self.BY, np.nan)
            ys = np.full(self.BX * self.BY, np.nan)
            ids = bj * self.BX + bi
            xs[ids] = self.x0 + fi * self.step
            ys[ids] = self.y0 + fj * self.step
            pen = np.zeros(self.BX * self.BY)
            d = dwl[np.minimum(fj, self.ny - 1), np.minimum(fi, self.nx - 1)] / 10.0
            # prefer open ground: up to +3 m per edge near walls
            pen[ids] = np.clip((self.r_plan[k] + 2.5 - d) * 1.2, 0, 3.0)
            self.NXY.append((xs.tolist(), ys.tolist()))
            self.NPEN.append(pen.tolist())
        self.DOFF = [di + dj * self.BX for di, dj in DIRS]
        self.DLEN = [B * (SQ2 if di and dj else 1.0) for di, dj in DIRS]
        self.ok_nav = True

    # ------------------------------------------------------------------ small helpers
    def _cell_ij(self, x, y):
        return int((x - self.gx0) // CELL), int((y - self.gy0) // CELL)

    def _cell_of(self, x, y) -> int:
        gi, gj = int((x - self.gx0) // CELL), int((y - self.gy0) // CELL)
        if 0 <= gi < self.GX and 0 <= gj < self.GY:
            return gj * self.GX + gi
        return -1

    def _vidx(self, x, y) -> int:
        """Index of the nearest terrain vertex (clamped)."""
        i = int(round((x - self.x0) / self.step))
        j = int(round((y - self.y0) / self.step))
        i = 0 if i < 0 else (self.nx - 1 if i >= self.nx else i)
        j = 0 if j < 0 else (self.ny - 1 if j >= self.ny else j)
        return j * self.nx + i

    def in_bounds(self, x, y, margin=0.0) -> bool:
        b = self.bounds
        return b[0] + margin <= x <= b[1] - margin and b[2] + margin <= y <= b[3] - margin

    def new_tick(self, tick=None):
        """Optional: clear per-tick caches (called by navigate.step)."""
        if tick != self._cache_tick:
            self._cache_tick = tick
            if len(self._los_cache) > 4000 or tick is None:
                self._los_cache.clear()

    # ------------------------------------------------------------------ heights
    def height(self, x: float, y: float) -> float:
        """Terrain height (bilinear), ignoring prisms."""
        fx = (x - self.x0) / self.step
        fy = (y - self.y0) / self.step
        if fx < 0:
            fx = 0.0
        elif fx > self.nx - 1.001:
            fx = self.nx - 1.001
        if fy < 0:
            fy = 0.0
        elif fy > self.ny - 1.001:
            fy = self.ny - 1.001
        i, j = int(fx), int(fy)
        u, v = fx - i, fy - j
        H = self._Hl
        k = j * self.nx + i
        h00, h10 = H[k], H[k + 1]
        h01, h11 = H[k + self.nx], H[k + self.nx + 1]
        return (h00 * (1 - u) + h10 * u) * (1 - v) + (h01 * (1 - u) + h11 * u) * v

    def ground_z(self, x: float, y: float, z_hint: Optional[float] = None) -> float:
        """Top walkable surface at (x, y) at or below z_hint (+ step tolerance): roof, deck or terrain."""
        h = self.height(x, y)
        best = h
        for k in self._prisms_at(x, y):
            top = self.p_top[k]
            if top > best and (z_hint is None or top <= z_hint + 1.5) and self._inside_prism(k, x, y):
                if z_hint is None and self.p_base[k] > h + 9.0:
                    continue   # elevated deck: without a hint assume we are under it
                best = top
        return best

    def _prisms_at(self, x, y):
        c = self._cell_of(x, y)
        if c < 0:
            return ()
        out = []
        for k in self.cell_prisms[c]:
            b = self.p_bbox[k]
            if b[0] <= x <= b[2] and b[1] <= y <= b[3]:
                out.append(k)
        return out

    def _inside_prism(self, k, x, y) -> bool:
        inside = False
        for xs, ys in self.p_rings[k]:
            n = len(xs)
            j = n - 1
            for i in range(n):
                yi, yj = ys[i], ys[j]
                if (yi > y) != (yj > y):
                    xc = xs[i] + (y - yi) * (xs[j] - xs[i]) / (yj - yi)
                    if x < xc:
                        inside = not inside
                j = i
        return inside

    def inside_solid(self, p: Vec3) -> bool:
        x, y, z = float(p[0]), float(p[1]), float(p[2])
        if z < self.height(x, y) - 0.05:
            return True
        for k in self._prisms_at(x, y):
            if self.p_base[k] < z < self.p_top[k] and self._inside_prism(k, x, y):
                return True
        return False

    # ------------------------------------------------------------------ segment tests
    def _cells_on_seg(self, ax, ay, bx, by) -> List[int]:
        """Grid cells touched by the 2D segment (Amanatides-Woo DDA)."""
        gx0, gy0 = self.gx0, self.gy0
        fx, fy = (ax - gx0) / CELL, (ay - gy0) / CELL
        tx, ty = (bx - gx0) / CELL, (by - gy0) / CELL
        i, j = int(math.floor(fx)), int(math.floor(fy))
        ie, je = int(math.floor(tx)), int(math.floor(ty))
        dx, dy = tx - fx, ty - fy
        si = 1 if dx > 0 else -1
        sj = 1 if dy > 0 else -1
        tdx = abs(1.0 / dx) if dx != 0 else 1e30
        tdy = abs(1.0 / dy) if dy != 0 else 1e30
        tmx = ((i + 1 - fx) if dx > 0 else (fx - i)) * tdx if dx != 0 else 1e30
        tmy = ((j + 1 - fy) if dy > 0 else (fy - j)) * tdy if dy != 0 else 1e30
        GX, GY = self.GX, self.GY
        out = []
        n = abs(ie - i) + abs(je - j) + 1
        for _ in range(n):
            if 0 <= i < GX and 0 <= j < GY:
                out.append(j * GX + i)
            if tmx < tmy:
                tmx += tdx
                i += si
            else:
                tmy += tdy
                j += sj
        return out

    def _seg_blocked(self, a: Vec3, b: Vec3, trees: bool = False, cells=None) -> bool:
        ax, ay, az = float(a[0]), float(a[1]), float(a[2])
        bx, by, bz = float(b[0]), float(b[1]), float(b[2])
        self.stats["seg_calls"] += 1
        if cells is None:
            cells = self._cells_on_seg(ax, ay, bx, by)
        zlo, zhi = (az, bz) if az < bz else (bz, az)
        # ---- prisms
        ce, mt, mb = self.cell_edges, self.cell_maxtop, self.cell_minbase
        parts = [ce[c] for c in cells if ce[c] is not None and mt[c] >= zlo and mb[c] <= zhi]
        if parts:
            ids = parts[0] if len(parts) == 1 else np.concatenate(parts)
            if self._edges_hit(ax, ay, az, bx, by, bz, ids):
                return True
        # endpoint inside a solid (rare: only near/over roofs)
        for (px, py, pz) in ((ax, ay, az), (bx, by, bz)):
            for k in self._prisms_at(px, py):
                if self.p_base[k] + 0.05 < pz < self.p_top[k] - 0.05 and self._inside_prism(k, px, py):
                    return True
        # ---- terrain
        tm = self.cell_tmax
        if any(tm[c] > zlo - 0.5 for c in cells):
            if self._terrain_hit(ax, ay, az, bx, by, bz):
                return True
        # ---- trees (vision only)
        if trees and self.n_trees:
            if self._trees_block(ax, ay, az, bx, by, bz, cells):
                return True
        return False

    def _edges_hit(self, ax, ay, az, bx, by, bz, ids) -> bool:
        dx, dy = bx - ax, by - ay
        eax, eay = self.EAX[ids], self.EAY[ids]
        ex, ey = self.EBX[ids] - eax, self.EBY[ids] - eay
        den = dx * ey - dy * ex
        wx, wy = eax - ax, eay - ay
        den = np.where(den == 0.0, 1e-300, den)
        t = (wx * ey - wy * ex) / den
        u = (wx * dy - wy * dx) / den
        hit = (t >= 0.0) & (t <= 1.0) & (u >= 0.0) & (u <= 1.0)
        if not hit.any():
            return False
        t = t[hit]
        idh = ids[hit]
        z = az + (bz - az) * t
        if ((z >= self.EBASE[idh]) & (z <= self.ETOP[idh])).any():
            return True
        # pass-through of a slab between two side crossings (enter above top, leave below base or reverse)
        if az == bz:
            return False
        pids = self.EP[idh]
        for k in set(pids.tolist()):
            m = pids == k
            zk = z[m]
            base, top = self.p_base[k], self.p_top[k]
            if zk.min() < base and zk.max() > top:
                tk = np.sort(t[m])
                inside0 = self._inside_prism(k, ax, ay)
                bounds = [0.0] + tk.tolist() + [1.0]
                ins = inside0
                for q in range(len(bounds) - 1):
                    if ins:
                        z0 = az + (bz - az) * bounds[q]
                        z1 = az + (bz - az) * bounds[q + 1]
                        if min(z0, z1) <= top and max(z0, z1) >= base:
                            return True
                    ins = not ins
        return False

    def _terrain_hit(self, ax, ay, az, bx, by, bz) -> bool:
        L = math.hypot(bx - ax, by - ay)
        n = int(L / self.step) + 2
        if n <= 2:
            return False
        t = np.linspace(0.0, 1.0, n)[1:-1]
        # ignore the first/last 0.6 m (feet-level endpoints sit on the bilinear surface)
        if L > 1.5:
            m = (t * L > 0.6) & ((1 - t) * L > 0.6)
            t = t[m]
        if t.size == 0:
            return False
        xs = ax + (bx - ax) * t
        ys = ay + (by - ay) * t
        zs = az + (bz - az) * t
        fx = np.clip((xs - self.x0) / self.step, 0, self.nx - 1.001)
        fy = np.clip((ys - self.y0) / self.step, 0, self.ny - 1.001)
        i = fx.astype(np.int32)
        j = fy.astype(np.int32)
        u, v = fx - i, fy - j
        H = self.H
        h = (H[j, i] * (1 - u) + H[j, i + 1] * u) * (1 - v) + (H[j + 1, i] * (1 - u) + H[j + 1, i + 1] * u) * v
        return bool((zs < h - 0.05).any())

    def _trees_block(self, ax, ay, az, bx, by, bz, cells) -> bool:
        ct = self.cell_trees
        parts = [ct[c] for c in cells if ct[c] is not None]
        if not parts:
            return False
        ids = np.unique(np.concatenate(parts)) if len(parts) > 1 else parts[0]
        dx, dy, dz = bx - ax, by - ay, bz - az
        # trunks: vertical cylinders from z to z + crownBase
        tx, ty = self.TX[ids], self.TY[ids]
        L2 = dx * dx + dy * dy
        if L2 > 1e-9:
            s = np.clip(((tx - ax) * dx + (ty - ay) * dy) / L2, 0.0, 1.0)
            d = np.hypot(ax + dx * s - tx, ay + dy * s - ty)
            zs = az + dz * s
            if ((d <= self.TR[ids]) & (zs >= self.TZ[ids]) & (zs <= self.TZ[ids] + self.CB[ids])).any():
                return True
        # crowns: ellipsoid chords
        cr = np.maximum(self.CR[ids], 0.3)
        hz = self.CHZ[ids]
        px, py, pz = (ax - self.CX[ids]) / cr, (ay - self.CY[ids]) / cr, (az - self.CZ[ids]) / hz
        qx, qy, qz = dx / cr, dy / cr, dz / hz
        A = qx * qx + qy * qy + qz * qz
        Bq = 2 * (px * qx + py * qy + pz * qz)
        C = px * px + py * py + pz * pz - 1.0
        disc = Bq * Bq - 4 * A * C
        m = disc > 0
        if not m.any():
            return False
        sq = np.sqrt(disc[m])
        A2 = 2 * A[m]
        t1 = np.clip((-Bq[m] - sq) / A2, 0.0, 1.0)
        t2 = np.clip((-Bq[m] + sq) / A2, 0.0, 1.0)
        chord = float(((t2 - t1).clip(min=0)).sum()) * math.sqrt(dx * dx + dy * dy + dz * dz)
        return math.exp(-self.canopy_density * chord) < self.canopy_block_t

    def shot_clear(self, a: Vec3, b: Vec3) -> bool:
        """Projectile/beam path a->b clear of prisms and terrain (trees never block shots)."""
        try:
            key = (round(a[0], 1), round(a[1], 1), round(a[2], 1), round(b[0], 1), round(b[1], 1), round(b[2], 1), 0)
            r = self._los_cache.get(key)
            if r is None:
                r = not self._seg_blocked(a, b, trees=False)
                self._los_cache[key] = r
            return r
        except Exception:
            return True

    def los(self, a: Vec3, b: Vec3) -> bool:
        """Sight line a->b clear of buildings, terrain, trunks and dense canopy (vision rules, §8)."""
        try:
            key = (round(a[0], 1), round(a[1], 1), round(a[2], 1), round(b[0], 1), round(b[1], 1), round(b[2], 1), 1)
            r = self._los_cache.get(key)
            if r is None:
                r = not self._seg_blocked(a, b, trees=True)
                self._los_cache[key] = r
            return r
        except Exception:
            return True

    def shot_clear_many(self, a: Vec3, pts: Sequence[Vec3]) -> List[bool]:
        """shot_clear from one origin to many points (shares cell gathering)."""
        return [self.shot_clear(a, p) for p in pts]

    def los_many(self, a: Vec3, pts: Sequence[Vec3]) -> List[bool]:
        return [self.los(a, p) for p in pts]

    # ---- mech-level helpers
    def can_see(self, obs_feet: Vec3, tgt_feet: Vec3, obs_cubes=0, tgt_cubes=0, tgt_height=9.0) -> bool:
        """Vision rule: observer eye -> target centre or top (trees count)."""
        so, stg = size_scale(obs_cubes), size_scale(tgt_cubes)
        eye = (obs_feet[0], obs_feet[1], obs_feet[2] + 8.0 * so)
        h = tgt_height * stg
        return (self.los(eye, (tgt_feet[0], tgt_feet[1], tgt_feet[2] + 0.5 * h))
                or self.los(eye, (tgt_feet[0], tgt_feet[1], tgt_feet[2] + h)))

    def can_shoot(self, shooter_feet: Vec3, tgt_feet: Vec3, shooter_cubes=0, tgt_cubes=0) -> Optional[Vec3]:
        """Best clear aim point on a target mech's body from the shooter's muzzle (gun/laser), or None.

        The segment stops at the target cylinder surface so a target hugging a wall still counts."""
        so, stg = size_scale(shooter_cubes), size_scale(tgt_cubes)
        mx, my, mz = shooter_feet[0], shooter_feet[1], shooter_feet[2] + 7.0 * so
        r = 2.5 * stg
        dx, dy = tgt_feet[0] - mx, tgt_feet[1] - my
        d = math.hypot(dx, dy)
        f = max(0.0, (d - r * 0.8) / d) if d > 1e-6 else 0.0
        for hz in (4.5, 7.0, 2.0, 8.5):
            z = tgt_feet[2] + hz * stg
            end = (mx + dx * f, my + dy * f, mz + (z - mz) * f)
            if self.shot_clear((mx, my, mz), end):
                return (tgt_feet[0], tgt_feet[1], z)
        return None

    # ------------------------------------------------------------------ walkability
    def size_class(self, cubes: float = 0) -> int:
        if not self.ok_nav:
            return 0
        need = 2.5 * size_scale(cubes) + 0.25
        for k, rp in enumerate(self.r_plan):
            if rp >= need:
                return k
        return self.K - 1

    def walkable(self, x, y, k=0) -> bool:
        if not self.ok_nav:
            return True
        return bool((self._Wb[self._vidx(x, y)] >> k) & 1)

    def clearance(self, x, y) -> float:
        """Distance (m, capped 8) from (x, y) to the nearest wall for a mech standing at the ground surface."""
        if not self.ok_nav:
            return 8.0
        return self._DWb[self._vidx(x, y)] / 10.0

    def surface(self, x, y) -> float:
        """Baked ground-column surface (roof top inside buildings, deck on low bridges, else terrain)."""
        if not self.ok_nav:
            return self.height(x, y)
        v = self._vidx(x, y)
        if self._Kb[v] & 15 == 0:
            return self.height(x, y)
        return self._Gl[v]

    def walk_line(self, x0, y0, x1, y1, k=0, step=0.5) -> bool:
        """Straight walk from (x0,y0) to (x1,y1) stays on the main walkable component of class k with no
        ledge taller than step_up (vectorised; ~20 us)."""
        if not self.ok_nav:
            return True
        L = math.hypot(x1 - x0, y1 - y0)
        n = int(L / step) + 2
        t = np.linspace(0.0, 1.0, n)
        i = np.rint((x0 + (x1 - x0) * t - self.x0) / self.step).astype(np.int32)
        j = np.rint((y0 + (y1 - y0) * t - self.y0) / self.step).astype(np.int32)
        if i.min() < 0 or j.min() < 0 or i.max() >= self.nx or j.max() >= self.ny:
            return False
        if not ((self.WALK[j, i] >> k) & 1).all():
            return False
        g = self.G[j, i]
        return bool((np.diff(g) <= STEP_UP).all())

    # ------------------------------------------------------------------ lattice graph
    def _node_xy(self, n, k):
        xs, ys = self.NXY[k]
        return xs[n], ys[n]

    def snap(self, x, y, k=0, max_r=3, need_line=True) -> int:
        """Nearest lattice node (id) to (x, y) for class k, -1 if none within max_r blocks."""
        if not self.ok_nav:
            return -1
        B = self.block
        bi = int((x - self.x0) / self.step) // B
        bj = int((y - self.y0) / self.step) // B
        off = self.node_off[k]
        xs, ys = self.NXY[k]
        best, bd = -1, 1e18
        fallback, fd = -1, 1e18
        for r in range(0, max_r + 1):
            for dj in range(-r, r + 1):
                for di in range(-r, r + 1):
                    if max(abs(di), abs(dj)) != r:
                        continue
                    i, j = bi + di, bj + dj
                    if not (0 <= i < self.BX and 0 <= j < self.BY):
                        continue
                    n = j * self.BX + i
                    if off[n] == 255:
                        continue
                    d = (xs[n] - x) ** 2 + (ys[n] - y) ** 2
                    if d < fd:
                        fallback, fd = n, d
                    if d < bd and (not need_line or self.walk_line(x, y, xs[n], ys[n], k)):
                        best, bd = n, d
            if best >= 0 and r >= 1:
                break
        return best if best >= 0 else fallback

    def _search(self, s: _Search, start: int, budget_s: float) -> bool:
        """Advance reverse search toward `start`. True when start is closed (path known)."""
        if start in s.closed:
            return True
        if s.done_fail:
            return False
        k = s.k
        xs, ys = self.NXY[k]
        em = self.emask[k]
        pen = self.NPEN[k]
        DOFF, DLEN = self.DOFF, self.DLEN
        W = self.W_ASTAR
        sx, sy = xs[start], ys[start]
        if s.target != start:
            # re-target the heuristic (the start moved): rebuild priorities
            s.target = start
            s.open = [(s.g[n] + W * math.hypot(xs[n] - sx, ys[n] - sy), n) for (_, n) in s.open if n not in s.closed]
            heapq.heapify(s.open)
        if not s.open and not s.closed:
            n = s.goal
            s.open = [(W * math.hypot(xs[n] - sx, ys[n] - sy), n)]
        g, parent, closed, op = s.g, s.parent, s.closed, s.open
        push, pop = heapq.heappush, heapq.heappop
        t_end = time.perf_counter() + budget_s
        cnt = 0
        while op:
            f, n = pop(op)
            if n in closed:
                continue
            closed.add(n)
            s.expanded += 1
            if n == start:
                return True
            gn = g[n]
            cnt += 1
            if cnt & 63 == 0 and time.perf_counter() > t_end:
                push(op, (f, n))
                closed.discard(n)
                return False
            # reverse search: we need edges m -> n (walking from m to n). Edge bit REV[d] at m.
            for d in range(8):
                m = n + DOFF[d]
                if m < 0 or m >= len(em):
                    continue
                if not (em[m] >> REV[d]) & 1:
                    continue
                if m in closed:
                    continue
                gm = gn + DLEN[d] + pen[m]
                if gm < g.get(m, 1e18):
                    g[m] = gm
                    parent[m] = n
                    push(op, (gm + W * math.hypot(xs[m] - sx, ys[m] - sy), m))
        s.done_fail = True
        return False

    def _get_search(self, goal: int, k: int, start: int) -> _Search:
        key = (goal, k)
        s = self._searches.get(key)
        if s is None:
            if len(self._searches) >= self.MAX_SEARCHES:
                old = min(self._searches.items(), key=lambda kv: kv[1].t_last)[0]
                del self._searches[old]
            s = _Search(goal, k, start)
            self._searches[key] = s
        s.t_last = time.perf_counter()
        return s

    def plan_nodes(self, start: Vec3, goal: Vec3, k=0, budget_ms=3.0):
        """(status, node list start..goal). status: 'ok' | 'pending' | 'fail' | 'nonav'."""
        if not self.ok_nav:
            return "nonav", []
        sn = self.snap(start[0], start[1], k, max_r=3)
        gn = self.snap(goal[0], goal[1], k, max_r=6, need_line=False)
        if sn < 0 or gn < 0:
            return "fail", []
        gx, gy = self._node_xy(gn, k)
        self.last_goal_snapped = math.hypot(gx - goal[0], gy - goal[1]) < 4.0
        if sn == gn:
            return "ok", [sn]
        s = self._get_search(gn, k, sn)
        if not self._search(s, sn, budget_ms / 1000.0):
            return ("fail" if s.done_fail else "pending"), []
        out = [sn]
        n = sn
        par = s.parent
        while n != gn and len(out) < 5000:
            n = par[n]
            if n < 0:
                break
            out.append(n)
        return "ok", out

    def smooth(self, x0, y0, nodes: List[int], k=0, max_checks=80) -> List[Tuple[float, float]]:
        """String-pull a node path from (x0, y0) with walk-line checks. Returns 2D waypoints (excl. start)."""
        xs, ys = self.NXY[k]
        pts = [(xs[n], ys[n]) for n in nodes]
        if not pts:
            return []
        out = []
        ax, ay = x0, y0
        i = 0
        n = len(pts)
        checks = 0
        while i < n:
            if checks >= max_checks:
                out.extend(pts[i:])
                break
            hi = min(n - 1, i + 12)
            lo = i
            # farthest j in [i, hi] walkable in a straight line from (ax, ay) (binary search)
            if self.walk_line(ax, ay, pts[hi][0], pts[hi][1], k):
                j = hi
                checks += 1
            else:
                checks += 1
                j = lo
                a, b = lo, hi - 1
                while a <= b and checks < max_checks:
                    mid = (a + b) // 2
                    checks += 1
                    if self.walk_line(ax, ay, pts[mid][0], pts[mid][1], k):
                        j = mid
                        a = mid + 1
                    else:
                        b = mid - 1
            out.append(pts[j])
            ax, ay = pts[j]
            i = j + 1
        return out

    def plan(self, start: Vec3, goal: Vec3, cubes: float = 0, budget_ms: float = 3.0) -> List[Vec3]:
        """Walkable waypoints from start to goal (excluding start, including goal). [] if unreachable.

        If the search has not finished within budget_ms, returns [goal] (straight line) and keeps the
        search state: calling again (any start nearby) continues it."""
        t0 = time.perf_counter()
        self.stats["plan_calls"] += 1
        try:
            if not self.ok_nav:
                return [tuple(goal)]
            k = self.size_class(cubes)
            st, nodes = self.plan_nodes(start, goal, k, budget_ms)
            if st == "fail":
                self.last_raw_path = []
                return []
            if st != "ok":
                self.last_raw_path = []
                return [tuple(goal)]
            xs, ys = self.NXY[k]
            self.last_raw_path = [(xs[n], ys[n]) for n in nodes]
            pts = self.smooth(start[0], start[1], nodes, k)
            # final hop to the true goal when it is walkable from the last node
            gx, gy = float(goal[0]), float(goal[1])
            if pts and math.hypot(pts[-1][0] - gx, pts[-1][1] - gy) > 0.5:
                if self.walk_line(pts[-1][0], pts[-1][1], gx, gy, k) or not self.last_goal_snapped:
                    pts.append((gx, gy))
            if len(pts) >= 2 and self.walk_line(start[0], start[1], pts[1][0], pts[1][1], k):
                pts = pts[1:]
            out = [(x, y, self.surface(x, y)) for (x, y) in pts]
            if out and math.hypot(out[-1][0] - gx, out[-1][1] - gy) < 0.6:
                out[-1] = (gx, gy, float(goal[2]) if len(goal) > 2 else out[-1][2])
            return out or [tuple(goal)]
        except Exception as e:
            _log("plan error", repr(e))
            return [tuple(goal)]
        finally:
            dt = (time.perf_counter() - t0) * 1000
            if dt > self.stats["plan_ms_max"]:
                self.stats["plan_ms_max"] = dt

    def path_len(self, start: Vec3, goal: Vec3, cubes: float = 0, budget_ms: float = 2.0) -> float:
        """Length (m) along the planned path; math.inf if unreachable. While the search is still pending,
        returns a conservative estimate (1.35 x straight line)."""
        d = math.hypot(goal[0] - start[0], goal[1] - start[1])
        if not self.ok_nav:
            return d
        try:
            k = self.size_class(cubes)
            st, nodes = self.plan_nodes(start, goal, k, budget_ms)
            if st == "fail":
                return math.inf
            if st != "ok":
                return d * 1.35
            xs, ys = self.NXY[k]
            L = math.hypot(xs[nodes[0]] - start[0], ys[nodes[0]] - start[1])
            for a, b in zip(nodes, nodes[1:]):
                L += math.hypot(xs[b] - xs[a], ys[b] - ys[a])
            L += math.hypot(goal[0] - xs[nodes[-1]], goal[1] - ys[nodes[-1]])
            return L * 0.97   # lattice paths are slightly longer than smoothed ones
        except Exception:
            return d * 1.35

    # ------------------------------------------------------------------ tactics
    def nearest_cover(self, pos: Vec3, threat_pos, max_dist: float = 60.0, cubes: float = 0,
                      budget_ms: float = 3.0) -> Optional[Vec3]:
        """Nearby reachable feet position hidden (shots and sight) from the threat(s), or None.

        threat_pos: one feet position or a list of them."""
        if not threat_pos:
            return None
        threats = [threat_pos] if isinstance(threat_pos[0], (int, float)) else list(threat_pos)
        t_end = time.perf_counter() + budget_ms / 1000.0
        k = self.size_class(cubes)
        x, y = float(pos[0]), float(pos[1])
        cands = self._candidate_spots(x, y, max_dist, k)
        cands.sort(key=lambda c: c[2])
        sc = size_scale(cubes)
        for (cx, cy, dd) in cands:
            if time.perf_counter() > t_end:
                break
            cz = self.surface(cx, cy)
            hidden = True
            for tp in threats:
                eye = (tp[0], tp[1], tp[2] + 8.0)
                mz = (tp[0], tp[1], tp[2] + 7.0)
                for hz in (4.5 * sc, 8.5 * sc):
                    if self.shot_clear(mz, (cx, cy, cz + hz)) or self.shot_clear(eye, (cx, cy, cz + hz)):
                        hidden = False
                        break
                if not hidden:
                    break
            if hidden:
                return (cx, cy, cz)
        return None

    def _candidate_spots(self, x, y, R, k):
        """Lattice nodes within R of (x, y) for class k: (x, y, straight distance)."""
        if not self.ok_nav:
            out = []
            for a in range(16):
                for r in (10.0, 20.0, 35.0, 50.0):
                    if r <= R:
                        px, py = x + r * math.cos(a * math.pi / 8), y + r * math.sin(a * math.pi / 8)
                        out.append((px, py, r))
            return out
        B = self.block
        bi = int((x - self.x0) / self.step) // B
        bj = int((y - self.y0) / self.step) // B
        rb = int(R / B) + 1
        off = self.node_off[k]
        xs, ys = self.NXY[k]
        out = []
        for j in range(max(0, bj - rb), min(self.BY, bj + rb + 1)):
            for i in range(max(0, bi - rb), min(self.BX, bi + rb + 1)):
                n = j * self.BX + i
                if off[n] == 255:
                    continue
                d = math.hypot(xs[n] - x, ys[n] - y)
                if d <= R:
                    out.append((xs[n], ys[n], d))
        return out
