"""
Node/edge graph from segments; Shapely room polygons; exterior vs interior walls.
Simplified version with cleaner wall classification.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon, Point
from shapely.ops import linemerge, unary_union

from app.config import settings
from app.schemas import GraphPayload, Point2D, RoomRegion, WallEdge, StaircaseData


def _edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def segments_to_graph(
    segments: list[tuple[float, float, float, float]],
    tolerance: float | None = None,
) -> tuple[list[tuple[float, float]], list[tuple[int, int]]]:
    tol = tolerance if tolerance is not None else settings.snap_tolerance_px
    pts = []
    for x1, y1, x2, y2 in segments:
        pts.append((float(x1), float(y1)))
        pts.append((float(x2), float(y2)))

    from app.snapping import merge_nearby_points
    canonical, remap = merge_nearby_points(pts, tol)

    edges_set: set[tuple[int, int]] = set()
    for i in range(0, len(pts), 2):
        i1 = remap[i]
        i2 = remap[i + 1]
        if i1 != i2:
            edges_set.add(_edge_key(i1, i2))

    return canonical, sorted(edges_set)


def _polygon_from_contours(
    contours: list,
    image_shape: tuple[int, int],
) -> list[RoomRegion]:
    h, w = image_shape
    img_area = float(h * w)
    rooms: list[RoomRegion] = []
    min_a = settings.min_room_area_ratio * img_area
    max_a = settings.max_room_area_ratio * img_area
    
    for i, c in enumerate(contours):
        if len(c) < 3:
            continue
        poly = Polygon([(p[0][0], p[0][1]) for p in c])
        if not poly.is_valid:
            poly = poly.buffer(0)
        a = poly.area
        if a < min_a or a > max_a:
            continue
        try:
            c_pt = poly.centroid
        except Exception:
            continue
        coords = list(poly.exterior.coords)[:-1]
        rooms.append(
            RoomRegion(
                id=f"room_{i}",
                polygon=[Point2D(x=float(px), y=float(py)) for px, py in coords],
                area_px=float(a),
                centroid=Point2D(x=float(c_pt.x), y=float(c_pt.y)),
            )
        )
    rooms.sort(key=lambda r: -r.area_px)
    return rooms[:10]  # Limit to 10 rooms max


def rooms_from_binary_mask(binary: np.ndarray) -> list[RoomRegion]:
    inv = 255 - binary
    contours, _ = cv2.findContours(inv, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    h, w = binary.shape[:2]
    return _polygon_from_contours(contours, (h, w))


def classify_wall_edges(
    nodes: list[tuple[float, float]],
    edges: list[tuple[int, int]],
    rooms: list[RoomRegion],
    image_shape: tuple[int, int] | None = None,
) -> list[WallEdge]:
    if not edges:
        return []

    # Calculate bounds
    if nodes:
        xs = [n[0] for n in nodes]
        ys = [n[1] for n in nodes]
        bounds = (min(xs), min(ys), max(xs), max(ys))
    else:
        bounds = (0, 0, 100, 100)
    
    min_x, min_y, max_x, max_y = bounds
    margin = 15  # Edge margin for exterior walls

    result: list[WallEdge] = []
    
    for (a, b) in edges:
        if a >= len(nodes) or b >= len(nodes):
            continue
            
        p0, p1 = nodes[a], nodes[b]
        length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        
        # Skip very short walls
        if length < settings.min_wall_length_px:
            continue
        
        # Determine if exterior or interior based on position
        # Walls near the outer boundary are exterior
        near_edge = (
            p0[0] < min_x + margin or p0[0] > max_x - margin or
            p1[0] < min_x + margin or p1[0] > max_x - margin or
            p0[1] < min_y + margin or p0[1] > max_y - margin or
            p1[1] < min_y + margin or p1[1] > max_y - margin
        )
        
        kind = "exterior" if near_edge else "interior"

        result.append(WallEdge(a=a, b=b, length_px=length, kind=kind))
    
    return result


def build_graph_payload(
    segments: list[tuple[float, float, float, float]],
    binary_for_rooms: np.ndarray | None,
    image_shape: tuple[int, int],
    tolerance: float | None = None,
    has_second_floor: bool = False,
    void_coordinates: tuple[float, float] | None = None,
    staircase_info: dict | None = None,
) -> GraphPayload:
    nodes_t, edges_t = segments_to_graph(segments, tolerance)
    nodes = [(float(x), float(y)) for x, y in nodes_t]

    rooms: list[RoomRegion] = []
    if binary_for_rooms is not None:
        rooms = rooms_from_binary_mask(binary_for_rooms)

    wall_edges = classify_wall_edges(nodes, edges_t, rooms, image_shape)

    # Calculate gaps (nodes with exactly 1 connection)
    degree_map = {i: 0 for i in range(len(nodes))}
    for e in wall_edges:
        degree_map[e.a] += 1
        degree_map[e.b] += 1
    
    gaps = [Point2D(x=nodes[i][0], y=nodes[i][1]) for i, deg in degree_map.items() if deg == 1]

    # Convert staircase info to StaircaseData
    staircase_data = None
    if staircase_info and staircase_info.get('detected'):
        staircase_data = StaircaseData(
            detected=staircase_info.get('detected', False),
            type=staircase_info.get('staircase_type', 'unknown'),
            bounding_box=staircase_info.get('bounding_box', {"x": 0, "y": 0, "width": 0, "height": 0}),
            center=Point2D(
                x=staircase_info.get('center', (0, 0))[0],
                y=staircase_info.get('center', (0, 0))[1]
            ),
            direction=staircase_info.get('direction', 'unknown'),
            num_steps=staircase_info.get('num_steps', 17)
        )

    return GraphPayload(
        nodes=[Point2D(x=x, y=y) for x, y in nodes],
        edges=wall_edges,
        rooms=rooms,
        gaps=gaps,
        has_second_floor=has_second_floor,
        void_coordinates=void_coordinates,
        staircase=staircase_data
    )


def graph_from_fallback(
    nodes: list[tuple[float, float]],
    edges: list[tuple[int, int]],
    room_vertex_indices: list[list[int]] | None,
) -> GraphPayload:
    pts = [(float(x), float(y)) for x, y in nodes]
    
    rooms: list[RoomRegion] = []
    if room_vertex_indices:
        for i, loop in enumerate(room_vertex_indices):
            if len(loop) < 3:
                continue
            coords = [pts[j] for j in loop if j < len(pts)]
            if len(coords) < 3:
                continue
            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
            c = poly.centroid
            rooms.append(
                RoomRegion(
                    id=f"room_{i}",
                    polygon=[Point2D(x=x, y=y) for x, y in coords],
                    area_px=float(poly.area),
                    centroid=Point2D(x=float(c.x), y=float(c.y)),
                )
            )

    wall_edges = classify_wall_edges(pts, edges, rooms)

    # Calculate gaps
    degree_map = {i: 0 for i in range(len(pts))}
    for e in wall_edges:
        degree_map[e.a] += 1
        degree_map[e.b] += 1
    
    gaps = [Point2D(x=pts[i][0], y=pts[i][1]) for i, deg in degree_map.items() if deg == 1]

    return GraphPayload(
        nodes=[Point2D(x=x, y=y) for x, y in pts],
        edges=wall_edges,
        rooms=rooms,
        gaps=gaps,
    )
