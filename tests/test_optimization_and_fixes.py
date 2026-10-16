"""
Unit tests validating bug fixes and performance optimizations in Week 3 refactoring.
Tests corner-cutting prevention, multi-key release consistency, anti-thrashing FSM,
and zero-division safety.
"""
import unittest
from game_module.physics.vector2 import Vector2
from game_module.physics.aabb import AABB
from game_module.physics.rigidbody import Rigidbody, BodyType
from game_module.physics.world import PhysicsWorld
from game_module.ai.pathfinding import AStarPathfinder
from game_module.ai.behaviours import FleeState, IdleState, ChaseState
from game_module.input.handler import InputHandler, Action
from game_module.entities.enemy import Enemy


class TestOptimizationAndFixes(unittest.TestCase):

    def test_corner_cutting_prevention(self):
        """
        Verify that Bresenham line-of-sight test strictly blocks corner cutting.
        Scenario:
            Wall at (1, 0) and (0, 1). Free cells at (0, 0) and (1, 1).
            Moving diagonally from (0, 0) to (1, 1) must be BLOCKED because
            orthogonal corners are solid walls.
        """
        grid = [
            [0, 1],  # row 0: (0,0)=0, (1,0)=1 (wall)
            [1, 0]   # row 1: (0,1)=1 (wall), (1,1)=0
        ]
        pf = AStarPathfinder(grid, cell_size=1.0, allow_diagonal=True)
        start = Vector2(0.5, 0.5)  # cell (0, 0)
        goal = Vector2(1.5, 1.5)   # cell (1, 1)

        has_los = pf._has_line_of_sight(start, goal)
        self.assertFalse(has_los, "Line of sight must NOT cut through diagonally blocked wall corners!")

    def test_multikey_release_consistency(self):
        """
        Verify multi-key aggregate release tracking.
        If Action.MOVE_UP is bound to ['w', 'up'], holding 'w' and releasing 'up'
        must NOT trigger is_action_just_released(MOVE_UP), because 'w' is still held.
        """
        handler = InputHandler()
        handler.bind(Action.MOVE_UP, ["w", "up"])

        # Press 'w'
        handler.feed("w", True)
        handler.update(0.016)
        self.assertTrue(handler.is_action_pressed(Action.MOVE_UP))
        self.assertTrue(handler.is_action_just_pressed(Action.MOVE_UP))

        # Now press 'up' as well (both held)
        handler.feed("up", True)
        handler.update(0.016)
        self.assertTrue(handler.is_action_pressed(Action.MOVE_UP))
        self.assertFalse(handler.is_action_just_pressed(Action.MOVE_UP))

        # Release 'up' while 'w' remains held
        handler.feed("up", False)
        handler.update(0.016)
        self.assertTrue(handler.is_action_pressed(Action.MOVE_UP), "Action must remain pressed while 'w' is held")
        self.assertFalse(handler.is_action_just_released(Action.MOVE_UP),
                         "Action must NOT report just_released while another bound key is held!")

        # Finally release 'w'
        handler.feed("w", False)
        handler.update(0.016)
        self.assertFalse(handler.is_action_pressed(Action.MOVE_UP))
        self.assertTrue(handler.is_action_just_released(Action.MOVE_UP),
                        "Action must report just_released when the final bound key is released")

    def test_vector2_inplace_and_zero_division(self):
        """Verify Vector2 in-place arithmetic and safe division."""
        v = Vector2(3.0, 4.0)
        v += Vector2(1.0, -1.0)
        self.assertAlmostEqual(v.x, 4.0)
        self.assertAlmostEqual(v.y, 3.0)

        v *= 2.0
        self.assertAlmostEqual(v.x, 8.0)
        self.assertAlmostEqual(v.y, 6.0)

        # Zero division guard
        v_zero = v / 0.0
        self.assertEqual(v_zero.x, 0.0)
        self.assertEqual(v_zero.y, 0.0)

        # Distance squared
        dist_sq = Vector2(0, 0).distance_sq_to(Vector2(3, 4))
        self.assertAlmostEqual(dist_sq, 25.0)

    def test_aabb_scalar_accessors(self):
        """Verify AABB scalar bounds property without heap allocation."""
        box = AABB(Vector2(10.0, 20.0), Vector2(5.0, 8.0))
        self.assertAlmostEqual(box.min_x, 5.0)
        self.assertAlmostEqual(box.max_x, 15.0)
        self.assertAlmostEqual(box.min_y, 12.0)
        self.assertAlmostEqual(box.max_y, 28.0)
        self.assertTrue(box.contains_point(Vector2(10.0, 20.0)))
        self.assertFalse(box.contains_point(Vector2(4.0, 20.0)))

    def test_flee_state_anti_thrashing(self):
        """
        Verify that an entity in FleeState does not oscillate back to Idle
        if HP is still critically low and the player is within dangerous range.
        """
        flee = FleeState(speed=6.0, safe_duration=1.0, safe_distance=10.0)

        # Mock entity
        class MockEntity:
            def __init__(self):
                self.hp = 10.0
                self.max_hp = 100.0
                self.body = Rigidbody(position=Vector2(5.0, 5.0))
                self.player_pos = Vector2(6.0, 5.0)  # Only 1.0 unit away!
            def steer_towards(self, des, dt):
                pass

        entity = MockEntity()
        flee.on_enter(entity)

        # Simulate 1.5 seconds (past safe_duration of 1.0s)
        nxt = flee.on_update(entity, 1.5)
        # Should stay in Flee (return None) because player is dangerously close (dist 1.0 < 10.0)
        self.assertIsNone(nxt, "Flee state must suppress thrashing when player is still dangerously close")


if __name__ == "__main__":
    unittest.main()
