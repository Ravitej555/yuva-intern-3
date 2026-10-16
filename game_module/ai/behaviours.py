"""
Behaviour states for Enemy AI.

States:
- IdleState   : wait / look around, transitions to Chase if player in range
- PatrolState : walk between waypoints
- ChaseState  : pursue player, uses steering; fails -> Search
- AttackState : melee / ranged attack with cooldown
- FleeState   : retreat when low HP (with anti-thrashing hysteresis)

Optimized with O(1) waypoint indexing, distance-squared distance metrics,
and state oscillation guards.
"""
from __future__ import annotations
import random
from game_module.ai.state_machine import State
from game_module.physics.vector2 import Vector2

FLEE_HP_THRESHOLD = 0.25  # Unified low HP threshold (25% max HP)


class IdleState(State):
    name = "Idle"

    def __init__(self, idle_duration: float = 1.5,
                 chase_range: float = 8.0) -> None:
        self.idle_duration = idle_duration
        self.chase_range = chase_range
        self.chase_range_sq = chase_range * chase_range
        self._t = 0.0

    def on_enter(self, entity) -> None:
        self._t = 0.0
        entity.velocity_hint = Vector2.zero()

    def on_update(self, entity, dt: float) -> str | None:
        self._t += dt
        if entity.hp is not None and entity.hp < entity.max_hp * FLEE_HP_THRESHOLD:
            return "Flee"
        # Check for player using fast sensing
        if entity.can_see_player(self.chase_range):
            return "Chase"
        if self._t >= self.idle_duration:
            # Randomly patrol or keep idling
            return "Patrol" if random.random() < 0.7 else None
        return None


class PatrolState(State):
    name = "Patrol"

    def __init__(self, speed: float = 3.0, chase_range: float = 8.0) -> None:
        self.speed = speed
        self.chase_range = chase_range
        self._waypoint_arrival_dist_sq = 0.4 * 0.4

    def on_enter(self, entity) -> None:
        if not entity.waypoints:
            entity.waypoints = [entity.body.position.copy()]
        entity.current_waypoint_idx = getattr(entity, "current_waypoint_idx", 0)

    def on_update(self, entity, dt: float) -> str | None:
        if entity.hp is not None and entity.hp < entity.max_hp * FLEE_HP_THRESHOLD:
            return "Flee"
        if entity.can_see_player(self.chase_range):
            return "Chase"

        target = entity.waypoints[entity.current_waypoint_idx]
        dx = target.x - entity.body.position.x
        dy = target.y - entity.body.position.y
        dist_sq = dx * dx + dy * dy

        if dist_sq < self._waypoint_arrival_dist_sq:
            entity.current_waypoint_idx = (entity.current_waypoint_idx + 1) % len(entity.waypoints)
            return None

        # Steering: desired velocity using single-sqrt normalization
        inv_dist = 1.0 / (dist_sq ** 0.5)
        desired = Vector2(dx * inv_dist * self.speed, dy * inv_dist * self.speed)
        entity.velocity_hint = desired
        entity.steer_towards(desired, dt)
        return None


