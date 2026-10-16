"""
Comprehensive Performance Benchmark Suite for Game Module
Measures baseline execution times and throughput before optimization.
"""
import time
import cProfile
import pstats
import io
import gc

from game_module.physics.vector2 import Vector2
from game_module.physics.aabb import AABB
from game_module.physics.rigidbody import Rigidbody, BodyType
from game_module.physics.world import PhysicsWorld
from game_module.ai.pathfinding import AStarPathfinder
from game_module.input.handler import InputHandler, Action
from game_module.entities.player import Player
from game_module.entities.enemy import Enemy


def benchmark_vector_math(iterations=200000):
    gc.collect()
    v1 = Vector2(3.5, 4.2)
    v2 = Vector2(-1.2, 8.9)
    
    start = time.perf_counter()
    for _ in range(iterations):
        v3 = v1 + v2
        d = v1.distance_to(v2)
        m = v3.magnitude()
        n = v3.normalized()
        c = v3.clamp_magnitude(5.0)
    elapsed = time.perf_counter() - start
    ops_per_sec = (iterations * 5) / elapsed
    return elapsed, ops_per_sec


def benchmark_aabb_checks(iterations=150000):
    gc.collect()
    box1 = AABB(Vector2(5.0, 5.0), Vector2(2.0, 2.0))
    box2 = AABB(Vector2(6.5, 5.5), Vector2(1.5, 1.5))
    pt = Vector2(5.5, 4.5)
    
    start = time.perf_counter()
    for _ in range(iterations):
        inter = box1.intersects(box2)
        mtv = box1.intersection_depth(box2)
        inside = box1.contains_point(pt)
    elapsed = time.perf_counter() - start
    checks_per_sec = (iterations * 3) / elapsed
    return elapsed, checks_per_sec


def benchmark_physics_world(steps=1000):
    gc.collect()
    world = PhysicsWorld(gravity=Vector2(0, 9.8), sub_steps=4)
    # Add ground
    world.add_body(Rigidbody(name="ground", body_type=BodyType.STATIC,
                             position=Vector2(50, 100), size=Vector2(100, 10)))
    # Add 40 dynamic bodies in a cluster
    for i in range(40):
        b = Rigidbody(name=f"body_{i}", body_type=BodyType.DYNAMIC,
                      position=Vector2(20 + (i % 8) * 5, 20 + (i // 8) * 8),
                      size=Vector2(2, 2), mass=1.0)
        world.add_body(b)
        
    start = time.perf_counter()
    dt = 1.0 / 60.0
    for _ in range(steps):
        world.step(dt)
    elapsed = time.perf_counter() - start
    steps_per_sec = steps / elapsed
    return elapsed, steps_per_sec


def benchmark_pathfinding(iterations=500):
    gc.collect()
    # 30x30 maze-like grid
    grid = [[0 for _ in range(30)] for _ in range(30)]
    for y in range(5, 25):
        grid[y][10] = 1
        grid[y][20] = 1
    grid[15][10] = 0  # gateway
    grid[15][20] = 0  # gateway
    
    pf = AStarPathfinder(grid, cell_size=1.0, allow_diagonal=True)
    start = Vector2(2.0, 2.0)
    goal = Vector2(28.0, 28.0)
    
    start_time = time.perf_counter()
    paths_found = 0
    waypoints_total = 0
    for _ in range(iterations):
        path = pf.find_path(start, goal)
        if path:
            sm = pf.smooth_path(path)
            paths_found += 1
            waypoints_total += len(sm)
    elapsed = time.perf_counter() - start_time
    queries_per_sec = iterations / elapsed
    return elapsed, queries_per_sec, paths_found


def benchmark_input_handler(iterations=100000):
    gc.collect()
    handler = InputHandler()
    keys = ["a", "d", "space", "shift", "w", "s"]
    
    start = time.perf_counter()
    dt = 0.016
    for i in range(iterations):
        k = keys[i % len(keys)]
        handler.feed(k, i % 2 == 0)
        handler.update(dt)
        _ = handler.is_action_pressed(Action.MOVE_RIGHT)
        _ = handler.is_action_just_pressed(Action.JUMP)
        _ = handler.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT)
    elapsed = time.perf_counter() - start
    updates_per_sec = iterations / elapsed
    return elapsed, updates_per_sec


def run_all_benchmarks():
    print("=================================================================")
    print("        RUNNING COMPREHENSIVE PERFORMANCE BENCHMARK              ")
    print("=================================================================")
    
    t_vec, ops_vec = benchmark_vector_math()
    print(f"1. Vector2 Math (200k iters x 5 ops):   {t_vec:.4f}s | {ops_vec:,.0f} ops/sec")
    
    t_aabb, ops_aabb = benchmark_aabb_checks()
    print(f"2. AABB Collision/MTV (150k checks):    {t_aabb:.4f}s | {ops_aabb:,.0f} checks/sec")
    
    t_phys, steps_phys = benchmark_physics_world(steps=1000)
    print(f"3. PhysicsWorld Simulation (1000 steps): {t_phys:.4f}s | {steps_phys:,.1f} steps/sec")
    
    t_pf, q_pf, count_pf = benchmark_pathfinding(iterations=500)
    print(f"4. A* + Line-of-Sight Smoothing (500q): {t_pf:.4f}s | {q_pf:,.1f} paths/sec")
    
    t_inp, up_inp = benchmark_input_handler(iterations=50000)
    print(f"5. InputHandler Updates (50k frames):   {t_inp:.4f}s | {up_inp:,.0f} updates/sec")
    
    total_time = t_vec + t_aabb + t_phys + t_pf + t_inp
    print("-----------------------------------------------------------------")
    print(f"TOTAL BENCHMARK TIME:                   {total_time:.4f}s")
    print("=================================================================")
    return {
        "vector_math": (t_vec, ops_vec),
        "aabb": (t_aabb, ops_aabb),
        "physics": (t_phys, steps_phys),
        "pathfinding": (t_pf, q_pf),
        "input": (t_inp, up_inp),
        "total_time": total_time
    }


if __name__ == "__main__":
    run_all_benchmarks()
