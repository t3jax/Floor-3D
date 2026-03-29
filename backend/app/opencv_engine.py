"""
Floor plan parsing: Canny, HoughLinesP, contour detection, snapping.
Improved with merge_similar_lines() and snap_endpoints_to_corners().
Enhanced staircase detection with pattern recognition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from app.config import settings
from app.snapping import enforce_axis_alignment, snap_segment


@dataclass
class StaircaseInfo:
    """Staircase detection result."""
    detected: bool = False
    staircase_type: str = "unknown"  # straight, l_shaped, spiral
    bounding_box: dict = field(default_factory=lambda: {"x": 0, "y": 0, "width": 0, "height": 0})
    center: tuple[float, float] = (0, 0)
    direction: str = "unknown"  # up, down
    num_steps: int = 17


@dataclass
class DetectionResult:
    lines_hough: list[tuple[float, float, float, float]]
    snapped_segments: list[tuple[float, float, float, float]]
    binary_vis: np.ndarray
    edges_vis: np.ndarray
    contours: list[np.ndarray]
    image_shape: tuple[int, int]
    has_second_floor: bool = False
    void_coordinates: tuple[float, float] | None = None
    staircase: StaircaseInfo | None = None


def _preprocess(gray: np.ndarray) -> np.ndarray:
    """
    Clean preprocessing for floor plan images.
    Steps: adaptive threshold -> morphological close to remove noise.
    """
    # Adaptive threshold for varying lighting - THRESH_BINARY_INV for black walls on white
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=11,
        C=2
    )
    
    # Morphological close to remove noise dots
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    return binary


def _get_line_angle(x1: float, y1: float, x2: float, y2: float) -> float:
    """Get angle of line in degrees (0-180 range)."""
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    # Normalize to 0-180 range
    if angle < 0:
        angle += 180
    return angle


def _get_midpoint(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    """Get midpoint of a line segment."""
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def merge_similar_lines(
    lines: list[tuple[float, float, float, float]],
    midpoint_tolerance: float = 15.0,
    angle_tolerance: float = 5.0
) -> list[tuple[float, float, float, float]]:
    """
    Merge lines with similar midpoints and angles.
    Groups lines whose midpoints are within midpoint_tolerance AND
    whose angles differ by less than angle_tolerance degrees.
    Replaces each group with a single averaged line.
    """
    if len(lines) < 2:
        return lines
    
    # Track which lines have been merged
    merged = [False] * len(lines)
    result = []
    
    for i, (x1, y1, x2, y2) in enumerate(lines):
        if merged[i]:
            continue
            
        # Start a new group with this line
        group = [(x1, y1, x2, y2)]
        merged[i] = True
        
        mid_i = _get_midpoint(x1, y1, x2, y2)
        angle_i = _get_line_angle(x1, y1, x2, y2)
        
        # Find similar lines to merge
        for j in range(i + 1, len(lines)):
            if merged[j]:
                continue
                
            jx1, jy1, jx2, jy2 = lines[j]
            mid_j = _get_midpoint(jx1, jy1, jx2, jy2)
            angle_j = _get_line_angle(jx1, jy1, jx2, jy2)
            
            # Check midpoint distance
            mid_dist = math.hypot(mid_i[0] - mid_j[0], mid_i[1] - mid_j[1])
            
            # Check angle difference (handle wraparound at 180)
            angle_diff = abs(angle_i - angle_j)
            if angle_diff > 90:
                angle_diff = 180 - angle_diff
            
            if mid_dist < midpoint_tolerance and angle_diff < angle_tolerance:
                group.append((jx1, jy1, jx2, jy2))
                merged[j] = True
        
        # Average the group into a single line
        if len(group) == 1:
            result.append(group[0])
        else:
            # Use endpoints that give the longest segment
            all_points = []
            for gx1, gy1, gx2, gy2 in group:
                all_points.append((gx1, gy1))
                all_points.append((gx2, gy2))
            
            # Find the two points that are farthest apart
            max_dist = 0
            best_p1, best_p2 = all_points[0], all_points[1]
            
            for pi in range(len(all_points)):
                for pj in range(pi + 1, len(all_points)):
                    d = math.hypot(all_points[pi][0] - all_points[pj][0],
                                   all_points[pi][1] - all_points[pj][1])
                    if d > max_dist:
                        max_dist = d
                        best_p1, best_p2 = all_points[pi], all_points[pj]
            
            result.append((best_p1[0], best_p1[1], best_p2[0], best_p2[1]))
    
    return result


def snap_endpoints_to_corners(
    lines: list[tuple[float, float, float, float]],
    radius: float = 20.0
) -> list[tuple[float, float, float, float]]:
    """
    Snap line endpoints to canonical corner points.
    1. Collect all endpoints
    2. Cluster points within radius
    3. Replace each cluster with averaged point
    4. Remap all endpoints to nearest canonical corner
    5. Drop zero-length lines
    """
    if len(lines) == 0:
        return lines
    
    # Collect all endpoints
    endpoints = []
    for x1, y1, x2, y2 in lines:
        endpoints.append((x1, y1))
        endpoints.append((x2, y2))
    
    # Cluster points within radius using simple greedy clustering
    canonical_points = []
    point_to_canonical = {}
    
    for pt in endpoints:
        pt_key = pt
        found_cluster = None
        
        for i, (cx, cy) in enumerate(canonical_points):
            if math.hypot(pt[0] - cx, pt[1] - cy) < radius:
                found_cluster = i
                break
        
        if found_cluster is not None:
            # Update canonical point to average
            old_cx, old_cy = canonical_points[found_cluster]
            # Count how many points are in this cluster
            count = sum(1 for v in point_to_canonical.values() if v == found_cluster)
            new_cx = (old_cx * count + pt[0]) / (count + 1)
            new_cy = (old_cy * count + pt[1]) / (count + 1)
            canonical_points[found_cluster] = (new_cx, new_cy)
            point_to_canonical[pt_key] = found_cluster
        else:
            # Create new cluster
            canonical_points.append(pt)
            point_to_canonical[pt_key] = len(canonical_points) - 1
    
    # Remap all line endpoints to canonical points
    result = []
    for x1, y1, x2, y2 in lines:
        # Find nearest canonical point for each endpoint
        min_dist1, idx1 = float('inf'), 0
        min_dist2, idx2 = float('inf'), 0
        
        for i, (cx, cy) in enumerate(canonical_points):
            d1 = math.hypot(x1 - cx, y1 - cy)
            d2 = math.hypot(x2 - cx, y2 - cy)
            
            if d1 < min_dist1:
                min_dist1, idx1 = d1, i
            if d2 < min_dist2:
                min_dist2, idx2 = d2, i
        
        new_x1, new_y1 = canonical_points[idx1]
        new_x2, new_y2 = canonical_points[idx2]
        
        # Drop zero-length lines
        if abs(new_x1 - new_x2) < 0.5 and abs(new_y1 - new_y2) < 0.5:
            continue
        
        result.append((new_x1, new_y1, new_x2, new_y2))
    
    return result


def _is_axis_aligned(x1: float, y1: float, x2: float, y2: float, tolerance: float = 0.15) -> bool:
    """Check if a line segment is roughly horizontal or vertical."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    length = math.hypot(dx, dy)
    
    if length < 1:
        return False
    
    # Check if mostly horizontal or mostly vertical
    return (dy / length < tolerance) or (dx / length < tolerance)


