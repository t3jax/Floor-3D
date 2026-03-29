"""
Epsilon-based coordinate snapping so wall junctions align (orthogonality-friendly).
Default tolerance matches spec: 10px.
"""

from __future__ import annotations

import math
from collections.abc import Iterable


def _quantize(v: float, step: float) -> float:
    return round(v / step) * step


def snap_point(x: float, y: float, tolerance: float) -> tuple[float, float]:
    """Snap to a grid with cell size = tolerance (merges endpoints within ε)."""
    if tolerance <= 0:
        return (x, y)
    return (_quantize(x, tolerance), _quantize(y, tolerance))


def snap_segment(
    x1: float, y1: float, x2: float, y2: float, tolerance: float
) -> tuple[float, float, float, float]:
    sx1, sy1 = snap_point(x1, y1, tolerance)
    sx2, sy2 = snap_point(x2, y2, tolerance)
    return (sx1, sy1, sx2, sy2)


def merge_nearby_points(
    points: Iterable[tuple[float, float]], tolerance: float
) -> tuple[list[tuple[float, float]], dict[int, int]]:
    """
    Cluster points within tolerance; return canonical points and index remap.
    Uses greedy O(n^2) — fine for floor-plan scale (< few thousand points).
    """
    pts = list(points)
    if tolerance <= 0:
        canon = pts
        remap = {i: i for i in range(len(pts))}
        return canon, remap

    cell_size = max(tolerance, 1.0)
    grid = {}
    
    canonical: list[tuple[float, float]] = []
    remap: dict[int, int] = {}
    
    for i, p in enumerate(pts):
        x, y = p
        cx = int(x // cell_size)
        cy = int(y // cell_size)
        
        found_cluster_idx = -1
        # Check neighboring cells
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                cell = (cx + dx, cy + dy)
                if cell in grid:
                    for cid in grid[cell]:
                        qx, qy = canonical[cid]
                        if math.hypot(x - qx, y - qy) <= tolerance:
                            found_cluster_idx = cid
                            break
                if found_cluster_idx != -1:
                    break
                    
        if found_cluster_idx != -1:
            remap[i] = found_cluster_idx
        else:
            new_id = len(canonical)
            canonical.append((x, y))
            remap[i] = new_id
            cell = (cx, cy)
            if cell not in grid:
                grid[cell] = []
            grid[cell].append(new_id)

    # Final pass to snap point formatting
    final_canon = [snap_point(cx, cy, tolerance) for cx, cy in canonical]

    return final_canon, remap


def enforce_axis_alignment(
    x1: float, y1: float, x2: float, y2: float, tolerance: float
) -> tuple[float, float, float, float]:
    """
    If segment is nearly horizontal or vertical, snap to axis for orthogonality.
    """
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) < tolerance and abs(dy) >= tolerance:
        return (x1, y1, x1, y2)
    if abs(dy) < tolerance and abs(dx) >= tolerance:
        return (x1, y1, x2, y1)
    return (x1, y1, x2, y2)
