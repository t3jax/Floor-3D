"""
Scaling & Calibration Engine for Floor3D.
Implements a tiered approach:
- Tier 1: OCR-based dimension extraction
- Tier 2: Heuristic room-label scaling
- Tier 3: Aspect ratio constraint
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Literal

import cv2
import numpy as np

# Optional OCR imports
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


@dataclass
class ScaleResult:
    """Result of the scaling calibration."""
    scale_factor: float  # pixels to meters
    scaling_method: Literal["ocr", "heuristic", "default"]
    confidence: float  # 0.0 to 1.0
    detected_dimensions: list[dict] = field(default_factory=list)
    room_labels: list[dict] = field(default_factory=list)
    aspect_ratio: float = 1.0
    reference_length_px: float = 0.0
    reference_length_m: float = 0.0


@dataclass
class WallThicknessResult:
    """Result of wall thickness analysis."""
    wall_thicknesses: list[dict] = field(default_factory=list)  # {segment_idx, thickness_px, category}
    major_thickness_m: float = 0.23
    minor_thickness_m: float = 0.115


# Dimension pattern regex: matches "16m", "9.2m", "12.5 m", "8M", "3.5 meters", etc.
DIMENSION_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:m|meters?|metre?s?|M)\b',
    re.IGNORECASE
)

# Room label patterns for heuristic scaling
ROOM_PATTERNS = {
    'bedroom': {'min_dim_m': 3.0, 'pattern': re.compile(r'\b(?:bed\s*room|bedroom|br|b/r)\b', re.IGNORECASE)},
    'bathroom': {'min_dim_m': 1.8, 'pattern': re.compile(r'\b(?:bath\s*room|bathroom|wc|toilet|w\.c\.)\b', re.IGNORECASE)},
    'kitchen': {'min_dim_m': 2.5, 'pattern': re.compile(r'\b(?:kitchen|kit|k)\b', re.IGNORECASE)},
    'living': {'min_dim_m': 4.0, 'pattern': re.compile(r'\b(?:living|lounge|hall|drawing)\b', re.IGNORECASE)},
    'dining': {'min_dim_m': 3.0, 'pattern': re.compile(r'\b(?:dining|dinning)\b', re.IGNORECASE)},
}

# Default scale when nothing detected
DEFAULT_SCALE = 0.01  # 1 pixel = 1cm


class ScalingEngine:
    """
    Tiered scaling engine for converting pixel measurements to real-world meters.
    """
    
    def __init__(self, enable_ocr: bool = True):
        self.enable_ocr = enable_ocr and EASYOCR_AVAILABLE
        self.ocr_reader = None
        if self.enable_ocr:
            try:
                self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            except Exception:
                self.enable_ocr = False
    
    def calculate_scale(
        self,
        image_bgr: np.ndarray,
        detected_lines: list[tuple[float, float, float, float]] | None = None
    ) -> ScaleResult:
        """
        Calculate the scale factor using tiered approach:
        1. OCR dimension extraction
        2. Heuristic room-label scaling
        3. Default fallback with aspect ratio constraint
        """
        h, w = image_bgr.shape[:2]
        aspect_ratio = w / h if h > 0 else 1.0
        
        # Tier 1: Try OCR-based scaling
        if self.enable_ocr and self.ocr_reader:
            ocr_result = self._tier1_ocr_scaling(image_bgr, detected_lines)
            if ocr_result.confidence > 0.5:
                ocr_result.aspect_ratio = aspect_ratio
                return ocr_result
        
        # Tier 2: Heuristic room-label scaling
        heuristic_result = self._tier2_heuristic_scaling(image_bgr, detected_lines)
        if heuristic_result.confidence > 0.3:
            heuristic_result.aspect_ratio = aspect_ratio
            return heuristic_result
        
        # Tier 3: Default with aspect ratio constraint
        return ScaleResult(
            scale_factor=DEFAULT_SCALE,
            scaling_method="default",
            confidence=0.1,
            aspect_ratio=aspect_ratio,
            reference_length_px=w,
            reference_length_m=w * DEFAULT_SCALE
        )
    
    def _tier1_ocr_scaling(
        self,
        image_bgr: np.ndarray,
        detected_lines: list[tuple[float, float, float, float]] | None = None
    ) -> ScaleResult:
        """
        Tier 1: OCR-based dimension extraction.
        Scans for dimension text like "16m", "9.2m" and correlates with line lengths.
        """
        if not self.ocr_reader:
            return ScaleResult(scale_factor=DEFAULT_SCALE, scaling_method="ocr", confidence=0.0)
        
        # Preprocess for better OCR
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # Run OCR
        try:
            ocr_results = self.ocr_reader.readtext(gray, detail=1)
        except Exception:
            return ScaleResult(scale_factor=DEFAULT_SCALE, scaling_method="ocr", confidence=0.0)
        
        detected_dimensions = []
        
        for (bbox, text, conf) in ocr_results:
            if conf < 0.4:
                continue
            
            # Check if text matches dimension pattern
            match = DIMENSION_PATTERN.search(text)
            if match:
                value_m = float(match.group(1))
                
                # Get bounding box center
                pts = np.array(bbox)
                cx = pts[:, 0].mean()
                cy = pts[:, 1].mean()
                
                # Estimate line length from text bounding box width
                text_width_px = np.max(pts[:, 0]) - np.min(pts[:, 0])
                
                detected_dimensions.append({
                    'text': text,
                    'value_m': value_m,
                    'center': (cx, cy),
                    'text_width_px': text_width_px,
                    'confidence': conf
                })
        
        if not detected_dimensions:
            return ScaleResult(scale_factor=DEFAULT_SCALE, scaling_method="ocr", confidence=0.0)
        
        # Find the longest dimension with highest confidence
        best_dim = max(detected_dimensions, key=lambda d: d['value_m'] * d['confidence'])
        
        # Find the nearest line to the dimension text
        if detected_lines:
            best_line_length_px = self._find_nearest_line(
                best_dim['center'], detected_lines
            )
        else:
            # Estimate from text position - assume text spans the dimension line
            best_line_length_px = best_dim['text_width_px'] * 3  # Rough estimate
        
        if best_line_length_px > 0:
            scale_factor = best_dim['value_m'] / best_line_length_px
        else:
            scale_factor = DEFAULT_SCALE
        
        return ScaleResult(
            scale_factor=scale_factor,
            scaling_method="ocr",
            confidence=best_dim['confidence'],
            detected_dimensions=detected_dimensions,
            reference_length_px=best_line_length_px,
            reference_length_m=best_dim['value_m']
        )
    
    def _tier2_heuristic_scaling(
        self,
        image_bgr: np.ndarray,
        detected_lines: list[tuple[float, float, float, float]] | None = None
    ) -> ScaleResult:
        """
        Tier 2: Heuristic room-label scaling.
        Scans for room labels and uses architectural standards for scaling.
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        room_labels = []
        
        # Try OCR for room labels
        if self.ocr_reader:
            try:
                ocr_results = self.ocr_reader.readtext(gray, detail=1)
                for (bbox, text, conf) in ocr_results:
                    if conf < 0.3:
                        continue
                    
                    text_lower = text.lower()
                    for room_type, room_info in ROOM_PATTERNS.items():
                        if room_info['pattern'].search(text_lower):
                            pts = np.array(bbox)
                            cx = pts[:, 0].mean()
                            cy = pts[:, 1].mean()
                            room_labels.append({
                                'type': room_type,
                                'text': text,
                                'center': (cx, cy),
                                'min_dim_m': room_info['min_dim_m'],
                                'confidence': conf
                            })
                            break
            except Exception:
                pass
        
        if not room_labels:
            # Fallback: try to detect enclosed regions and assume standard bedroom
            return self._estimate_from_layout(detected_lines, w, h)
        
        # Use best room label for scaling
        best_room = max(room_labels, key=lambda r: r['confidence'])
        
        # Find the smallest room dimension (width or height of enclosing region)
        if detected_lines:
            room_dim_px = self._estimate_room_dimension(best_room['center'], detected_lines)
        else:
            # Estimate from image proportions
            room_dim_px = min(w, h) / 3  # Assume ~3 rooms fit in smallest dimension
        
        if room_dim_px > 0:
            scale_factor = best_room['min_dim_m'] / room_dim_px
        else:
            scale_factor = DEFAULT_SCALE
        
        return ScaleResult(
            scale_factor=scale_factor,
            scaling_method="heuristic",
            confidence=0.6 * best_room['confidence'],
            room_labels=room_labels,
            reference_length_px=room_dim_px,
            reference_length_m=best_room['min_dim_m']
        )
    
    def _estimate_from_layout(
        self,
        detected_lines: list[tuple[float, float, float, float]] | None,
        w: int,
        h: int
    ) -> ScaleResult:
        """
        Estimate scale from overall layout proportions.
        Assumes a typical residential floor plan.
        """
        if not detected_lines:
            return ScaleResult(
                scale_factor=DEFAULT_SCALE,
                scaling_method="heuristic",
                confidence=0.2
            )
        
        # Find the longest wall segment - likely an exterior wall
        max_length = 0
        for x1, y1, x2, y2 in detected_lines:
            length = math.hypot(x2 - x1, y2 - y1)
            if length > max_length:
                max_length = length
        
        if max_length > 0:
            # Assume longest wall is around 12m for typical residence
            assumed_length_m = 12.0
            scale_factor = assumed_length_m / max_length
        else:
            scale_factor = DEFAULT_SCALE
        
        return ScaleResult(
            scale_factor=scale_factor,
            scaling_method="heuristic",
            confidence=0.25,
            reference_length_px=max_length,
            reference_length_m=12.0
        )
    
    def _find_nearest_line(
        self,
        point: tuple[float, float],
        lines: list[tuple[float, float, float, float]]
    ) -> float:
        """Find the length of the line nearest to a point."""
        px, py = point
        best_dist = float('inf')
        best_length = 0
        
        for x1, y1, x2, y2 in lines:
            # Distance from point to line segment
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dist = math.hypot(px - mx, py - my)
            
            if dist < best_dist:
                best_dist = dist
                best_length = math.hypot(x2 - x1, y2 - y1)
        
        return best_length
    
    def _estimate_room_dimension(
        self,
        center: tuple[float, float],
        lines: list[tuple[float, float, float, float]]
    ) -> float:
        """Estimate the dimension of a room from its center point."""
        cx, cy = center
        
        # Find walls near the center point
        nearby_walls = []
        for x1, y1, x2, y2 in lines:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dist = math.hypot(cx - mx, cy - my)
            if dist < 200:  # Within 200 pixels
                nearby_walls.append((x1, y1, x2, y2, dist))
        
        if len(nearby_walls) < 2:
            return 0
        
        # Estimate room dimension from nearby horizontal/vertical walls
        horiz_walls = []
        vert_walls = []
        
        for x1, y1, x2, y2, dist in nearby_walls:
            angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            if angle < 15 or angle > 165:  # Horizontal
                horiz_walls.append((x1, y1, x2, y2))
            elif 75 < angle < 105:  # Vertical
                vert_walls.append((x1, y1, x2, y2))
        
        # Find min dimension (likely room width)
        room_width = float('inf')
        
        if len(horiz_walls) >= 2:
            y_coords = [(y1 + y2) / 2 for x1, y1, x2, y2 in horiz_walls]
            for i, y1 in enumerate(y_coords):
                for y2 in y_coords[i+1:]:
                    room_width = min(room_width, abs(y2 - y1))
        
        if len(vert_walls) >= 2:
            x_coords = [(x1 + x2) / 2 for x1, y1, x2, y2 in vert_walls]
            for i, x1 in enumerate(x_coords):
                for x2 in x_coords[i+1:]:
                    room_width = min(room_width, abs(x2 - x1))
        
        return room_width if room_width != float('inf') else 100  # Default 100px


