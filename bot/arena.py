"""Map geometry. OWNER: nav. This is the integrator's placeholder with the agreed signatures.

Arena.load(map_dir) must finish well inside the 20 s hello budget on 1 CPU (target < 4 s).
"""
from __future__ import annotations

import math
import os
from typing import List, Optional, Sequence

Vec3 = Sequence[float]


class Arena:
    def __init__(self, map_dir: str):
        self.map_dir = map_dir

    @classmethod
    def load(cls, map_dir: str) -> "Arena":
        return cls(map_dir)

    def height(self, x: float, y: float) -> float:
        """Terrain ground height (bilinear), ignoring prisms."""
        return 0.0

    def ground_z(self, x: float, y: float, z_hint: Optional[float] = None) -> float:
        """Top walkable surface at (x, y) at or below z_hint (roof or terrain)."""
        return self.height(x, y)

    def los(self, a: Vec3, b: Vec3) -> bool:
        """Sight line a->b clear of buildings/terrain (vision; trees approximated)."""
        return True

    def shot_clear(self, a: Vec3, b: Vec3) -> bool:
        """Projectile/beam ray a->b clear of prisms and terrain (trees never block shots)."""
        return True

    def plan(self, start: Vec3, goal: Vec3) -> List[Vec3]:
        """Walkable waypoints from start to goal (excluding start, including goal). [] if unreachable."""
        return [tuple(goal)]

    def path_len(self, start: Vec3, goal: Vec3) -> float:
        """Length (m) of plan(start, goal); math.inf if unreachable."""
        return math.dist(start[:2], goal[:2])

    def nearest_cover(self, pos: Vec3, threat_pos: Vec3, max_dist: float = 60.0) -> Optional[Vec3]:
        """Nearby reachable feet position with no LOS from threat_pos (eye height), or None."""
        return None

    def inside_solid(self, p: Vec3) -> bool:
        return False
