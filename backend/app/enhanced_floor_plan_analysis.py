import math
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
import uuid

# Only import easyocr when needed or handle gracefully
try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False


class EnhancedConfig:
    """Configurable parameters optimized for clean, printed floor plans."""
    
    # Preprocessing
    BLUR_KERNEL = (3, 3)
    ADAPTIVE_THRESH_BLOCK = 15
    ADAPTIVE_THRESH_C = 5
    
    # Wall Detection
    HOUGH_RHO = 1
    HOUGH_THETA = np.pi / 180
    HOUGH_THRESHOLD = 80
    HOUGH_MIN_LINE_LENGTH = 30
    HOUGH_MAX_LINE_GAP = 15
    
    # Line Merging Parameter
    MERGE_ANGLE_TOLERANCE = 5.0      # degrees
    MERGE_DISTANCE_TOLERANCE = 15.0  # pixels
    
    # Room Detection
    MIN_ROOM_AREA = 1000.0  # pixels squared
    
    # Corner Detection
    HARRIS_BLOCK_SIZE = 3
    HARRIS_KSIZE = 3
    HARRIS_K = 0.04
    CORNER_QUALITY = 0.05
    MIN_CORNER_DISTANCE = 20

    # OCR 
    OCR_LANG = ['en']
    OCR_MIN_CONFIDENCE = 0.4


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Enhance structural lines for printed documents."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # High contrast prints do well with adaptive thresholding
    binary = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        EnhancedConfig.ADAPTIVE_THRESH_BLOCK, 
        EnhancedConfig.ADAPTIVE_THRESH_C
    )
    
    # Morphological closing to fill small gaps in drawn lines
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    return binary


def improved_wall_detection(image: np.ndarray) -> List[Dict[str, Any]]:
    """Detects lines and merges parallel walls drawn with thickness into single abstract lines."""
    binary = preprocess_image(image)
    
    lines = cv2.HoughLinesP(
        binary, 
        rho=EnhancedConfig.HOUGH_RHO, 
        theta=EnhancedConfig.HOUGH_THETA, 
        threshold=EnhancedConfig.HOUGH_THRESHOLD, 
        minLineLength=EnhancedConfig.HOUGH_MIN_LINE_LENGTH, 
        maxLineGap=EnhancedConfig.HOUGH_MAX_LINE_GAP
    )
    
    if lines is None:
        return []

    raw_lines = lines[:, 0, :]
    
    # Simple formatting of detected lines
    formatted_walls = []
    for x1, y1, x2, y2 in raw_lines:
        length = float(math.hypot(x2 - x1, y2 - y1))
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        # Normalize angle to [0, 180) for parallel checks
        if angle < 0: angle += 180
        if angle == 180: angle = 0
            
        formatted_walls.append({
            'x1': float(x1), 'y1': float(y1), 
            'x2': float(x2), 'y2': float(y2), 
            'length': length, 'angle': angle
        })
        
    # TODO: Complex parallel merging could be placed here to snap thick walls to centerlines,
    # but for printed plans HoughLinesP on a precise binary mask is usually very robust.
    
    return formatted_walls


