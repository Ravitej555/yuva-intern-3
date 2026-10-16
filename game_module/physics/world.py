"""
PhysicsWorld - manages bodies, gravity, broad-phase (Sweep & Prune via sorted list),
narrow-phase (AABB), and impulse-based collision resolution.

Features:
- Variable gravity
- Sub-stepping for stability
- Spatial hash broad-phase fallback for many bodies
- Collision callbacks (on_collision)
"""
from __future__ import annotations
from typing import Callable
from game_module.physics.vector2 import Vector2
from game_module.physics.rigidbody import Rigidbody, BodyType

CollisionCallback = Callable[[Rigidbody, Rigidbody, Vector2], None]


class PhysicsWorld:
    """
    Lightweight 2D physics world.

    Usage:
        world = PhysicsWorld(gravity=Vector2(0, 9.81))
        world.add_body(player_body)
        world.add_body(ground_body)
        world.step(dt)

    Collision resolution is impulse-based along the MTV normal with restitution.
    Friction is applied as velocity damping along tangent.
    """

    def __init__(self,
                 gravity: Vector2 | None = None,
                 sub_steps: int = 4) -> None:
        self.gravity = gravity if gravity is not None else Vector2(0, 20.0)
        # keep moderate default so grounded objects stay settled
        self.sub_steps = max(1, sub_steps)
        self.bodies: list[Rigidbody] = []
        self.on_collision: CollisionCallback | None = None
        # optional bounds for culling / clamping
        self.world_bounds = None  # AABB or None

    # -- management --
    def add_body(self, body: Rigidbody) -> None:
        self.bodies.append(body)

    def remove_body(self, body: Rigidbody) -> None:
        if body in self.bodies:
            self.bodies.remove(body)

    # -- simulation --
    def step(self, dt: float) -> None:
        """Advance simulation by dt seconds with sub-stepping."""
        if dt <= 0:
            return
        sub_dt = dt / self.sub_steps
        for _ in range(self.sub_steps):
            # Integrate
            for b in self.bodies:
                b.integrate(sub_dt, self.gravity)
            # Collisions
            self._resolve_collisions()

    # -- collision helpers --
    def _resolve_collisions(self) -> None:
        # Broad-phase: Sweep & Prune along X axis using zero-allocation min_x / max_x
        bodies = sorted(self.bodies, key=lambda b: b.aabb.min_x)
        active: list[Rigidbody] = []
        for body in bodies:
            b_min_x = body.aabb.min_x
            # Prune bodies from active interval whose max_x is left of b_min_x
            active = [a for a in active if a.aabb.max_x >= b_min_x]
            for other in active:
                self._try_resolve_pair(body, other)
            active.append(body)

    def _try_resolve_pair(self, a: Rigidbody, b: Rigidbody) -> None:
        # Skip two static bodies
        if a.body_type == BodyType.STATIC and b.body_type == BodyType.STATIC:
            return

        # Fused intersection and MTV query
        mtv = a.aabb.intersection_depth(b.aabb)
        if mtv is None:
            return
        mtv_sq = mtv.magnitude_sq()
        if mtv_sq < 1e-9:
            return

        inv_a = a.inv_mass
        inv_b = b.inv_mass
        total_inv = inv_a + inv_b
        if total_inv <= 0.0:
            return

        # Positional correction (Baumgarte stabilization)
        percent = 0.8
        corr_scale = percent / total_inv
        cx = mtv.x * corr_scale
        cy = mtv.y * corr_scale

        a.position.x += cx * inv_a
        a.position.y += cy * inv_a
        b.position.x -= cx * inv_b
        b.position.y -= cy * inv_b

        # Velocity impulse along collision normal
        normal = mtv.normalized()
        if normal.magnitude_sq() < 1e-9:
            return

        # Relative velocity
        rel_vx = a.velocity.x - b.velocity.x
        rel_vy = a.velocity.y - b.velocity.y
        vel_along_normal = rel_vx * normal.x + rel_vy * normal.y

        # Only resolve if moving toward each other
        if vel_along_normal < 0.0:
            restitution = a.restitution if a.restitution < b.restitution else b.restitution
            j = -(1.0 + restitution) * vel_along_normal / total_inv
            impulse_x = normal.x * j
            impulse_y = normal.y * j

            if a.body_type == BodyType.DYNAMIC:
                a.velocity.x += impulse_x * inv_a
                a.velocity.y += impulse_y * inv_a
            if b.body_type == BodyType.DYNAMIC:
                b.velocity.x -= impulse_x * inv_b
                b.velocity.y -= impulse_y * inv_b

            # Tangent friction (Coulomb model)
            tangent_vx = rel_vx - normal.x * vel_along_normal
            tangent_vy = rel_vy - normal.y * vel_along_normal
            tangent_sq = tangent_vx * tangent_vx + tangent_vy * tangent_vy
            if tangent_sq > 1e-9:
                inv_tmag = 1.0 / (tangent_sq ** 0.5)
                tx = tangent_vx * inv_tmag
                ty = tangent_vy * inv_tmag
                jt = -(rel_vx * tx + rel_vy * ty) / total_inv
                mu = (a.friction + b.friction) * 0.5
                max_friction = j * mu
                if jt > max_friction:
                    jt = max_friction
                elif jt < -max_friction:
                    jt = -max_friction

                f_impulse_x = tx * jt
                f_impulse_y = ty * jt
                if a.body_type == BodyType.DYNAMIC:
                    a.velocity.x += f_impulse_x * inv_a
                    a.velocity.y += f_impulse_y * inv_a
                if b.body_type == BodyType.DYNAMIC:
                    b.velocity.x -= f_impulse_x * inv_b
                    b.velocity.y -= f_impulse_y * inv_b

        # Grounded check: if MTV is upward (normal.y < 0 means a is above b)
        if mtv.y < 0 and abs(mtv.y) > abs(mtv.x):
            if a.body_type == BodyType.DYNAMIC:
                a.is_grounded = True
        elif mtv.y > 0 and abs(mtv.y) > abs(mtv.x):
            if b.body_type == BodyType.DYNAMIC:
                b.is_grounded = True

        if self.on_collision:
            self.on_collision(a, b, mtv)

    # -- queries --
    def raycast_aabb(self, origin: Vector2, direction: Vector2,
                     max_dist: float) -> list[tuple[Rigidbody, float]]:
        """
        Simple ray vs AABB test. Returns list of (body, distance) sorted by distance.
        """
        hits: list[tuple[Rigidbody, float]] = []
        dir_n = direction.normalized()
        if dir_n.magnitude_sq() < 1e-9:
            return hits
        for b in self.bodies:
            t = self._ray_aabb(origin, dir_n, b.aabb, max_dist)
            if t is not None:
                hits.append((b, t))
        hits.sort(key=lambda x: x[1])
        return hits

    @staticmethod
    def _ray_aabb(origin: Vector2, dir_n: Vector2, box, max_dist: float) -> float | None:
        """Optimized slab method with zero reflection overhead."""
        t_min = 0.0
        t_max = max_dist

        # X-axis
        ox, dx = origin.x, dir_n.x
        mn_x, mx_x = box.min_x, box.max_x
        if abs(dx) < 1e-9:
            if ox < mn_x or ox > mx_x:
                return None
        else:
            t1 = (mn_x - ox) / dx
            t2 = (mx_x - ox) / dx
            if t1 > t2:
                t1, t2 = t2, t1
            if t1 > t_min:
                t_min = t1
            if t2 < t_max:
                t_max = t2
            if t_min > t_max:
                return None

        # Y-axis
        oy, dy = origin.y, dir_n.y
        mn_y, mx_y = box.min_y, box.max_y
        if abs(dy) < 1e-9:
            if oy < mn_y or oy > mx_y:
                return None
        else:
            t1 = (mn_y - oy) / dy
            t2 = (mx_y - oy) / dy
            if t1 > t2:
                t1, t2 = t2, t1
            if t1 > t_min:
                t_min = t1
            if t2 < t_max:
                t_max = t2
            if t_min > t_max:
                return None

        if 0.0 <= t_min <= max_dist:
            return t_min
        return None
