"""
LLM prompt template: geometric stats + wall types → narrative explanation of material choices.
"""

from __future__ import annotations

from app.schemas import GraphPayload, MaterialRecommendation


def build_material_explanation_prompt(
    graph: GraphPayload,
    recommendations: dict[str, list[MaterialRecommendation]],
    extra_context: str | None = None,
) -> str:
    ext = sum(1 for e in graph.edges if e.kind == "exterior")
    interior = sum(1 for e in graph.edges if e.kind == "interior")
    lengths = [e.length_px for e in graph.edges]
    max_span = max(lengths) if lengths else 0.0
    avg_span = sum(lengths) / len(lengths) if lengths else 0.0

    lines = [
        "You are a structural engineering assistant. Explain material choices clearly for a non-expert.",
        "",
        "## Detected geometry",
        f"- Nodes: {len(graph.nodes)}",
        f"- Wall segments: {len(graph.edges)}",
        f"- Exterior (load-bearing) segments: {ext}",
        f"- Interior (partition) segments: {interior}",
        f"- Approx. max wall segment length (px): {max_span:.1f}",
        f"- Approx. mean segment length (px): {avg_span:.1f}",
        f"- Room regions detected: {len(graph.rooms)}",
        "",
        "## Top material recommendations (score = (0.6×Strength + 0.4×Durability) / Cost)",
    ]
    for key, recs in recommendations.items():
        lines.append(f"### {key}")
        for r in recs:
            lines.append(
                f"- {r.name} (id={r.material_id}): score={r.score:.4f}, "
                f"strength={r.strength}, durability={r.durability}, cost={r.cost_per_unit}"
            )
    if extra_context:
        lines.extend(["", "## Additional context", extra_context])
    lines.extend(
        [
            "",
            "## Task",
            "Write a short, structured explanation (3–6 bullet points) of why these materials "
            "fit the detected spans and wall roles. Mention tradeoffs between cost and structural "
            "performance. Do not invent numeric loads; refer only to relative spans and roles given.",
        ]
    )
    return "\n".join(lines)
