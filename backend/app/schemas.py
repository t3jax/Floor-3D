from typing import Any, Literal

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


class RoomRegion(BaseModel):
    id: str
    polygon: list[Point2D]
    area_px: float
    centroid: Point2D


class GraphPayload(BaseModel):
    nodes: list[Point2D]
    edges: list[WallEdge]
    rooms: list[RoomRegion]
    gaps: list[Point2D] | None = None
    has_second_floor: bool = False
    void_coordinates: tuple[float, float] | None = None


class MaterialEntry(BaseModel):
    id: str
    name: str
    strength: float
    durability: float
    cost_per_unit: float
    unit: str = ""
    notes: str = ""


class MaterialRecommendation(BaseModel):
    material_id: str
    name: str
    score: float
    strength: float
    durability: float
    cost_per_unit: float


class ProcessResult(BaseModel):
    success: bool
    message: str = ""
    graph: GraphPayload | None = None
    raw_lines: list[tuple[float, float, float, float]] = Field(default_factory=list)
    snapped_segments: list[tuple[float, float, float, float]] = Field(default_factory=list)
    detection_mode: Literal["opencv", "fallback"] = "opencv"
    material_recommendations: dict[str, list[MaterialRecommendation]] = Field(default_factory=dict)
    llm_prompt: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None


class FallbackGraphInput(BaseModel):
    """Manual / recovered geometry when OpenCV fails to close loops."""

    nodes: list[Point2D]
    edges: list[tuple[int, int]]
    rooms: list[list[int]] | None = None