def _remove_duplicates(
    segments: list[tuple[float, float, float, float]], 
    tolerance: float = 15.0
) -> list[tuple[float, float, float, float]]:
    """Remove duplicate or very similar segments."""
    if len(segments) < 2:
        return segments
    
    filtered = []
    for seg in segments:
        x1, y1, x2, y2 = seg
        is_dup = False
        
        for ex1, ey1, ex2, ey2 in filtered:
            # Check if endpoints match (in either direction)
            dist1 = math.hypot(x1 - ex1, y1 - ey1) + math.hypot(x2 - ex2, y2 - ey2)
            dist2 = math.hypot(x1 - ex2, y1 - ey2) + math.hypot(x2 - ex1, y2 - ey1)
            
            if min(dist1, dist2) < tolerance * 2:
                is_dup = True
                break
        
        if not is_dup:
            filtered.append(seg)
    
    return filtered


def detect_walls_opencv(
    image_bgr: np.ndarray,
    tolerance_px: float | None = None,
) -> DetectionResult:
    tol = tolerance_px if tolerance_px is not None else settings.snap_tolerance_px
    h, w = image_bgr.shape[:2]
    
    # Step 1: Convert to grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    
    # Step 2: Preprocess with adaptive threshold + morphological close
    binary = _preprocess(gray)

    # Step 3: Canny edge detection  
    edges = cv2.Canny(binary, 50, 150, apertureSize=3)

    # Step 4: HoughLinesP with specified parameters
    lines_hough: list[tuple[float, float, float, float]] = []
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,        # As specified
        minLineLength=100,    # As specified
        maxLineGap=30,        # As specified
    )
    
    if lines is not None:
        for ln in lines:
            x1, y1, x2, y2 = ln[0]
            lines_hough.append((float(x1), float(y1), float(x2), float(y2)))

    # Step 5: Merge similar lines (midpoints within 15px, angles within 5 degrees)
    lines_hough = merge_similar_lines(lines_hough, midpoint_tolerance=15.0, angle_tolerance=5.0)

    # Step 6: Snap endpoints to corners (cluster within 20px radius)
    lines_hough = snap_endpoints_to_corners(lines_hough, radius=20.0)

    # Find contours for fallback
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Apply axis alignment and snapping for clean segments
    snapped: list[tuple[float, float, float, float]] = []
    for x1, y1, x2, y2 in lines_hough:
        # Only keep axis-aligned lines (horizontal/vertical)
        if not _is_axis_aligned(x1, y1, x2, y2, settings.axis_alignment_tolerance):
            continue
            
        ax1, ay1, ax2, ay2 = enforce_axis_alignment(x1, y1, x2, y2, tol)
        sx1, sy1, sx2, sy2 = snap_segment(ax1, ay1, ax2, ay2, tol)
        
        seg_length = math.hypot(sx2 - sx1, sy2 - sy1)
        if seg_length >= settings.min_wall_length_px:
            snapped.append((sx1, sy1, sx2, sy2))

    # Fallback to contours if no lines found
    if not snapped and contours:
        for c in contours[:30]:
            eps = 0.015 * cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, eps, True)
            n = len(approx)
            
            for i in range(n):
                p0 = approx[i][0]
                p1 = approx[(i + 1) % n][0]
                x1, y1 = float(p0[0]), float(p0[1])
                x2, y2 = float(p1[0]), float(p1[1])
                
                if not _is_axis_aligned(x1, y1, x2, y2, 0.2):
                    continue
                    
                ax1, ay1, ax2, ay2 = enforce_axis_alignment(x1, y1, x2, y2, tol)
                sx1, sy1, sx2, sy2 = snap_segment(ax1, ay1, ax2, ay2, tol)
                
                if math.hypot(sx2 - sx1, sy2 - sy1) >= settings.min_wall_length_px:
                    snapped.append((sx1, sy1, sx2, sy2))

    # Remove duplicates
    snapped = _remove_duplicates(snapped, tol)
    
    # Final snap endpoints to corners again for clean output
    snapped = snap_endpoints_to_corners(snapped, radius=20.0)
    
    # Enhanced staircase detection
    staircase_info = detect_staircase_pattern(binary, gray, lines, h, w)
    has_second_floor = staircase_info.detected
    void_coordinates = staircase_info.center if staircase_info.detected else None

    return DetectionResult(
        lines_hough=lines_hough,
        snapped_segments=snapped,
        binary_vis=binary,
        edges_vis=edges,
        contours=contours,
        image_shape=(h, w),
        has_second_floor=has_second_floor,
        void_coordinates=void_coordinates,
        staircase=staircase_info if staircase_info.detected else None
    )


