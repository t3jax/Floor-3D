"""
Orchestrates OpenCV detection → graph → materials → LLM prompt.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.config import settings
from app.database import get_db
import uuid
from app.geometry_graph import build_graph_payload, graph_from_fallback
from app.llm_prompt import build_material_explanation_prompt
from app.materials import load_materials, recommendations_for_context
from app.opencv_engine import detect_walls_opencv, has_meaningful_geometry
from app.schemas import FallbackGraphInput, GraphPayload, MaterialRecommendation, ProcessResult


def _material_map_for_graph(graph: GraphPayload) -> tuple[dict[str, list[MaterialRecommendation]], list[str]]:
    materials = load_materials()
    out: dict[str, list[MaterialRecommendation]] = {}
    all_exclusions: list[str] = []

    ext_recs, ext_exc = recommendations_for_context(
        materials, wall_kind="exterior", span_px=None, has_second_floor=graph.has_second_floor
    )
    int_recs, int_exc = recommendations_for_context(
        materials, wall_kind="interior", span_px=None, has_second_floor=graph.has_second_floor
    )
    all_exclusions.extend(ext_exc)
    all_exclusions.extend(int_exc)
    
    out["exterior_walls"] = ext_recs
    out["interior_walls"] = int_recs

    for i, room in enumerate(graph.rooms):
        label = f"room:{room.id}"
        prefer = float(room.area_px) > 5000
        recs, exc = recommendations_for_context(
            materials,
            wall_kind="exterior" if prefer else "interior",
            span_px=None,
            has_second_floor=graph.has_second_floor,
        )
        out[label] = recs
        all_exclusions.extend(exc)

    if not graph.rooms:
        out["general"] = ext_recs

    # Deduplicate exclusions
    unique_exc = list(dict.fromkeys(all_exclusions))
    
    return out, unique_exc


def process_image_bytes(image_bytes: bytes) -> ProcessResult:
    arr = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return ProcessResult(
            success=False,
            message="Could not decode image bytes.",
            detection_mode="opencv",
        )

    det = detect_walls_opencv(img)
    ok = has_meaningful_geometry(len(det.snapped_segments), len(det.contours))

    if not ok or len(det.snapped_segments) < 2:
        return ProcessResult(
            success=False,
            message="OpenCV did not find enough wall geometry. Use fallback JSON mode.",
            raw_lines=det.lines_hough,
            snapped_segments=det.snapped_segments,
            detection_mode="opencv",
            meta={
                "contour_count": len(det.contours),
                "hough_line_count": len(det.lines_hough),
            },
        )

    graph = build_graph_payload(
        det.snapped_segments,
        det.binary_vis,
        det.image_shape,
        settings.snap_tolerance_px,
        det.has_second_floor,
        det.void_coordinates,
    )
    mats, exclusions = _material_map_for_graph(graph)
    
    extra_context = ""
    if exclusions:
        extra_context += "The following materials were actively excluded from the recommendations for safety/reliability:\n"
        for exc in exclusions:
            extra_context += f"- {exc}\n"
            
    prompt = build_material_explanation_prompt(graph, mats, extra_context=extra_context)

    project_id = str(uuid.uuid4())
    
    # Save geometry to database
    conn = get_db()
    c = conn.cursor()
    for e in graph.edges:
        c.execute('''
            INSERT INTO Structural_Elements (id, project_id, element_type, length_px, has_second_floor)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), project_id, e.kind, e.length_px, graph.has_second_floor))

    # Save recommendations
    for group, recs in mats.items():
        for r in recs:
            c.execute('''
                INSERT INTO Recommendations (id, project_id, element_id, material_id, score, llm_explanation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(uuid.uuid4()), project_id, group, r.material_id, r.score, prompt))
            
    conn.commit()
    conn.close()

    return ProcessResult(
        success=True,
        message="Parsed floor plan.",
        graph=graph,
        raw_lines=det.lines_hough,
        snapped_segments=det.snapped_segments,
        detection_mode="opencv",
        material_recommendations=mats,
        llm_prompt=prompt,
        meta={
            "image_shape": list(det.image_shape),
            "snap_tolerance_px": settings.snap_tolerance_px,
        },
        project_id=project_id
    )


def process_fallback(payload: FallbackGraphInput) -> ProcessResult:
    nodes = [(p.x, p.y) for p in payload.nodes]
    rooms_spec = payload.rooms
    graph = graph_from_fallback(nodes, payload.edges, rooms_spec)
    mats, exclusions = _material_map_for_graph(graph)
    
    extra_context = ""
    if exclusions:
        extra_context += "The following materials were actively excluded from the recommendations for safety/reliability:\n"
        for exc in exclusions:
            extra_context += f"- {exc}\n"
            
    prompt = build_material_explanation_prompt(graph, mats, extra_context=extra_context)

    return ProcessResult(
        success=True,
        message="Loaded geometry from fallback JSON.",
        graph=graph,
        detection_mode="fallback",
        material_recommendations=mats,
        llm_prompt=prompt,
        meta={"snap_tolerance_px": settings.snap_tolerance_px},
    )
