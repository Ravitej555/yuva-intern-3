"""
Vector2 - 2D vector math for physics and gameplay.

Uses operator overloading and provides common game-math utilities.
Optimized for high-performance physics loops with in-place operations,
distance-squared metrics, zero-division guards, and minimal allocations.
"""
from __future__ import annotations
import math


class Vector2:
    """High-performance 2D vector with value semantics and optional in-place ops."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = float(x)
        self.y = float(y)

    # --- Factory ---
    @staticmethod
    def zero() -> Vector2:
        return Vector2(0.0, 0.0)

    @staticmethod
    def one() -> Vector2:
        return Vector2(1.0, 1.0)

    @staticmethod
    def from_angle(angle_rad: float, magnitude: float = 1.0) -> Vector2:
        return Vector2(math.cos(angle_rad) * magnitude,
                       math.sin(angle_rad) * magnitude)

    # --- Iterable unpacking ---
    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        raise IndexError("Vector2 index out of range (must be 0 or 1)")

    # --- Arithmetic ---
    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __iadd__(self, other: Vector2) -> Vector2:
        self.x += other.x
        self.y += other.y
        return self

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __isub__(self, other: Vector2) -> Vector2:
        self.x -= other.x
        self.y -= other.y
        return self

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __imul__(self, scalar: float) -> Vector2:
        self.x *= scalar
        self.y *= scalar
        return self

    def __rmul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        if scalar == 0.0:
            return Vector2.zero()
        inv = 1.0 / scalar
        return Vector2(self.x * inv, self.y * inv)

    def __itruediv__(self, scalar: float) -> Vector2:
        if scalar == 0.0:
            self.x = 0.0
            self.y = 0.0
        else:
            inv = 1.0 / scalar
            self.x *= inv
            self.y *= inv
        return self

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return math.isclose(self.x, other.x, abs_tol=1e-6) and \
               math.isclose(self.y, other.y, abs_tol=1e-6)

    def __repr__(self) -> str:
        return f"Vector2({self.x:.3f}, {self.y:.3f})"

    # --- Vector operations ---
    def dot(self, other: Vector2) -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2) -> float:
        """2D cross product (scalar z-component)."""
        return self.x * other.y - self.y * other.x

    def magnitude(self) -> float:
        return math.hypot(self.x, self.y)

    def magnitude_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vector2:
        """Return unit vector. Zero vector returns zero."""
        sq = self.x * self.x + self.y * self.y
        if sq < 1e-18:
            return Vector2.zero()
        inv_mag = 1.0 / math.sqrt(sq)
        return Vector2(self.x * inv_mag, self.y * inv_mag)

    def distance_to(self, other: Vector2) -> float:
        dx = other.x - self.x
        dy = other.y - self.y
        return math.hypot(dx, dy)

    def distance_sq_to(self, other: Vector2) -> float:
        """Fast squared distance avoiding expensive square root."""
        dx = other.x - self.x
        dy = other.y - self.y
        return dx * dx + dy * dy

    def angle(self) -> float:
        """Angle in radians from +X axis."""
        return math.atan2(self.y, self.x)

    def lerp(self, other: Vector2, t: float) -> Vector2:
        return Vector2(self.x + (other.x - self.x) * t,
                       self.y + (other.y - self.y) * t)

    def clamp_magnitude(self, max_len: float) -> Vector2:
        sq = self.x * self.x + self.y * self.y
        if sq > max_len * max_len and sq > 1e-18:
            factor = max_len / math.sqrt(sq)
            return Vector2(self.x * factor, self.y * factor)
        return Vector2(self.x, self.y)

    def copy(self) -> Vector2:
        return Vector2(self.x, self.y)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

