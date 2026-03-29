"""
Floor plan parsing: Canny, HoughLinesP, contour detection, snapping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from app.config import settings
from app.snapping import enforce_axis_alignment, snap_segment


@dataclass
class DetectionResult:
    lines_hough: list[tuple[float, float, float, float]]
    snapped_segments: list[tuple[float, float, float, float]]
    binary_vis: np.ndarray
    edges_vis: np.ndarray
    contours: list[np.ndarray]
    image_shape: tuple[int, int]
    has_second_floor: bool = False
    void_coordinates: tuple[float, float] | None = None


def _preprocess(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    return binary


def detect_walls_opencv(
    image_bgr: np.ndarray,
    tolerance_px: float | None = None,
) -> DetectionResult:
    tol = tolerance_px if tolerance_px is not None else settings.snap_tolerance_px
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    binary = _preprocess(gray)

    edges = cv2.Canny(
        gray, settings.canny_low, settings.canny_high, apertureSize=3
    )

    lines_hough: list[tuple[float, float, float, float]] = []
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=settings.hough_threshold,
        minLineLength=settings.min_line_length,
        maxLineGap=settings.max_line_gap,
    )
    if lines is not None:
        for ln in lines:
            x1, y1, x2, y2 = ln[0]
            lines_hough.append((float(x1), float(y1), float(x2), float(y2)))

    contour_src = binary
    contours, _ = cv2.findContours(
        contour_src, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )

    snapped: list[tuple[float, float, float, float]] = []
    for x1, y1, x2, y2 in lines_hough:
        ax1, ay1, ax2, ay2 = enforce_axis_alignment(x1, y1, x2, y2, tol)
        sx1, sy1, sx2, sy2 = snap_segment(ax1, ay1, ax2, ay2, tol)
        if math.hypot(sx2 - sx1, sy2 - sy1) < 1.0:
            continue
        snapped.append((sx1, sy1, sx2, sy2))

    if not snapped and contours:
        for c in contours[:50]:
            eps = 0.01 * cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, eps, True)
            n = len(approx)
            for i in range(n):
                p0 = approx[i][0]
                p1 = approx[(i + 1) % n][0]
                x1, y1 = float(p0[0]), float(p0[1])
                x2, y2 = float(p1[0]), float(p1[1])
                ax1, ay1, ax2, ay2 = enforce_axis_alignment(x1, y1, x2, y2, tol)
                sx1, sy1, sx2, sy2 = snap_segment(ax1, ay1, ax2, ay2, tol)
                if math.hypot(sx2 - sx1, sy2 - sy1) >= 1.0:
                    snapped.append((sx1, sy1, sx2, sy2))

    h, w = image_bgr.shape[:2]
    
    # Heuristic for Staircase / Void 'X' detection
    # We look for intersecting diagonal lines among snapped or raw hough lines
    has_second_floor = False
    void_coordinates = None
    
    def do_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
        # A simple bounding box check + line intersection
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0: return False
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
        if 0 < t < 1 and 0 < u < 1:
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return False

    # 1. Filter out only strictly diagonal lines (slope between 0.3 and 3.0)
    diagonal_lines = []
    for ln in lines_hough:
        x1, y1, x2, y2 = ln
        dx, dy = x2 - x1, y2 - y1
        l = math.hypot(dx, dy)
        if l < 20: continue
        if abs(dx) > 1e-5 and abs(dy) > 1e-5:
            slope = abs(dy / dx)
            if 0.3 < slope < 3.0:
                diagonal_lines.append((x1, y1, x2, y2, dx, dy, l))

    # 2. Check intersecting lines only among the much smaller diagonal pool
    for i in range(len(diagonal_lines)):
        x1, y1, x2, y2, dx1, dy1, l1 = diagonal_lines[i]
        for j in range(i+1, len(diagonal_lines)):
            x3, y3, x4, y4, dx2, dy2, l2 = diagonal_lines[j]
            
            dot = dx1*dx2 + dy1*dy2
            cos_theta = max(-1.0, min(1.0, dot / (l1 * l2)))
            
            # Cross indicates perpendicular roughly (angle between 60° and 120°) -> |cos_theta| < 0.5
            if abs(cos_theta) < 0.5:
                intersect = do_intersect(x1, y1, x2, y2, x3, y3, x4, y4)
                if intersect:
                    has_second_floor = True
                    void_coordinates = intersect
                    break
        if has_second_floor:
            break

    return DetectionResult(
        lines_hough=lines_hough,
        snapped_segments=snapped,
        binary_vis=binary,
        edges_vis=edges,
        contours=contours,
        image_shape=(h, w),
        has_second_floor=has_second_floor,
        void_coordinates=void_coordinates
    )


def has_meaningful_geometry(snapped_count: int, contour_count: int) -> bool:
    return snapped_count >= 3 or contour_count >= 2
