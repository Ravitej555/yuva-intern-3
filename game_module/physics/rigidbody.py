"""
Rigidbody - simple 2D rigid body with Newtonian integration.

Supports forces, impulses, gravity, friction, restitution, and static/kinematic modes.
Uses semi-implicit Euler integration and zero-allocation AABB caching.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from game_module.physics.vector2 import Vector2
from game_module.physics.aabb import AABB


class BodyType(Enum):
    DYNAMIC = auto()    # affected by forces & collisions
    KINEMATIC = auto()  # moved explicitly, infinite mass
    STATIC = auto()     # immovable


@dataclass
class Rigidbody:
    """
    Minimal rigid body.
    - mass <= 0 treated as infinite mass (static-like).
    - Use add_force for continuous forces, add_impulse for instant velocity change.
    """

    # Identity
    name: str = "body"
    body_type: BodyType = BodyType.DYNAMIC
    position: Vector2 = field(default_factory=Vector2.zero)
    velocity: Vector2 = field(default_factory=Vector2.zero)

    # Physical properties
    mass: float = 1.0
    size: Vector2 = field(default_factory=lambda: Vector2(1, 1))  # full width/height
    restitution: float = 0.2   # bounciness [0,1]
    friction: float = 0.3      # [0,1]
    drag: float = 0.01         # linear air drag
    gravity_scale: float = 1.0

    # State
    is_grounded: bool = False
    _force: Vector2 = field(default_factory=Vector2.zero, init=False, repr=False)
    _cached_aabb: AABB = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._cached_aabb = AABB(
            self.position,
            Vector2(self.size.x * 0.5, self.size.y * 0.5)
        )

    @property
    def inv_mass(self) -> float:
        if self.body_type != BodyType.DYNAMIC or self.mass <= 0:
            return 0.0
        return 1.0 / self.mass

    @property
    def aabb(self) -> AABB:
        # Keep center and half_size synchronized with zero allocation
        aabb = self._cached_aabb
        if aabb is None:
            self._cached_aabb = AABB(
                self.position,
                Vector2(self.size.x * 0.5, self.size.y * 0.5)
            )
            return self._cached_aabb
        aabb.center = self.position
        aabb.half_size.x = self.size.x * 0.5
        aabb.half_size.y = self.size.y * 0.5
        return aabb

    # ---- Force application ----
    def add_force(self, force: Vector2) -> None:
        """Accumulate force for next integration step (F = m*a)."""
        if self.body_type == BodyType.DYNAMIC:
            self._force.x += force.x
            self._force.y += force.y

    def add_impulse(self, impulse: Vector2) -> None:
        """Instant velocity change: delta_v = impulse / mass."""
        if self.body_type == BodyType.DYNAMIC:
            inv = self.inv_mass
            if inv > 0:
                self.velocity.x += impulse.x * inv
                self.velocity.y += impulse.y * inv

    def add_force_at_position(self, force: Vector2, world_pos: Vector2) -> None:
        """Simplified: treat as force at center (no torque in this 2D model)."""
        self.add_force(force)

    # ---- Integration ----
    def integrate(self, dt: float, gravity: Vector2) -> None:
        """
        Semi-implicit Euler integration using zero-allocation scalar arithmetic:
            v += (F/m + gravity*gravity_scale - drag*v) * dt
            p += v * dt
        """
        if self.body_type != BodyType.DYNAMIC:
            return

        inv_m = self.inv_mass
        g_scale = self.gravity_scale
        # Compute acceleration components directly
        ax = self._force.x * inv_m + gravity.x * g_scale - self.velocity.x * self.drag
        ay = self._force.y * inv_m + gravity.y * g_scale - self.velocity.y * self.drag

        # Integrate velocity
        self.velocity.x += ax * dt
        self.velocity.y += ay * dt

        # Integrate position
        self.position.x += self.velocity.x * dt
        self.position.y += self.velocity.y * dt

        # Reset force accumulator and contact state
        self._force.x = 0.0
        self._force.y = 0.0
        self.is_grounded = False

    def move_kinematic(self, delta: Vector2) -> None:
        if self.body_type == BodyType.KINEMATIC:
            self.position.x += delta.x
            self.position.y += delta.y

