"""
Orchestrates OpenCV detection → graph → materials → LLM prompt.
"""

from __future__ import annotations

import json
import cv2
import numpy as np

from app.config import settings
from app.database import get_db
import uuid
from app.geometry_graph import build_graph_payload, graph_from_fallback
from app.llm_prompt import build_material_explanation_prompt
from app.materials import (
    load_materials, 
    recommendations_for_context, 
    estimate_construction_cost,
    get_material_comparison,
    calculate_wall_volume
)
from app.opencv_engine import detect_walls_opencv, has_meaningful_geometry
from app.schemas import FallbackGraphInput, GraphPayload, MaterialRecommendation, ProcessResult, ScaleMetadata
from app.scaling_engine import get_scaling_engine, analyze_wall_thickness, count_staircase_treads, calculate_staircase_height
from app.graph_reconstruction import reconstruct_wall_graph, snap_to_orthogonal_grid


def _to_python_native(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _to_python_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_to_python_native(i) for i in obj]
    return obj


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


def _calculate_cost_estimates(graph: GraphPayload) -> tuple[list[dict], float, list[dict]]:
    """Calculate cost estimates for the floor plan."""
    materials = load_materials()
    
    # Convert edges to dict format for cost calculation
    edges_dict = [
        {'length_px': e.length_px, 'kind': e.kind}
        for e in graph.edges
    ]
    nodes_dict = [{'x': n.x, 'y': n.y} for n in graph.nodes]
    
    # Get cost estimates
    cost_estimates, recommended_cost = estimate_construction_cost(
        edges_dict,
        nodes_dict,
        materials,
        has_second_floor=graph.has_second_floor
    )
    
    # Get material comparisons
    total_volume = calculate_wall_volume(edges_dict, nodes_dict)
    if graph.has_second_floor:
        total_volume *= 2
    
    material_comparisons = get_material_comparison(total_volume, materials)
    
    return cost_estimates, recommended_cost, material_comparisons