def detect_staircase_pattern(
    binary: np.ndarray, 
    gray: np.ndarray, 
    lines: np.ndarray | None,
    h: int, 
    w: int
) -> StaircaseInfo:
    """
    Detect staircase patterns in floor plans.
    Looks for:
    1. Parallel lines pattern (stair treads)
    2. X pattern (crossing diagonals indicating stairs)
    3. L-shaped or spiral patterns
    """
    staircase = StaircaseInfo()
    
    if lines is None:
        return staircase
    
    # Collect all lines for analysis
    all_lines = []
    diagonal_lines = []
    horizontal_lines = []
    vertical_lines = []
    
    for ln in lines:
        x1, y1, x2, y2 = ln[0]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        
        if length < 20:
            continue
        
        angle = math.degrees(math.atan2(dy, dx)) % 180
        all_lines.append((x1, y1, x2, y2, angle, length))
        
        # Classify by angle
        if 80 < angle < 100:  # Vertical
            vertical_lines.append((x1, y1, x2, y2))
        elif angle < 10 or angle > 170:  # Horizontal
            horizontal_lines.append((x1, y1, x2, y2))
        elif 20 < angle < 70 or 110 < angle < 160:  # Diagonal
            diagonal_lines.append((x1, y1, x2, y2))
    
    # Pattern 1: Look for parallel lines (stair treads)
    parallel_groups = find_parallel_line_groups(horizontal_lines, tolerance=15)
    
    for group in parallel_groups:
        if len(group) >= 5:  # At least 5 parallel lines = potential staircase
            # Calculate bounding box of the parallel lines
            all_x = []
            all_y = []
            for x1, y1, x2, y2 in group:
                all_x.extend([x1, x2])
                all_y.extend([y1, y2])
            
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            width = max_x - min_x
            height = max_y - min_y
            
            # Staircase should be roughly rectangular
            if width > 30 and height > 50:
                staircase.detected = True
                staircase.staircase_type = "straight"
                staircase.bounding_box = {
                    "x": min_x, "y": min_y, "width": width, "height": height
                }
                staircase.center = ((min_x + max_x) / 2, (min_y + max_y) / 2)
                staircase.direction = "up"
                staircase.num_steps = len(group)
                return staircase
    
    # Pattern 2: X pattern (intersecting diagonals)
    for i, (x1, y1, x2, y2) in enumerate(diagonal_lines):
        for x3, y3, x4, y4 in diagonal_lines[i+1:]:
            # Check if they intersect
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1:
                continue
                
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
            
            if 0.1 < t < 0.9 and 0.1 < u < 0.9:
                ix = x1 + t * (x2 - x1)
                iy = y1 + t * (y2 - y1)
                
                # Found X pattern
                staircase.detected = True
                staircase.staircase_type = "straight"
                staircase.bounding_box = {
                    "x": ix - 100, "y": iy - 150, "width": 200, "height": 300
                }
                staircase.center = (ix, iy)
                staircase.direction = "up"
                return staircase
    
    # Pattern 3: L-shaped pattern (two perpendicular groups of parallel lines)
    vertical_groups = find_parallel_line_groups(vertical_lines, tolerance=15)
    
    for h_group in parallel_groups:
        for v_group in vertical_groups:
            if len(h_group) >= 3 and len(v_group) >= 3:
                # Check if they share a corner area
                h_box = get_line_group_bounds(h_group)
                v_box = get_line_group_bounds(v_group)
                
                # Check for overlap/adjacency
                if boxes_adjacent(h_box, v_box, tolerance=50):
                    combined_box = merge_boxes(h_box, v_box)
                    staircase.detected = True
                    staircase.staircase_type = "l_shaped"
                    staircase.bounding_box = combined_box
                    staircase.center = (
                        combined_box["x"] + combined_box["width"] / 2,
                        combined_box["y"] + combined_box["height"] / 2
                    )
                    staircase.direction = "up"
                    staircase.num_steps = len(h_group) + len(v_group)
                    return staircase
    
    return staircase


