"""
Coordinate-Based Reconstruction Engine for Floor3D.
Implements vertex-edge graph approach:
- Skeletonization to 1-pixel center-lines
- Vertex extraction at junctions
- Orthogonal snapping to 90° grid
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import cv2
import numpy as np

try:
    from skimage.morphology import skeletonize
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False


@dataclass
class Vertex:
    """A vertex (junction point) in the wall graph."""
    id: int
    x: float
    y: float
    junction_type: Literal["L", "T", "X", "endpoint"] = "endpoint"
    degree: int = 0  # Number of connected edges


@dataclass 
class Edge:
    """An edge (wall segment) between two vertices."""
    id: int
    start_vertex: int
    end_vertex: int
    length_px: float
    angle_deg: float  # 0 = horizontal, 90 = vertical
    is_orthogonal: bool = True
    thickness_category: Literal["major", "minor"] = "minor"


@dataclass
class GraphReconstruction:
    """Result of coordinate-based reconstruction."""
    vertices: list[Vertex] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    skeleton_image: np.ndarray | None = None
    orthogonal_segments: list[tuple[float, float, float, float]] = field(default_factory=list)


def skeletonize_walls(binary_mask: np.ndarray) -> np.ndarray:
    """
    Reduce wall masks to 1-pixel wide center-lines.
    Uses morphological skeletonization.
    """
    # Ensure binary format (0 or 1)
    binary = (binary_mask > 0).astype(np.uint8)
    
    if SKIMAGE_AVAILABLE:
        # Use skimage for better skeletonization
        skeleton = skeletonize(binary).astype(np.uint8) * 255
    else:
        # Fallback: morphological thinning
        skeleton = _morphological_skeleton(binary)
    
    return skeleton


def _morphological_skeleton(binary: np.ndarray) -> np.ndarray:
    """Fallback skeletonization using morphological operations."""
    skeleton = np.zeros_like(binary)
    img = binary.copy()
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    
    done = False
    while not done:
        eroded = cv2.erode(img, kernel)
        temp = cv2.dilate(eroded, kernel)
        temp = cv2.subtract(img, temp)
        skeleton = cv2.bitwise_or(skeleton, temp)
        img = eroded.copy()
        
        if cv2.countNonZero(img) == 0:
            done = True
    
    return skeleton * 255


def extract_vertices(
    skeleton: np.ndarray,
    tolerance_px: float = 5.0
) -> list[Vertex]:
    """
    Extract junction vertices from skeletonized image.
    Identifies L, T, X junctions and endpoints.
    """
    h, w = skeleton.shape
    vertices = []
    vertex_id = 0
    
    # Find all skeleton points
    points = np.column_stack(np.where(skeleton > 0))
    
    if len(points) == 0:
        return vertices
    
    # Analyze each point's neighborhood to determine junction type
    junction_points = []
    endpoint_points = []
    
    for y, x in points:
        # Count neighbors in 8-connected neighborhood
        neighbors = 0
        neighbor_dirs = []
        
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    if skeleton[ny, nx] > 0:
                        neighbors += 1
                        neighbor_dirs.append((dx, dy))
        
        # Classify junction type
        if neighbors == 1:
            endpoint_points.append((x, y, "endpoint"))
        elif neighbors >= 3:
            # Analyze branch directions to determine junction type
            junction_type = _classify_junction(neighbor_dirs)
            junction_points.append((x, y, junction_type, neighbors))
    
    # Cluster nearby junction points
    junction_clusters = _cluster_points(
        [(x, y) for x, y, *_ in junction_points],
        tolerance_px
    )
    
    # Create vertices from clusters
    for cluster in junction_clusters:
        cx = sum(p[0] for p in cluster) / len(cluster)
        cy = sum(p[1] for p in cluster) / len(cluster)
        
        # Find the junction type with highest degree in cluster
        best_type = "L"
        max_degree = 0
        for x, y, jtype, degree in junction_points:
            if any(abs(x - px) < tolerance_px and abs(y - py) < tolerance_px for px, py in cluster):
                if degree > max_degree:
                    max_degree = degree
                    best_type = jtype
        
        vertices.append(Vertex(
            id=vertex_id,
            x=cx,
            y=cy,
            junction_type=best_type,
            degree=max_degree
        ))
        vertex_id += 1
    
    # Cluster endpoint points
    endpoint_clusters = _cluster_points(
        [(x, y) for x, y, _ in endpoint_points],
        tolerance_px
    )
    
    for cluster in endpoint_clusters:
        cx = sum(p[0] for p in cluster) / len(cluster)
        cy = sum(p[1] for p in cluster) / len(cluster)
        
        vertices.append(Vertex(
            id=vertex_id,
            x=cx,
            y=cy,
            junction_type="endpoint",
            degree=1
        ))
        vertex_id += 1
    
    return vertices


def _classify_junction(neighbor_dirs: list[tuple[int, int]]) -> Literal["L", "T", "X"]:
    """Classify junction type based on neighbor directions."""
    num_dirs = len(neighbor_dirs)
    
    if num_dirs >= 4:
        return "X"
    elif num_dirs == 3:
        return "T"
    else:
        return "L"


def _cluster_points(
    points: list[tuple[float, float]],
    tolerance: float
) -> list[list[tuple[float, float]]]:
    """Cluster nearby points within tolerance."""
    if not points:
        return []
    
    clusters: list[list[tuple[float, float]]] = []
    used = [False] * len(points)
    
    for i, (x1, y1) in enumerate(points):
        if used[i]:
            continue
        
        cluster = [(x1, y1)]
        used[i] = True
        
        for j, (x2, y2) in enumerate(points):
            if used[j]:
                continue
            
            if math.hypot(x2 - x1, y2 - y1) < tolerance:
                cluster.append((x2, y2))
                used[j] = True
        
        clusters.append(cluster)
    
    return clusters


def extract_edges_from_segments(
    segments: list[tuple[float, float, float, float]],
    vertices: list[Vertex],
    tolerance_px: float = 10.0
) -> list[Edge]:
    """
    Create edges by matching segment endpoints to vertices.
    """
    edges = []
    edge_id = 0
    
    for x1, y1, x2, y2 in segments:
        # Find nearest vertex to each endpoint
        start_v = _find_nearest_vertex(x1, y1, vertices, tolerance_px)
        end_v = _find_nearest_vertex(x2, y2, vertices, tolerance_px)
        
        if start_v is None or end_v is None or start_v == end_v:
            continue
        
        length = math.hypot(x2 - x1, y2 - y1)
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        
        # Normalize angle to 0-180
        if angle < 0:
            angle += 180
        
        # Check if orthogonal (within 5° of 0°, 90°, or 180°)
        is_orth = (angle < 5 or angle > 175 or 85 < angle < 95)
        
        edges.append(Edge(
            id=edge_id,
            start_vertex=start_v.id,
            end_vertex=end_v.id,
            length_px=length,
            angle_deg=angle,
            is_orthogonal=is_orth
        ))
        edge_id += 1
    
    return edges


def _find_nearest_vertex(
    x: float,
    y: float,
    vertices: list[Vertex],
    tolerance: float
) -> Vertex | None:
    """Find the nearest vertex to a point."""
    best_vertex = None
    best_dist = tolerance
    
    for v in vertices:
        dist = math.hypot(x - v.x, y - v.y)
        if dist < best_dist:
            best_dist = dist
            best_vertex = v
    
    return best_vertex


def snap_to_orthogonal_grid(
    segments: list[tuple[float, float, float, float]],
    angle_tolerance_deg: float = 5.0
) -> list[tuple[float, float, float, float]]:
    """
    Snap all lines within tolerance to perfect 90° grid.
    Lines close to horizontal become perfectly horizontal.
    Lines close to vertical become perfectly vertical.
    """
    snapped = []
    
    for x1, y1, x2, y2 in segments:
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        
        # Normalize to -180 to 180
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        
        # Check if close to horizontal (0° or 180°)
        if abs(angle) < angle_tolerance_deg or abs(abs(angle) - 180) < angle_tolerance_deg:
            # Make perfectly horizontal - average Y
            avg_y = (y1 + y2) / 2
            snapped.append((x1, avg_y, x2, avg_y))
        
        # Check if close to vertical (90° or -90°)
        elif abs(abs(angle) - 90) < angle_tolerance_deg:
            # Make perfectly vertical - average X
            avg_x = (x1 + x2) / 2
            snapped.append((avg_x, y1, avg_x, y2))
        
        else:
            # Keep non-orthogonal lines as-is (for diagonal walls)
            snapped.append((x1, y1, x2, y2))
    
    return snapped


def snap_vertices_to_grid(
    vertices: list[Vertex],
    grid_size_px: float = 5.0
) -> list[Vertex]:
    """
    Snap vertices to a regular grid for cleaner geometry.
    """
    snapped = []
    for v in vertices:
        snapped_x = round(v.x / grid_size_px) * grid_size_px
        snapped_y = round(v.y / grid_size_px) * grid_size_px
        
        snapped.append(Vertex(
            id=v.id,
            x=snapped_x,
            y=snapped_y,
            junction_type=v.junction_type,
            degree=v.degree
        ))
    
    return snapped


def reconstruct_wall_graph(
    binary_mask: np.ndarray,
    detected_segments: list[tuple[float, float, float, float]],
    use_skeleton: bool = True,
    tolerance_px: float = 10.0
) -> GraphReconstruction:
    """
    Full coordinate-based reconstruction pipeline.
    
    1. Skeletonize wall masks
    2. Extract vertices at junctions
    3. Create edges between vertices
    4. Snap to orthogonal grid
    """
    # Step 1: Skeletonize
    skeleton = None
    if use_skeleton and binary_mask is not None:
        skeleton = skeletonize_walls(binary_mask)
    
    # Step 2: Snap segments to orthogonal grid
    ortho_segments = snap_to_orthogonal_grid(detected_segments, angle_tolerance_deg=5.0)
    
    # Step 3: Extract vertices from skeleton or segment endpoints
    if skeleton is not None:
        vertices = extract_vertices(skeleton, tolerance_px)
    else:
        # Extract vertices from segment endpoints
        vertices = _vertices_from_segments(ortho_segments, tolerance_px)
    
    # Step 4: Snap vertices to grid
    vertices = snap_vertices_to_grid(vertices, grid_size_px=5.0)
    
    # Step 5: Create edges
    edges = extract_edges_from_segments(ortho_segments, vertices, tolerance_px)
    
    return GraphReconstruction(
        vertices=vertices,
        edges=edges,
        skeleton_image=skeleton,
        orthogonal_segments=ortho_segments
    )


def _vertices_from_segments(
    segments: list[tuple[float, float, float, float]],
    tolerance_px: float
) -> list[Vertex]:
    """Extract vertices from segment endpoints."""
    # Collect all endpoints
    points: list[tuple[float, float]] = []
    for x1, y1, x2, y2 in segments:
        points.append((x1, y1))
        points.append((x2, y2))
    
    # Cluster nearby points
    clusters = _cluster_points(points, tolerance_px)
    
    # Create vertices
    vertices = []
    for i, cluster in enumerate(clusters):
        cx = sum(p[0] for p in cluster) / len(cluster)
        cy = sum(p[1] for p in cluster) / len(cluster)
        
        # Estimate degree based on cluster size
        degree = len(cluster)
        
        # Classify junction type
        if degree >= 4:
            jtype = "X"
        elif degree == 3:
            jtype = "T"
        elif degree == 2:
            jtype = "L"
        else:
            jtype = "endpoint"
        
        vertices.append(Vertex(
            id=i,
            x=cx,
            y=cy,
            junction_type=jtype,
            degree=degree
        ))
    
    return vertices


def segments_to_vertex_edges(
    ortho_segments: list[tuple[float, float, float, float]],
    vertices: list[Vertex],
    tolerance_px: float = 10.0
) -> tuple[list[dict], list[dict]]:
    """
    Convert orthogonal segments and vertices to JSON-serializable format.
    Returns (nodes, edges) for frontend consumption.
    """
    nodes = [
        {
            "id": v.id,
            "x": v.x,
            "y": v.y,
            "junction_type": v.junction_type,
            "degree": v.degree
        }
        for v in vertices
    ]
    
    edges = []
    edge_id = 0
    
    for x1, y1, x2, y2 in ortho_segments:
        start_v = _find_nearest_vertex(x1, y1, vertices, tolerance_px)
        end_v = _find_nearest_vertex(x2, y2, vertices, tolerance_px)
        
        if start_v is None or end_v is None or start_v.id == end_v.id:
            continue
        
        length = math.hypot(x2 - x1, y2 - y1)
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        
        edges.append({
            "id": edge_id,
            "a": start_v.id,
            "b": end_v.id,
            "length_px": length,
            "angle_deg": angle
        })
        edge_id += 1
    
    return nodes, edges