class ChaseState(State):
    name = "Chase"

    def __init__(self, speed: float = 5.0, attack_range: float = 1.2,
                 lose_range: float = 12.0) -> None:
        self.speed = speed
        self.attack_range = attack_range
        self.attack_range_sq = attack_range * attack_range
        self.lose_range = lose_range
        self.lose_range_sq = lose_range * lose_range
        self._wp_arrival_sq = 0.5 * 0.5

    def on_update(self, entity, dt: float) -> str | None:
        if entity.hp is not None and entity.hp < entity.max_hp * FLEE_HP_THRESHOLD:
            return "Flee"

        dist_sq = entity.body.position.distance_sq_to(entity.player_pos)
        if dist_sq > self.lose_range_sq:
            return "Idle"
        if dist_sq <= self.attack_range_sq:
            return "Attack"

        # Chase steering with O(1) waypoint traversal
        path = entity.path
        path_idx = getattr(entity, "path_index", 0)
        if path and path_idx < len(path):
            wp = path[path_idx]
            dx = wp.x - entity.body.position.x
            dy = wp.y - entity.body.position.y
            wp_dist_sq = dx * dx + dy * dy

            if wp_dist_sq < self._wp_arrival_sq:
                entity.path_index = path_idx + 1
                if entity.path_index >= len(path):
                    entity.request_path_recalc = True
            else:
                inv_dist = 1.0 / (wp_dist_sq ** 0.5)
                desired = Vector2(dx * inv_dist * self.speed, dy * inv_dist * self.speed)
                entity.steer_towards(desired, dt)
                return None

        # Direct pursuit steering
        dx = entity.player_pos.x - entity.body.position.x
        dy = entity.player_pos.y - entity.body.position.y
        curr_dist_sq = dx * dx + dy * dy
        if curr_dist_sq > 1e-9:
            inv_dist = 1.0 / (curr_dist_sq ** 0.5)
            desired = Vector2(dx * inv_dist * self.speed, dy * inv_dist * self.speed)
            entity.steer_towards(desired, dt)

        # Periodically request path recalculation
        entity.path_timer = getattr(entity, "path_timer", 0.0) + dt
        if entity.path_timer > 0.4:
            entity.path_timer = 0.0
            entity.request_path_recalc = True
        return None


class AttackState(State):
    name = "Attack"

    def __init__(self, cooldown: float = 0.8, attack_range: float = 1.5,
                 damage: float = 10.0) -> None:
        self.cooldown = cooldown
        self.attack_range = attack_range
        self.lose_attack_range_sq = (attack_range * 1.8) ** 2
        self.damage = damage
        self._t = 0.0

    def on_enter(self, entity) -> None:
        self._t = self.cooldown  # attack immediately
        entity.velocity_hint = Vector2.zero()

    def on_update(self, entity, dt: float) -> str | None:
        self._t += dt
        dist_sq = entity.body.position.distance_sq_to(entity.player_pos)
        if dist_sq > self.lose_attack_range_sq:
            return "Chase"
        if self._t >= self.cooldown:
            self._t = 0.0
            entity.attack_player(self.damage)

        # Face player
        to_px = entity.player_pos.x - entity.body.position.x
        to_py = entity.player_pos.y - entity.body.position.y
        to_sq = to_px * to_px + to_py * to_py
        if to_sq > 1e-6:
            inv_mag = 1.0 / (to_sq ** 0.5)
            entity.facing = Vector2(to_px * inv_mag, to_py * inv_mag)
        return None


class FleeState(State):
    name = "Flee"

    def __init__(self, speed: float = 6.0, safe_duration: float = 3.0,
                 safe_distance: float = 10.0) -> None:
        self.speed = speed
        self.safe_duration = safe_duration
        self.safe_distance_sq = safe_distance * safe_distance
        self._t = 0.0

    def on_enter(self, entity) -> None:
        self._t = 0.0

    def on_update(self, entity, dt: float) -> str | None:
        self._t += dt
        # Run away from player
        dx = entity.body.position.x - entity.player_pos.x
        dy = entity.body.position.y - entity.player_pos.y
        dist_sq = dx * dx + dy * dy

        if dist_sq < 1e-6:
            away = Vector2(1.0, 0.0)
        else:
            inv_dist = 1.0 / (dist_sq ** 0.5)
            away = Vector2(dx * inv_dist, dy * inv_dist)

        desired = away * self.speed
        entity.steer_towards(desired, dt)

        # Anti-thrashing hysteresis:
        # Only exit Flee if safe duration elapsed AND player is beyond safe distance OR HP recovered
        if self._t >= self.safe_duration:
            if entity.hp is not None and entity.hp < entity.max_hp * FLEE_HP_THRESHOLD:
                if dist_sq < self.safe_distance_sq:
                    # Player is still dangerously close; keep fleeing rather than thrashing to Idle/Chase!
                    self._t = self.safe_duration * 0.5
                    return None
            return "Idle"
        return None

