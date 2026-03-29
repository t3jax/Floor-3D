export interface Point2D {
  x: number;
  y: number;
}

export interface WallEdge {
  a: number;
  b: number;
  length_px: number;
  kind: 'exterior' | 'interior';
}

export interface RoomRegion {
  id: string;
  polygon: Point2D[];
  area_px: number;
  centroid: Point2D;
}

export interface GraphPayload {
  nodes: Point2D[];
  edges: WallEdge[];
  rooms: RoomRegion[];
  gaps?: Point2D[];
}

export interface MaterialRecommendation {
  material_id: string;
  name: string;
  score: number;
  strength: number;
  durability: number;
  cost_per_unit: number;
}

export interface ProcessResult {
  success: boolean;
  message: string;
  graph?: GraphPayload;
  raw_lines: [number, number, number, number][];
  snapped_segments: [number, number, number, number][];
  detection_mode: 'opencv' | 'fallback';
  material_recommendations: Record<string, MaterialRecommendation[]>;
  llm_prompt: string;
  meta: Record<string, any>;
  project_id?: string;
}