def find_parallel_line_groups(
    lines: list[tuple], 
    tolerance: float = 15.0
) -> list[list[tuple]]:
    """Group lines that are roughly parallel and evenly spaced."""
    if len(lines) < 3:
        return []
    
    groups = []
    used = [False] * len(lines)
    
    for i, (x1, y1, x2, y2) in enumerate(lines):
        if used[i]:
            continue
        
        group = [(x1, y1, x2, y2)]
        used[i] = True
        
        # Find other lines parallel to this one
        for j in range(i + 1, len(lines)):
            if used[j]:
                continue
            
            jx1, jy1, jx2, jy2 = lines[j]
            
            # Check if lines are parallel (similar angle)
            angle1 = math.atan2(y2 - y1, x2 - x1)
            angle2 = math.atan2(jy2 - jy1, jx2 - jx1)
            angle_diff = abs(angle1 - angle2)
            
            if angle_diff < 0.1 or abs(angle_diff - math.pi) < 0.1:  # ~6 degrees
                # Check if they're close enough (within staircase width)
                mid1 = ((x1 + x2) / 2, (y1 + y2) / 2)
                mid2 = ((jx1 + jx2) / 2, (jy1 + jy2) / 2)
                dist = math.hypot(mid1[0] - mid2[0], mid1[1] - mid2[1])
                
                if dist < 300:  # Max staircase width
                    group.append((jx1, jy1, jx2, jy2))
                    used[j] = True
        
        if len(group) >= 3:
            groups.append(group)
    
    return groups


