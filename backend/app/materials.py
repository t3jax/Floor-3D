"""
Material DB + tradeoff score: (Strength * 0.6 + Durability * 0.4) / Cost
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.schemas import MaterialEntry, MaterialRecommendation
from app.database import get_db

def load_materials(path: Path | None = None) -> list[MaterialEntry]:
    # We now fetch from our SQLite Database instead of the JSON
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM Materials")
    rows = c.fetchall()
    conn.close()
    
    return [MaterialEntry(
        id=row['id'],
        name=row['name'],
        strength=row['strength'],
        durability=row['durability'],
        cost_per_unit=row['cost_per_unit'],
        unit=row['unit'],
        notes=row['notes']
    ) for row in rows]


def score_material(strength: float, durability: float, cost: float) -> float:
    if cost <= 0:
        return 0.0
    return (strength * 0.6 + durability * 0.4) / cost


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