def analyze_wall_thickness(
    image_bgr: np.ndarray,
    detected_lines: list[tuple[float, float, float, float]],
    scale_factor: float
) -> WallThicknessResult:
    """
    Analyze wall thickness using parallel-line distance analysis.
    Classifies walls as Major (0.23m) or Minor (0.115m).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    wall_thicknesses = []
    thickness_values = []
    
    for idx, (x1, y1, x2, y2) in enumerate(detected_lines):
        # Calculate perpendicular direction
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        
        # Normalized perpendicular vector
        px, py = -dy / length, dx / length
        
        # Sample points along the wall
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        
        # Measure wall thickness by finding edges in perpendicular direction
        thickness_px = _measure_thickness_at_point(edges, mx, my, px, py)
        thickness_values.append(thickness_px)
        
        wall_thicknesses.append({
            'segment_idx': idx,
            'thickness_px': thickness_px
        })
    
    # Classify into Major/Minor based on distribution
    if thickness_values:
        median_thickness = sorted(thickness_values)[len(thickness_values) // 2]
        
        for wall in wall_thicknesses:
            if wall['thickness_px'] > median_thickness * 1.3:
                wall['category'] = 'major'
                wall['thickness_m'] = 0.23
            else:
                wall['category'] = 'minor'
                wall['thickness_m'] = 0.115
    
    return WallThicknessResult(
        wall_thicknesses=wall_thicknesses,
        major_thickness_m=0.23,
        minor_thickness_m=0.115
    )


def _measure_thickness_at_point(
    edges: np.ndarray,
    mx: float,
    my: float,
    px: float,
    py: float,
    max_distance: int = 50
) -> float:
    """Measure wall thickness at a point by scanning perpendicular to wall direction."""
    h, w = edges.shape
    
    # Scan in positive direction
    pos_dist = 0
    for d in range(1, max_distance):
        x = int(mx + px * d)
        y = int(my + py * d)
        if 0 <= x < w and 0 <= y < h:
            if edges[y, x] > 0:
                pos_dist = d
                break
    
    # Scan in negative direction
    neg_dist = 0
    for d in range(1, max_distance):
        x = int(mx - px * d)
        y = int(my - py * d)
        if 0 <= x < w and 0 <= y < h:
            if edges[y, x] > 0:
                neg_dist = d
                break
    
    return pos_dist + neg_dist if pos_dist or neg_dist else 10  # Default 10px


def count_staircase_treads(
    binary_mask: np.ndarray,
    staircase_bbox: dict
) -> int:
    """
    Count the number of treads (steps) in a detected staircase.
    Uses parallel line detection within the staircase bounding box.
    """
    x = int(staircase_bbox.get('x', 0))
    y = int(staircase_bbox.get('y', 0))
    w = int(staircase_bbox.get('width', 100))
    h = int(staircase_bbox.get('height', 100))
    
    # Ensure bounds are valid
    img_h, img_w = binary_mask.shape[:2]
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = min(w, img_w - x)
    h = min(h, img_h - y)
    
    if w < 10 or h < 10:
        return 17  # Default
    
    # Extract staircase region
    roi = binary_mask[y:y+h, x:x+w]
    
    # Detect horizontal lines (treads)
    edges = cv2.Canny(roi, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=20,
        minLineLength=w // 3,
        maxLineGap=5
    )
    
    if lines is None:
        return 17  # Default for 3m height
    
    # Count distinct horizontal lines (treads)
    horizontal_y_coords = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
        if angle < 15 or angle > 165:  # Horizontal
            avg_y = (y1 + y2) / 2
            horizontal_y_coords.append(avg_y)
    
    # Cluster nearby lines (within 5px)
    if not horizontal_y_coords:
        return 17
    
    horizontal_y_coords.sort()
    tread_count = 1
    prev_y = horizontal_y_coords[0]
    
    for y in horizontal_y_coords[1:]:
        if y - prev_y > 5:
            tread_count += 1
            prev_y = y
    
    return max(3, min(tread_count, 30))  # Clamp between 3 and 30 steps


def calculate_staircase_height(tread_count: int, tread_height_m: float = 0.15) -> float:
    """Calculate total staircase height from tread count."""
    return tread_count * tread_height_m


# Singleton scaling engine
_scaling_engine: ScalingEngine | None = None


def get_scaling_engine(enable_ocr: bool = True) -> ScalingEngine:
    """Get or create the singleton scaling engine."""
    global _scaling_engine
    if _scaling_engine is None:
        _scaling_engine = ScalingEngine(enable_ocr=enable_ocr)
    return _scaling_engine