def process_image_bytes(image_bytes: bytes) -> ProcessResult:
    try:
        arr = np.asarray(bytearray(image_bytes), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return ProcessResult(
                success=False,
                message="Could not decode image bytes.",
                detection_mode="opencv",
            )

        # Step 1: Run wall detection
        det = detect_walls_opencv(img)
        ok = has_meaningful_geometry(len(det.snapped_segments), len(det.contours))

        if not ok or len(det.snapped_segments) < 2:
            return ProcessResult(
                success=False,
                message="OpenCV did not find enough wall geometry. Use fallback JSON mode.",
                raw_lines=_to_python_native(det.lines_hough),
                snapped_segments=_to_python_native(det.snapped_segments),
                detection_mode="opencv",
                meta=_to_python_native({
                    "contour_count": len(det.contours),
                    "hough_line_count": len(det.lines_hough),
                }),
            )

        # Step 2: Calculate scale factor using tiered approach (OCR → Heuristic → Default)
        scaling_engine = get_scaling_engine(enable_ocr=settings.enable_ocr_labels)
        scale_result = scaling_engine.calculate_scale(img, det.snapped_segments)
        
        # Create scale metadata for response
        scale_metadata = ScaleMetadata(
            scale_factor=float(scale_result.scale_factor),
            scaling_method=str(scale_result.scaling_method),
            is_heuristic_scale=(scale_result.scaling_method != "ocr"),
            confidence=float(scale_result.confidence),
            aspect_ratio=float(scale_result.aspect_ratio),
            reference_length_px=float(scale_result.reference_length_px) if scale_result.reference_length_px else None,
            reference_length_m=float(scale_result.reference_length_m) if scale_result.reference_length_m else None,
            detected_dimensions=scale_result.detected_dimensions,
            room_labels=scale_result.room_labels
        )
        
        # Step 3: Apply orthogonal snapping to segments
        ortho_segments = snap_to_orthogonal_grid(det.snapped_segments, angle_tolerance_deg=5.0)
        
        # Step 4: Analyze wall thickness
        thickness_result = analyze_wall_thickness(img, ortho_segments, scale_result.scale_factor)
        
        # Step 5: Count staircase treads and calculate height if staircase detected
        staircase_height_m = 3.0  # Default floor height
        num_steps = 17
        if det.staircase and det.staircase.detected:
            num_steps = count_staircase_treads(det.binary_vis, det.staircase.bounding_box)
            staircase_height_m = calculate_staircase_height(num_steps, 0.15)
        
        # Build graph with updated segments and staircase info
        graph = build_graph_payload(
            ortho_segments,  # Use orthogonal-snapped segments
            det.binary_vis,
            det.image_shape,
            settings.snap_tolerance_px,
            det.has_second_floor,
            det.void_coordinates,
            staircase_info={
                'detected': det.staircase.detected if det.staircase else False,
                'staircase_type': det.staircase.staircase_type if det.staircase else 'unknown',
                'bounding_box': det.staircase.bounding_box if det.staircase else {},
                'center': det.staircase.center if det.staircase else (0, 0),
                'direction': det.staircase.direction if det.staircase else 'unknown',
                'num_steps': num_steps,
                'staircase_height_m': staircase_height_m,
            } if det.staircase else None,
            wall_thicknesses=thickness_result.wall_thicknesses
        )
        
        # Add scale metadata to graph
        graph.scale_metadata = scale_metadata
        
        mats, exclusions = _material_map_for_graph(graph)
        
        # Calculate cost estimates
        cost_estimates, recommended_cost, material_comparisons = _calculate_cost_estimates(graph)
        
        extra_context = ""
        if exclusions:
            extra_context += "The following materials were actively excluded from the recommendations for safety/reliability:\n"
            for exc in exclusions:
                extra_context += f"- {exc}\n"
        
        # Add cost information to context
        extra_context += f"\n\nEstimated construction cost (recommended materials): Rs.{recommended_cost:,.2f}\n"
        extra_context += "Cost varies based on material choice - see cost estimates for details.\n"
                
        prompt = build_material_explanation_prompt(graph, mats, extra_context=extra_context)

        project_id = str(uuid.uuid4())
        
        # Save geometry to database with real world lengths
        conn = get_db()
        c = conn.cursor()
        
        # Save scale metadata
        c.execute('''
            INSERT INTO Scale_Metadata (
                id, project_id, scale_factor, scaling_method, is_heuristic_scale,
                confidence, aspect_ratio, reference_length_px, reference_length_m
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), 
            project_id, 
            scale_result.scale_factor,
            scale_result.scaling_method,
            scale_result.scaling_method != "ocr",
            scale_result.confidence,
            scale_result.aspect_ratio,
            scale_result.reference_length_px,
            scale_result.reference_length_m
        ))
        
        # Save structural elements with real world lengths, thickness, and coordinates
        for idx, e in enumerate(graph.edges):
            real_world_length = e.length_px * scale_result.scale_factor
            
            # Get coordinates from nodes
            node_a = graph.nodes[e.a]
            node_b = graph.nodes[e.b]
            coordinates_json = json.dumps({
                'x1': node_a.x,
                'y1': node_a.y,
                'x2': node_b.x,
                'y2': node_b.y
            })
            
            c.execute('''
                INSERT INTO structural_elements (
                    id, project_id, element_type, length_px, real_world_length_m,
                    thickness_category, thickness_m, has_second_floor, coordinates
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()), 
                project_id, 
                e.kind, 
                e.length_px, 
                real_world_length,
                e.thickness_category,
                e.thickness_m,
                graph.has_second_floor,
                coordinates_json
            ))

        # Save recommendations
        for group, recs in mats.items():
            for r in recs:
                c.execute('''
                    INSERT INTO recommendations (id, project_id, element_id, material_id, score, llm_explanation)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (str(uuid.uuid4()), project_id, group, r.material_id, r.score, prompt))
                
        conn.commit()
        conn.close()

        # Convert all numpy types to native Python types
        raw_lines_native = _to_python_native(det.lines_hough)
        snapped_native = _to_python_native(list(ortho_segments))
        cost_estimates_native = _to_python_native(cost_estimates)
        material_comparisons_native = _to_python_native(material_comparisons)
        
        return ProcessResult(
            success=True,
            message="Parsed floor plan.",
            graph=graph,
            raw_lines=raw_lines_native,
            snapped_segments=snapped_native,
            detection_mode="opencv",
            material_recommendations=mats,
            cost_estimates=cost_estimates_native,
            total_construction_cost=float(recommended_cost),
            material_comparisons=material_comparisons_native,
            llm_prompt=prompt,
            meta=_to_python_native({
                "image_shape": list(det.image_shape),
                "snap_tolerance_px": settings.snap_tolerance_px,
                "scale_factor": scale_result.scale_factor,
                "scaling_method": scale_result.scaling_method,
                "is_heuristic_scale": scale_result.scaling_method != "ocr",
                "aspect_ratio": scale_result.aspect_ratio,
            }),
            project_id=project_id,
            scale_metadata=scale_metadata
        )
    except Exception as e:
        # Catch any unexpected errors and return a proper error response
        import traceback
        print(f"ERROR in process_image_bytes: {e}")
        traceback.print_exc()
        return ProcessResult(
            success=False,
            message=f"Processing failed: {str(e)}",
            detection_mode="opencv",
            meta={"error": str(e)}
        )


def process_fallback(payload: FallbackGraphInput) -> ProcessResult:
    nodes = [(p.x, p.y) for p in payload.nodes]
    rooms_spec = payload.rooms
    graph = graph_from_fallback(nodes, payload.edges, rooms_spec)
    mats, exclusions = _material_map_for_graph(graph)
    
    # Calculate cost estimates for fallback mode too
    cost_estimates, recommended_cost, material_comparisons = _calculate_cost_estimates(graph)
    
    extra_context = ""
    if exclusions:
        extra_context += "The following materials were actively excluded from the recommendations for safety/reliability:\n"
        for exc in exclusions:
            extra_context += f"- {exc}\n"
    
    extra_context += f"\n\nEstimated construction cost (recommended materials): ₹{recommended_cost:,.2f}\n"
            
    prompt = build_material_explanation_prompt(graph, mats, extra_context=extra_context)

    return ProcessResult(
        success=True,
        message="Loaded geometry from fallback JSON.",
        graph=graph,
        detection_mode="fallback",
        material_recommendations=mats,
        cost_estimates=cost_estimates,
        total_construction_cost=recommended_cost,
        material_comparisons=material_comparisons,
        llm_prompt=prompt,
        meta={"snap_tolerance_px": settings.snap_tolerance_px},
    )