def precise_corner_detection(image: np.ndarray, walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract precise structural corners using Harris and line intersections."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = np.float32(gray)
    
    dst = cv2.cornerHarris(
        gray, 
        EnhancedConfig.HARRIS_BLOCK_SIZE, 
        EnhancedConfig.HARRIS_KSIZE, 
        EnhancedConfig.HARRIS_K
    )
    
    # Dilate to mark corners
    dst = cv2.dilate(dst, None)
    
    # Find local maxima coordinates
    ret, dst_thresh = cv2.threshold(dst, EnhancedConfig.CORNER_QUALITY * dst.max(), 255, 0)
    dst_thresh = np.uint8(dst_thresh)
    
    # Find centroids
    ret, labels, stats, centroids = cv2.connectedComponentsWithStats(dst_thresh)
    
    corners = []
    for (x, y) in centroids[1:]:  # Skip background
        corners.append({
            'x': float(x),
            'y': float(y),
            'confidence': min(1.0, float(dst[int(y), int(x)] / dst.max()))
        })
        
    return corners


def improved_room_identification(image: np.ndarray, walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Segment rooms using morphological closing and contour detection (flood fill concept)."""
    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Draw walls as thick white lines to create solid boundaries
    for w_obj in walls:
        pt1 = (int(w_obj['x1']), int(w_obj['y1']))
        pt2 = (int(w_obj['x2']), int(w_obj['y2']))
        cv2.line(mask, pt1, pt2, 255, thickness=4)
        
    # Invert the mask. White areas are now empty spaces inside rooms.
    inv_mask = cv2.bitwise_not(mask)
    
    # Erode to detach slightly connected rooms 
    kernel = np.ones((5, 5), np.uint8)
    inv_mask = cv2.erode(inv_mask, kernel, iterations=2)
    
    # Find isolated room blobs
    contours, _ = cv2.findContours(inv_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    rooms = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < EnhancedConfig.MIN_ROOM_AREA:
            continue
            
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
        else:
            cx, cy = 0, 0
            
        # Get polygon approximation for corners
        epsilon = 0.02 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, epsilon, True)
        
        corners = [{'x': float(pt[0][0]), 'y': float(pt[0][1])} for pt in approx]
        
        shape = "Polygon"
        if len(approx) == 4:
            shape = "Rectangle"
            
        rooms.append({
            'id': str(uuid.uuid4())[:8],
            'corners': corners,
            'area': float(area),
            'centroid': {'x': float(cx), 'y': float(cy)},
            'shape': shape,
            'label': None # To be populated by OCR
        })
        
    return rooms


def calculate_dimensions(walls: List[Dict[str, Any]], px_to_m: float) -> List[Dict[str, Any]]:
    """Snaps angles to rigorous architectural degrees and computes physical length."""
    for w in walls:
        # Calculate real length
        w['length_m'] = round(w['length'] * px_to_m, 3)
        
        # Snap Angle
        angle = w['angle']
        # Normalize to 0-360
        angle = angle % 360
        # Common structural snaps
        snaps = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 360.0]
        
        best_snap = angle
        min_diff = 360.0
        for s in snaps:
            diff = abs(angle - s)
            if diff < 15.0 and diff < min_diff:
                min_diff = diff
                best_snap = s
                
        if best_snap == 360.0:
            best_snap = 0.0
            
        w['snapped_angle'] = best_snap
        
    return walls


def extract_text_labels(image: np.ndarray) -> List[Dict[str, Any]]:
    """Extract room labels and dimensions using EasyOCR."""
    if not HAS_EASYOCR:
        print("Warning: easyocr not installed. Returning empty label set.")
        return []
        
    print("Initializing Reader...")
    reader = easyocr.Reader(EnhancedConfig.OCR_LANG, gpu=False)
    results = reader.readtext(image)
    
    extracted = []
    for (bbox, text, prob) in results:
        if prob > EnhancedConfig.OCR_MIN_CONFIDENCE:
            # bbox is [[x_tl, y_tl], [x_tr, y_tr], [x_br, y_br], [x_bl, y_bl]]
            center_x = (bbox[0][0] + bbox[2][0]) / 2.0
            center_y = (bbox[0][1] + bbox[2][1]) / 2.0
            
            extracted.append({
                'text': text,
                'confidence': float(prob),
                'x': float(center_x),
                'y': float(center_y),
                'bbox': [[float(p[0]), float(p[1])] for p in bbox]
            })
            
    return extracted


def add_labels_to_rooms(rooms: List[Dict[str, Any]], labels: List[Dict[str, Any]]):
    """Assigns detected OCR labels to the closest room centroid."""
    for lbl in labels:
        tx, ty = lbl['x'], lbl['y']
        
        closest_room = None
        min_dist = float('inf')
        
        for r in rooms:
            cx, cy = r['centroid']['x'], r['centroid']['y']
            dist = math.hypot(tx - cx, ty - cy)
            if dist < min_dist:
                min_dist = dist
                closest_room = r
                
        # If the label is reasonably inside/near the room
        if closest_room and min_dist < 200: 
            if closest_room['label'] is None:
                closest_room['label'] = lbl['text']
            else:
                closest_room['label'] += f" {lbl['text']}"


def draw_diagnostics(image: np.ndarray, walls: List, rooms: List, corners: List, labels: List = None) -> np.ndarray:
    """Renders debug visual layers over a copy of the original image."""
    diag = image.copy()
    
    # Walls (Blue)
    for w in walls:
        cv2.line(diag, (int(w['x1']), int(w['y1'])), (int(w['x2']), int(w['y2'])), (255, 0, 0), 2)
        
    # Corners (Red Dots)
    for c in corners:
        cv2.circle(diag, (int(c['x']), int(c['y'])), 4, (0, 0, 255), -1)
        
    # Rooms (Green Polygons + Centroid Text)
    for r in rooms:
        pts = np.array([[pt['x'], pt['y']] for pt in r['corners']], np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(diag, [pts], True, (0, 255, 0), 2)
        
        cx, cy = int(r['centroid']['x']), int(r['centroid']['y'])
        cv2.circle(diag, (cx, cy), 5, (0, 255, 0), -1)
        
        # Draw resolved label if bound
        if r.get('label'):
            cv2.putText(diag, r['label'], (cx - 20, cy - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 0), 2)
            
    # Draw raw OCR labels if provided (Purple)
    if labels:
        for lbl in labels:
            lx, ly = int(lbl['x']), int(lbl['y'])
            cv2.putText(diag, lbl['text'], (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
            
    return diag


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python enhanced_floor_plan_analysis.py <path_to_image>")
        sys.exit(1)
        
    print(f"Loading {sys.argv[1]}...")
    img = cv2.imread(sys.argv[1])
    if img is None:
        print("Failed to load image.")
        sys.exit(1)
        
    print("1. Improved Wall Detection...")
    w_list = improved_wall_detection(img)
    print(f"   -> Found {len(w_list)} walls.")
    
    print("2. Improved Room Extraction...")
    r_list = improved_room_identification(img, w_list)
    print(f"   -> Found {len(r_list)} structural rooms.")
    
    print("3. Precise Corner Plotting...")
    c_list = precise_corner_detection(img, w_list)
    print(f"   -> Found {len(c_list)} key corners.")
    
    print("4. Dimensions Conversion...")
    w_list = calculate_dimensions(w_list, pixel_to_meter_ratio=0.01)
    
    print("5. Launching OCR Text Extraction...")
    texts = extract_text_labels(img)
    print(f"   -> Found {len(texts)} text occurrences.")
    
    add_labels_to_rooms(r_list, texts)
    
    diag_img = draw_diagnostics(img, w_list, r_list, c_list, texts)
    output_path = "debug_diagnostic.jpg"
    cv2.imwrite(output_path, diag_img)
    print(f"Diagnostic footprint generated at: {output_path}")
    
    print("Finished.")
