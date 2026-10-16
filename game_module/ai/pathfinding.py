"""
A* pathfinding on a 2D grid.

Grid convention:
- 0 = walkable, 1 = blocked
- grid[y][x]
- find_path returns list[Vector2] of world positions (cell centers)

Optimized for low-allocation priority queueing, flat integer keys,
precomputed octile math, and corner-cutting prevention in line-of-sight smoothing.
"""
from __future__ import annotations
import heapq
import math
from game_module.physics.vector2 import Vector2

SQRT2 = 1.4142135623730951
SQRT2_MINUS_ONE = 0.4142135623730951


class AStarPathfinder:
    def __init__(self, grid: list[list[int]], cell_size: float = 1.0,
                 allow_diagonal: bool = True) -> None:
        self.grid = grid
        self.cell_size = float(cell_size)
        self.inv_cell_size = 1.0 / self.cell_size if self.cell_size > 0 else 1.0
        self.allow_diagonal = allow_diagonal
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows > 0 else 0

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    def is_walkable(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows and self.grid[y][x] == 0

    def world_to_cell(self, pos: Vector2) -> tuple[int, int]:
        return (int(math.floor(pos.x * self.inv_cell_size)),
                int(math.floor(pos.y * self.inv_cell_size)))

    def cell_to_world(self, x: int, y: int) -> Vector2:
        return Vector2((x + 0.5) * self.cell_size, (y + 0.5) * self.cell_size)

    def neighbors(self, x: int, y: int):
        """Yield valid walkable neighbors with strict corner-cutting prevention."""
        # Orthogonal neighbors
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.cols and 0 <= ny < self.rows and self.grid[ny][nx] == 0:
                yield (nx, ny, 1.0)

        # Diagonal neighbors
        if self.allow_diagonal:
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.cols and 0 <= ny < self.rows and self.grid[ny][nx] == 0:
                    # Prevent diagonal corner cutting
                    if self.grid[y][x + dx] == 0 and self.grid[y + dy][x] == 0:
                        yield (nx, ny, SQRT2)

    def heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        """Octile distance heuristic with precomputed sqrt constants."""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        if self.allow_diagonal:
            if dx > dy:
                return dx + SQRT2_MINUS_ONE * dy
            return dy + SQRT2_MINUS_ONE * dx
        return dx + dy

    def find_path(self, start: Vector2, goal: Vector2) -> list[Vector2]:
        """
        Returns path as list of world positions from start cell to goal cell inclusive.
        Empty list if no path.
        """
        sx = int(math.floor(start.x * self.inv_cell_size))
        sy = int(math.floor(start.y * self.inv_cell_size))
        gx = int(math.floor(goal.x * self.inv_cell_size))
        gy = int(math.floor(goal.y * self.inv_cell_size))

        if not self.is_walkable(sx, sy) or not self.is_walkable(gx, gy):
            return []
        if sx == gx and sy == gy:
            return [self.cell_to_world(sx, sy)]

        cols = self.cols
        start_key = sy * cols + sx
        goal_key = gy * cols + gx

        # Priority queue stores: (f_score, counter, key, x, y)
        open_heap: list[tuple[float, int, int, int, int]] = []
        counter = 0

        # Octile heuristic directly from coordinates
        dx = abs(sx - gx)
        dy = abs(sy - gy)
        h0 = (dx + SQRT2_MINUS_ONE * dy) if dx > dy else (dy + SQRT2_MINUS_ONE * dx)

        heapq.heappush(open_heap, (h0, counter, start_key, sx, sy))
        came_from: dict[int, int | None] = {start_key: None}
        g_score: dict[int, float] = {start_key: 0.0}
        closed: set[int] = set()

        grid = self.grid
        allow_diag = self.allow_diagonal
        rows = self.rows

        while open_heap:
            _, _, cur_key, cx, cy = heapq.heappop(open_heap)
            if cur_key in closed:
                continue
            if cur_key == goal_key:
                break
            closed.add(cur_key)
            cur_g = g_score[cur_key]

            # Orthogonal neighbors
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == 0:
                    nb_key = ny * cols + nx
                    if nb_key in closed:
                        continue
                    tentative = cur_g + 1.0
                    if tentative < g_score.get(nb_key, float("inf")):
                        came_from[nb_key] = cur_key
                        g_score[nb_key] = tentative
                        h_dx = abs(nx - gx)
                        h_dy = abs(ny - gy)
                        h = (h_dx + SQRT2_MINUS_ONE * h_dy) if h_dx > h_dy else (h_dy + SQRT2_MINUS_ONE * h_dx)
                        counter += 1
                        heapq.heappush(open_heap, (tentative + h, counter, nb_key, nx, ny))

            # Diagonal neighbors
            if allow_diag:
                for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == 0:
                        # Prevent corner cutting
                        if grid[cy][cx + dx] == 0 and grid[cy + dy][cx] == 0:
                            nb_key = ny * cols + nx
                            if nb_key in closed:
                                continue
                            tentative = cur_g + SQRT2
                            if tentative < g_score.get(nb_key, float("inf")):
                                came_from[nb_key] = cur_key
                                g_score[nb_key] = tentative
                                h_dx = abs(nx - gx)
                                h_dy = abs(ny - gy)
                                h = (h_dx + SQRT2_MINUS_ONE * h_dy) if h_dx > h_dy else (h_dy + SQRT2_MINUS_ONE * h_dx)
                                counter += 1
                                heapq.heappush(open_heap, (tentative + h, counter, nb_key, nx, ny))

        if goal_key not in came_from:
            return []

        # Reconstruct path
        path_cells: list[tuple[int, int]] = []
        cur: int | None = goal_key
        while cur is not None:
            path_cells.append((cur % cols, cur // cols))
            cur = came_from[cur]
        path_cells.reverse()

        c_size = self.cell_size
        return [Vector2((x + 0.5) * c_size, (y + 0.5) * c_size) for x, y in path_cells]

    def smooth_path(self, path: list[Vector2]) -> list[Vector2]:
        """Line-of-sight path smoothing with greedy forward ray stepping."""
        if len(path) <= 2:
            return path[:]
        smoothed = [path[0]]
        i = 0
        n = len(path)
        while i < n - 1:
            farthest = i + 1
            for j in range(n - 1, i + 1, -1):
                if self._has_line_of_sight(path[i], path[j]):
                    farthest = j
                    break
            smoothed.append(path[farthest])
            i = farthest
        return smoothed

    def _has_line_of_sight(self, a: Vector2, b: Vector2) -> bool:
        """
        Bresenham line-of-sight test with strict corner-cutting validation.
        Prevents diagonal corridors from penetrating blocked corner walls.
        """
        x0 = int(math.floor(a.x * self.inv_cell_size))
        y0 = int(math.floor(a.y * self.inv_cell_size))
        x1 = int(math.floor(b.x * self.inv_cell_size))
        y1 = int(math.floor(b.y * self.inv_cell_size))

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0

        grid = self.grid
        rows, cols = self.rows, self.cols

        while True:
            if not (0 <= x < cols and 0 <= y < rows and grid[y][x] == 0):
                return False
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            step_x = 0
            step_y = 0
            if e2 > -dy:
                err -= dy
                step_x = sx
            if e2 < dx:
                err += dx
                step_y = sy

            # Corner cutting check on simultaneous diagonal step
            if step_x != 0 and step_y != 0:
                if not (0 <= x + step_x < cols and grid[y][x + step_x] == 0 and
                        0 <= y + step_y < rows and grid[y + step_y][x] == 0):
                    return False

            x += step_x
            y += step_y

        return True