def get_line_group_bounds(lines: list[tuple]) -> dict:
    """Get bounding box of a group of lines."""
    all_x = []
    all_y = []
    for x1, y1, x2, y2 in lines:
        all_x.extend([x1, x2])
        all_y.extend([y1, y2])
    
    return {
        "x": min(all_x),
        "y": min(all_y),
        "width": max(all_x) - min(all_x),
        "height": max(all_y) - min(all_y)
    }


def boxes_adjacent(box1: dict, box2: dict, tolerance: float = 50) -> bool:
    """Check if two bounding boxes are adjacent or overlapping."""
    # Expand boxes by tolerance
    b1_left = box1["x"] - tolerance
    b1_right = box1["x"] + box1["width"] + tolerance
    b1_top = box1["y"] - tolerance
    b1_bottom = box1["y"] + box1["height"] + tolerance
    
    b2_left = box2["x"]
    b2_right = box2["x"] + box2["width"]
    b2_top = box2["y"]
    b2_bottom = box2["y"] + box2["height"]
    
    # Check for overlap
    return not (b1_right < b2_left or b2_right < b1_left or 
                b1_bottom < b2_top or b2_bottom < b1_top)


def merge_boxes(box1: dict, box2: dict) -> dict:
    """Merge two bounding boxes into one."""
    min_x = min(box1["x"], box2["x"])
    min_y = min(box1["y"], box2["y"])
    max_x = max(box1["x"] + box1["width"], box2["x"] + box2["width"])
    max_y = max(box1["y"] + box1["height"], box2["y"] + box2["height"])
    
    return {
        "x": min_x,
        "y": min_y,
        "width": max_x - min_x,
        "height": max_y - min_y
    }


def has_meaningful_geometry(snapped_count: int, contour_count: int) -> bool:
    return snapped_count >= 3 or contour_count >= 2
