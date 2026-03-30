"""
Material DB + tradeoff score: (Strength * 0.6 + Durability * 0.4) / Cost
Cost estimation based on wall dimensions
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

from app.config import settings
from app.schemas import MaterialEntry, MaterialRecommendation
from app.database import get_db, get_db_session, Material


@dataclass
class CostEstimate:
    """Cost estimate for a material choice"""
    material_id: str
    material_name: str
    total_volume_m3: float
    unit_cost: float
    total_cost: float
    wall_type: str  # 'exterior', 'interior', or 'all'


def load_materials(path: Path | None = None) -> list[MaterialEntry]:
    """
    Load materials from Supabase database.
    Falls back to legacy SQL interface for compatibility.
    """
    # Option 1: Using modern ORM (preferred for new code)
    try:
        with get_db_session() as db:
            materials = db.query(Material).all()
            return [MaterialEntry(
                id=m.id,
                name=m.name,
                strength=m.strength,
                durability=m.durability,
                cost_per_unit=m.cost_per_unit,
                unit=m.unit,
                notes=m.notes
            ) for m in materials]
    except Exception:
        # Option 2: Fallback to legacy SQL interface
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM materials")
        rows = c.fetchall()
        conn.close()
        
        return [MaterialEntry(
            id=row[0] if isinstance(row, tuple) else row['id'],
            name=row[1] if isinstance(row, tuple) else row['name'],
            strength=row[2] if isinstance(row, tuple) else row['strength'],
            durability=row[3] if isinstance(row, tuple) else row['durability'],
            cost_per_unit=row[4] if isinstance(row, tuple) else row['cost_per_unit'],
            unit=row[5] if isinstance(row, tuple) else row['unit'],
            notes=row[6] if isinstance(row, tuple) else row['notes']
        ) for row in rows]


def score_material(strength: float, durability: float, cost: float) -> float:
    if cost <= 0:
        return 0.0
    return (strength * 0.6 + durability * 0.4) / cost


def calculate_wall_volume(
    edges: list,
    nodes: list,
    wall_kind: str | None = None,
    wall_height_m: float = 3.0,
    wall_thickness_m: float = 0.23,  # Standard brick wall thickness
    px_to_m_scale: float = 0.01,  # 1 pixel = 0.01 meters (adjustable)
) -> float:
    """
    Calculate total wall volume in cubic meters.
    
    Args:
        edges: List of wall edge dictionaries with 'length_px' and 'kind'
        nodes: List of node points
        wall_kind: Filter by wall type ('exterior', 'interior', or None for all)
        wall_height_m: Wall height in meters (default 3m for standard floor)
        wall_thickness_m: Wall thickness in meters
        px_to_m_scale: Scale factor to convert pixels to meters
    
    Returns:
        Total volume in cubic meters
    """
    total_length_px = 0.0
    
    for edge in edges:
        if wall_kind is None or edge.get('kind') == wall_kind:
            total_length_px += edge.get('length_px', 0)
    
    # Convert to meters
    total_length_m = total_length_px * px_to_m_scale
    
    # Volume = length × height × thickness
    volume_m3 = total_length_m * wall_height_m * wall_thickness_m
    
    return round(volume_m3, 2)


def estimate_construction_cost(
    edges: list,
    nodes: list,
    materials: list[MaterialEntry],
    has_second_floor: bool = False,
) -> tuple[list[dict], float]:
    """
    Estimate construction costs using AI model when available.
    Falls back to simple calculation if ML model is not loaded.
    
    Returns:
        Tuple of (list of cost estimates per material, recommended total cost)
    """
    from app.ml_cost_estimator import get_cost_estimator
    
    # Calculate volumes
    exterior_volume = calculate_wall_volume(edges, nodes, wall_kind='exterior')
    interior_volume = calculate_wall_volume(edges, nodes, wall_kind='interior')
    total_volume = exterior_volume + interior_volume
    
    # If second floor, double the volume
    if has_second_floor:
        exterior_volume *= 2
        interior_volume *= 2
        total_volume *= 2
    
    # Get AI cost estimator
    cost_estimator = get_cost_estimator()
    
    cost_estimates = []
    
    for material in materials:
        # Try to get AI prediction
        ai_estimate = cost_estimator.estimate_cost(
            material=material.name,
            grade='Standard',
            volume_m3=total_volume,
            transport_distance_km=30.0,
            labor_intensity_score=5.0,
            market_volatility=1.0
        )
        
        # Use AI prediction if available, otherwise fallback
        if ai_estimate.get('is_ai_generated', False):
            material_cost = ai_estimate['predicted_cost']
            unit_cost = material_cost / total_volume if total_volume > 0 else material.cost_per_unit
        else:
            # Fallback to simple calculation
            unit_cost = material.cost_per_unit
            material_cost = total_volume * unit_cost
        
        cost_estimates.append({
            'material_id': material.id,
            'material_name': material.name,
            'total_volume_m3': round(total_volume, 2),
            'unit_cost': round(unit_cost, 2),
            'total_cost': round(material_cost, 2),
            'wall_type': 'all',
            'strength': material.strength,
            'durability': material.durability,
            'is_ai_generated': ai_estimate.get('is_ai_generated', False),
            'ai_confidence': ai_estimate.get('confidence', 0.0),
        })
    
    # Sort by cost
    cost_estimates.sort(key=lambda x: x['total_cost'])
    
    # Recommended cost: use best score material
    best_score_material = None
    best_score = -1
    for m in materials:
        s = score_material(m.strength, m.durability, m.cost_per_unit)
        if s > best_score:
            best_score = s
            best_score_material = m
    
    # Get AI cost for recommended material
    if best_score_material:
        recommended_estimate = cost_estimator.estimate_cost(
            material=best_score_material.name,
            grade='Standard',
            volume_m3=total_volume,
            transport_distance_km=30.0,
            labor_intensity_score=5.0,
            market_volatility=1.0
        )
        if recommended_estimate.get('is_ai_generated', False):
            recommended_cost = recommended_estimate['predicted_cost']
        else:
            recommended_cost = total_volume * best_score_material.cost_per_unit
    else:
        recommended_cost = 0
    
    return cost_estimates, round(recommended_cost, 2)


def get_material_comparison(
    total_volume: float,
    materials: list[MaterialEntry],
) -> list[dict]:
    """
    Generate a comparison of costs for different materials using AI predictions.
    
    Returns:
        List of comparisons showing "If you use X material, it will cost Y"
    """
    from app.ml_cost_estimator import get_cost_estimator
    
    cost_estimator = get_cost_estimator()
    comparisons = []
    
    for material in materials:
        # Get AI prediction for this material
        ai_estimate = cost_estimator.estimate_cost(
            material=material.name,
            grade='Standard',
            volume_m3=total_volume,
            transport_distance_km=30.0,
            labor_intensity_score=5.0,
            market_volatility=1.0
        )
        
        # Use AI cost if available, otherwise fallback to simple calculation
        if ai_estimate.get('is_ai_generated', False):
            cost = ai_estimate['predicted_cost']
            unit_cost = cost / total_volume if total_volume > 0 else material.cost_per_unit
        else:
            cost = total_volume * material.cost_per_unit
            unit_cost = material.cost_per_unit
        
        # Determine cost rating
        if cost < 500000:
            rating = "Budget-Friendly"
            color = "green"
        elif cost < 1500000:
            rating = "Moderate"
            color = "orange"
        else:
            rating = "Premium"
            color = "red"
        
        comparisons.append({
            'material_id': material.id,
            'material_name': material.name,
            'estimated_cost': round(cost, 2),
            'cost_per_unit': round(unit_cost, 2),
            'unit': material.unit,
            'rating': rating,
            'color': color,
            'pros': get_material_pros(material),
            'cons': get_material_cons(material),
            'is_ai_generated': ai_estimate.get('is_ai_generated', False),
            'ai_confidence': ai_estimate.get('confidence', 0.0),
        })
    
    return sorted(comparisons, key=lambda x: x['estimated_cost'])


def get_material_pros(material: MaterialEntry) -> list[str]:
    """Get pros for a material based on its properties."""
    pros = []
    
    if material.strength >= 8:
        pros.append("Excellent structural strength")
    elif material.strength >= 5:
        pros.append("Good load-bearing capacity")
    
    if material.durability >= 8:
        pros.append("Outstanding durability")
    elif material.durability >= 6:
        pros.append("Long-lasting")
    
    if material.cost_per_unit <= 3000:
        pros.append("Very cost-effective")
    elif material.cost_per_unit <= 5000:
        pros.append("Affordable")
    
    if material.id in ['aac', 'fly_ash']:
        pros.append("Eco-friendly option")
        pros.append("Good thermal insulation")
    
    if material.id == 'steel':
        pros.append("Best strength-to-weight ratio")
        pros.append("Fast construction")
    
    if material.id == 'precast':
        pros.append("Factory-controlled quality")
        pros.append("Reduced construction time")
    
    return pros[:3]  # Return top 3 pros


def get_material_cons(material: MaterialEntry) -> list[str]:
    """Get cons for a material based on its properties."""
    cons = []
    
    if material.strength < 5:
        cons.append("Not suitable for load-bearing walls")
    
    if material.durability < 5:
        cons.append("May require frequent maintenance")
    
    if material.cost_per_unit > 8000:
        cons.append("High initial investment")
    
    if material.id in ['aac', 'fly_ash']:
        cons.append("Not for multi-storey structures")
    
    if material.id == 'steel':
        cons.append("Requires corrosion protection")
        cons.append("Higher thermal conductivity")
    
    if material.id == 'red_brick':
        cons.append("Slower construction")
        cons.append("Higher water absorption")
    
    return cons[:2]  # Return top 2 cons


def top_k_materials(
    materials: list[MaterialEntry],
    k: int = 3,
    *,
    prefer_load_bearing: bool = False,
    has_second_floor: bool = False,
) -> tuple[list[MaterialRecommendation], list[str]]:
    ranked: list[MaterialRecommendation] = []
    exclusions: list[str] = []
    
    # Structural Math Adjustment: Multi-Storey Load Factor
    load_factor = 1.5 if (prefer_load_bearing and has_second_floor) else 1.0

    for m in materials:
        # Base criteria block (strength < 5.0 for load bearing)
        if prefer_load_bearing and m.strength < 5.0:
            exclusions.append(f"{m.name} (id={m.id}) was excluded due to insufficient compressive strength ({m.strength} < 5 MPa) for a load-bearing wall.")
            continue
            
        # Multi-Storey block: Outright block AAC Blocks or Fly Ash if supporting level above
        if prefer_load_bearing and has_second_floor and m.id in ["aac", "fly_ash"]:
            exclusions.append(f"{m.name} was rejected because it cannot safely support multi-storey vertical loads.")
            continue
            
        # Apply the Load Factor Penalty to cost efficiency (makes weak/cheap materials score worse relative to structural need)
        # We increase the 'cost' penalty computationally by the load_factor so the ratio drops for non-structural materials
        effective_cost = m.cost_per_unit * load_factor if m.id not in ["rcc", "steel", "red_brick"] else m.cost_per_unit

        s = score_material(m.strength, m.durability, effective_cost)
        ranked.append(
            MaterialRecommendation(
                material_id=m.id,
                name=m.name,
                score=round(s, 6),
                strength=m.strength,
                durability=m.durability,
                cost_per_unit=m.cost_per_unit,
            )
        )
        
    if prefer_load_bearing:
        boost = {"steel", "rcc", "precast"}
        for item in ranked:
            if item.material_id in boost:
                # Geometric reliability boost
                item.score *= 1.2
                
    ranked.sort(key=lambda x: -x.score)
    return ranked[:k], exclusions


def recommendations_for_context(
    materials: list[MaterialEntry],
    *,
    wall_kind: str,
    span_px: float | None = None,
    has_second_floor: bool = False,
) -> tuple[list[MaterialRecommendation], list[str]]:
    prefer = wall_kind == "exterior"
    return top_k_materials(materials, k=3, prefer_load_bearing=prefer, has_second_floor=has_second_floor)
