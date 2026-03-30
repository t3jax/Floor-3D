export interface Point2D {
  x: number;
  y: number;
}

export interface WallEdge {
  a: number;
  b: number;
  length_px: number;
  kind: 'exterior' | 'interior';
  thickness_category?: 'major' | 'minor';
  thickness_m?: number;
}

export interface RoomRegion {
  id: string;
  polygon: Point2D[];
  area_px: number;
  centroid: Point2D;
}

export interface StaircaseData {
  detected: boolean;
  type: 'straight' | 'l_shaped' | 'spiral' | 'unknown';
  bounding_box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  center: Point2D;
  direction: 'up' | 'down' | 'unknown';
  num_steps: number;
}

export interface ScaleMetadata {
  scale_factor: number;
  scaling_method: 'ocr' | 'heuristic' | 'default';
  is_heuristic_scale: boolean;
  confidence: number;
  aspect_ratio: number;
  reference_length_px: number;
  reference_length_m: number;
  detected_dimensions?: any[];
  room_labels?: any[];
}

export interface GraphPayload {
  nodes: Point2D[];
  edges: WallEdge[];
  rooms: RoomRegion[];
  gaps?: Point2D[];
  has_second_floor?: boolean;
  void_coordinates?: [number, number];
  staircase?: StaircaseData;
  scale_metadata?: ScaleMetadata;
}

export interface MaterialRecommendation {
  material_id: string;
  name: string;
  score: number;
  strength: number;
  durability: number;
  cost_per_unit: number;
}

export interface CostEstimate {
  material_id: string;
  material_name: string;
  total_volume_m3: number;
  unit_cost: number;
  total_cost: number;
  wall_type: 'exterior' | 'interior' | 'all';
  strength?: number;
  durability?: number;
}

export interface MaterialComparison {
  material_id: string;
  material_name: string;
  estimated_cost: number;
  cost_per_unit: number;
  unit: string;
  rating: string;
  color: string;
  pros: string[];
  cons: string[];
}

export interface ProcessResult {
  success: boolean;
  message: string;
  graph?: GraphPayload;
  raw_lines: [number, number, number, number][];
  snapped_segments: [number, number, number, number][];
  detection_mode: 'opencv' | 'fallback';
  material_recommendations: Record<string, MaterialRecommendation[]>;
  cost_estimates?: CostEstimate[];
  total_construction_cost?: number;
  material_comparisons?: MaterialComparison[];
  llm_prompt: string;
  meta: Record<string, any>;
  project_id?: string;
  scale_metadata?: ScaleMetadata;
}
