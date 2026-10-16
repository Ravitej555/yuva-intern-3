"""
AABB - Axis-Aligned Bounding Box for collision detection.

Optimized with __slots__, zero-allocation point queries, direct axis accessors,
and fused overlap/MTV calculation.
"""
from __future__ import annotations
from game_module.physics.vector2 import Vector2


class AABB:
    """AABB defined by center and half-extents with zero-allocation query methods."""

    __slots__ = ("center", "half_size")

    def __init__(self, center: Vector2, half_size: Vector2) -> None:
        self.center = center
        self.half_size = half_size

    # Direct scalar bounds (zero heap allocations)
    @property
    def min_x(self) -> float:
        return self.center.x - self.half_size.x

    @property
    def max_x(self) -> float:
        return self.center.x + self.half_size.x

    @property
    def min_y(self) -> float:
        return self.center.y - self.half_size.y

    @property
    def max_y(self) -> float:
        return self.center.y + self.half_size.y

    @property
    def min(self) -> Vector2:
        return Vector2(self.center.x - self.half_size.x,
                       self.center.y - self.half_size.y)

    @property
    def max(self) -> Vector2:
        return Vector2(self.center.x + self.half_size.x,
                       self.center.y + self.half_size.y)

    @property
    def width(self) -> float:
        return self.half_size.x * 2.0

    @property
    def height(self) -> float:
        return self.half_size.y * 2.0

    @classmethod
    def from_min_max(cls, min_pt: Vector2, max_pt: Vector2) -> AABB:
        center = Vector2((min_pt.x + max_pt.x) * 0.5,
                         (min_pt.y + max_pt.y) * 0.5)
        half = Vector2((max_pt.x - min_pt.x) * 0.5,
                       (max_pt.y - min_pt.y) * 0.5)
        return cls(center, half)

    def contains_point(self, pt: Vector2) -> bool:
        """Zero-allocation point-in-box containment test."""
        cx, cy = self.center.x, self.center.y
        hx, hy = self.half_size.x, self.half_size.y
        return (cx - hx <= pt.x <= cx + hx) and (cy - hy <= pt.y <= cy + hy)

    def intersects(self, other: AABB) -> bool:
        """AABB-AABB overlap test."""
        return (abs(self.center.x - other.center.x) <= (self.half_size.x + other.half_size.x)) and \
               (abs(self.center.y - other.center.y) <= (self.half_size.y + other.half_size.y))

    def intersection_depth(self, other: AABB) -> Vector2 | None:
        """
        Fused intersection and minimum translation vector (MTV) calculation.
        Returns MTV to separate self from other, or None if not intersecting.
        """
        dx = self.center.x - other.center.x
        hx_sum = self.half_size.x + other.half_size.x
        px = hx_sum - abs(dx)
        if px <= 0:
            return None

        dy = self.center.y - other.center.y
        hy_sum = self.half_size.y + other.half_size.y
        py = hy_sum - abs(dy)
        if py <= 0:
            return None

        if px < py:
            sign_x = 1.0 if dx > 0 else (-1.0 if dx < 0 else 1.0)
            return Vector2(px * sign_x, 0.0)
        else:
            sign_y = 1.0 if dy > 0 else (-1.0 if dy < 0 else -1.0)
            return Vector2(0.0, py * sign_y)

    def expanded(self, amount: float) -> AABB:
        return AABB(self.center.copy(),
                    Vector2(self.half_size.x + amount, self.half_size.y + amount))

    def __repr__(self) -> str:
        return f"AABB(center={self.center}, half={self.half_size})"
