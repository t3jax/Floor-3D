from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Point2D(BaseModel):
    x: float
    y: float


class WallEdge(BaseModel):
    """A wall segment between two snapped nodes."""

    a: int
    b: int
    length_px: float
    kind: Literal["exterior", "interior"] = "interior"
    thickness_category: Literal["major", "minor"] = "minor"
    thickness_m: float = 0.115  # Default minor thickness


class ScaleMetadata(BaseModel):
    """Metadata about the scaling calibration."""
    scale_factor: float = 0.01  # pixels to meters
    scaling_method: Literal["ocr", "heuristic", "default"] = "default"
    is_heuristic_scale: bool = True
    confidence: float = 0.0
    aspect_ratio: float = 1.0
    reference_length_px: Optional[float] = None
    reference_length_m: Optional[float] = None
    detected_dimensions: list[dict] = Field(default_factory=list)
    room_labels: list[dict] = Field(default_factory=list)


class RoomRegion(BaseModel):
    id: str
    polygon: list[Point2D]
    area_px: float
    centroid: Point2D


class StaircaseData(BaseModel):
    """Detected staircase information."""
    detected: bool = False
    type: Literal["straight", "l_shaped", "spiral", "unknown"] = "unknown"
    bounding_box: dict = Field(default_factory=lambda: {"x": 0, "y": 0, "width": 0, "height": 0})
    center: Point2D = Field(default_factory=lambda: Point2D(x=0, y=0))
    direction: Literal["up", "down", "unknown"] = "unknown"
    num_steps: int = 17  # Default for 3m height with 18cm steps


class GraphPayload(BaseModel):
    nodes: list[Point2D]
    edges: list[WallEdge]
    rooms: list[RoomRegion]
    gaps: list[Point2D] | None = None
    has_second_floor: bool = False
    void_coordinates: tuple[float, float] | None = None
    staircase: StaircaseData | None = None
    scale_metadata: ScaleMetadata | None = None


class MaterialEntry(BaseModel):
    id: str
    name: str
    strength: float
    durability: float
    cost_per_unit: float
    unit: str = ""
    notes: str = ""
    cost_level: str = ""
    strength_level: str = ""
    durability_level: str = ""
    best_use: str = ""


class MaterialRecommendation(BaseModel):
    material_id: str
    name: str
    score: float
    strength: float
    durability: float
    cost_per_unit: float


class CostEstimate(BaseModel):
    """Cost estimate for a material choice."""
    material_id: str
    material_name: str
    total_volume_m3: float
    unit_cost: float
    total_cost: float
    wall_type: str
    strength: float = 0.0
    durability: float = 0.0


class MaterialComparison(BaseModel):
    """Material comparison with pros/cons."""
    material_id: str
    material_name: str
    estimated_cost: float
    cost_per_unit: float
    unit: str
    rating: str
    color: str
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


class ProcessResult(BaseModel):
    success: bool
    message: str = ""
    graph: GraphPayload | None = None
    raw_lines: list[tuple[float, float, float, float]] = Field(default_factory=list)
    snapped_segments: list[tuple[float, float, float, float]] = Field(default_factory=list)
    detection_mode: Literal["opencv", "fallback"] = "opencv"
    material_recommendations: dict[str, list[MaterialRecommendation]] = Field(default_factory=dict)
    cost_estimates: list[dict] = Field(default_factory=list)
    total_construction_cost: float = 0.0
    material_comparisons: list[dict] = Field(default_factory=list)
    llm_prompt: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    scale_metadata: ScaleMetadata | None = None


class FallbackGraphInput(BaseModel):
    """Manual / recovered geometry when OpenCV fails to close loops."""

    nodes: list[Point2D]
    edges: list[tuple[int, int]]
    rooms: list[list[int]] | None = None
